import zipfile
import pandas as pd
import numpy as np
import argparse
import psycopg2
from psycopg2.extras import execute_values
from tqdm import tqdm
from pathlib import Path
import yaml
import logging
from io import TextIOWrapper, StringIO
import math

logging.basicConfig(
    format="%(asctime)s.%(msecs)03d %(levelname)s : %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)


def remove_whitespace(s):
    while s.startswith(" "):
        s = s[1:]
    while s.endswith(" "):
        s = s[:-1]
    return s


def remove_newline(s):
    if s.endswith("\n"):
        s = s[:-1]
    return s


def replace_semicolon(s):
    return s.replace("; ", ":")


def dms2deg(dmss):
    dmss = dmss.replace("´", "'")
    degrees = int(dmss.split("°")[0])
    rest = dmss.split("°")[1]
    if len(rest) > 0:
        minute = float(rest.split("'")[0])
        degrees += minute / 60
        rest = rest.split("'")[1]
        if len(rest) > 0:
            second = float(rest.split("'")[0])
            degrees += second / (60 * 60)
    return degrees


def dms2latlon(dms):
    lon_dms, lat_dms = dms.split("/")
    lat = dms2deg(lat_dms)
    lon = dms2deg(lon_dms)
    return lat, lon


def is_empty_line(line):
    if len(line.replace(" ", "").replace("\n", "")) == 0:
        return True
    return False


def csvStringIO_to_df(csvStringIO):
    df = pd.read_csv(csvStringIO, sep=";", low_memory=False)
    for col in df.columns.tolist()[2:]:
        df[col] = pd.to_numeric(df[col], errors="coerce", downcast="float")
    format = "%Y%m%d"  # daily
    if len(str(df["time"].tolist()[0])) == 10:  # hourly
        format += "%H"
    elif len(str(df["time"].tolist()[0])) == 12:  # 10 minutes
        format += "%H%M"

    df.insert(2, "date", pd.to_datetime(df["time"], format=format))
    return df


def postgresql_connect(configuration_file):
    with open(configuration_file, "r") as stream:
        try:
            cfg = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    db_host = cfg.get("host")
    db_port = int(cfg.get("port"))
    db_user = cfg.get("user")
    db_password = cfg.get("password")
    database = cfg.get("database")
    logging.info(f"Connecting to {db_host}:{db_port} / {database}")
    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=database,
        )
        return conn
    except Exception as e:
        print(e)


def execute_query(query, args, conn):
    cur = conn.cursor()
    if args:
        cur.execute(query, args)
    conn.commit()
    conn.reset()


def insert_stations(df_station, conn):
    query = """INSERT INTO station (station_id, station_name, data_src, location, altitude) 
                VALUES (%s, %s, %s, point(%s, %s), %s) ON CONFLICT DO NOTHING"""
    for index, row in df_station.iterrows():
        args = (
            row["stn_id"],
            row["stn_name"],
            row["data_src"],
            row["latitude"],
            row["longitude"],
            row["altitude"],
        )
        execute_query(query=query, args=args, conn=conn)


def insert_parameters(df_param, conn):
    query = """INSERT INTO parameter (param_id, unit, description) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING"""
    for index, row in df_param.iterrows():
        args = (row["param_id"], row["unit"], row["description"])
        execute_query(query=query, args=args, conn=conn)


def insert_data(df, conn):
    param_ids = list(df.columns[3:])
    times = df.date.tolist()
    stn_ids = df.stn.tolist()
    for param in tqdm(param_ids):
        values = df[param].tolist()
        param_id = [param for i in range(len(values))]
        data = [(times[i], param, stn_ids[i], values[i]) for i in range(len(values))]
        data = filter(lambda x: math.isnan(x[3]) == False, data)
        data = list(data)
        query = """INSERT INTO meteodata VALUES %s ON CONFLICT DO NOTHING"""
        cur = conn.cursor()
        execute_values(cur, query, data, page_size=16000)
        conn.commit()


def parse_legend_file(archive, filename):
    print("reading input file:", filename)
    with archive.open(filename) as f:
        file_content = TextIOWrapper(f).readlines()

    # extract stn and param part from file
    current_block = None
    stns = []
    params = []
    for i in range(2, len(file_content)):
        if file_content[i - 1].startswith("---------"):
            if file_content[i - 2].startswith("Parameter"):
                current_block = "param"
            elif file_content[i - 2].startswith("Stationen"):
                current_block = "stn"
        if len(file_content[i]) == 1:
            current_block = None
        if current_block == "stn":
            stns.append(file_content[i])
        elif current_block == "param":
            params.append(file_content[i])

    params[0] = "param_id  " + params[0]

    # extract stations
    stn_content = []
    for i in range(1, len(stns)):
        stn_content.append(
            [
                remove_newline(remove_whitespace(i))
                for i in list(filter(None, stns[i].split("  ")))
            ]
        )
    stn_ids = [s[0] for s in stn_content]
    np.unique([s[1] for s in stn_content])
    known_stn = []
    unique_stns = []
    for i in range(len(stn_content)):
        if not stn_content[i][0] in known_stn:
            known_stn.append(stn_content[i][0])
            lat, lon = dms2latlon(stn_content[i][4])
            unique_stns.append(
                {
                    "stn_id": stn_content[i][0],
                    "stn_name": stn_content[i][1],
                    "data_src": stn_content[i][3],
                    "latitude": lat,
                    "longitude": lon,
                    "altitude": stn_content[i][6],
                }
            )

    df_station = pd.DataFrame(data=unique_stns)

    # extract parameters
    param_content = []
    for i in range(1, len(params)):

        param_content.append(
            [
                remove_newline(remove_whitespace(i))
                for i in list(
                    filter(
                        None,
                        [params[i].split(" ")[0]]
                        + replace_semicolon(" ".join(params[i].split(" ")[1:])).split(
                            "  "
                        ),
                    )
                )
            ]
        )
    unique_params = []
    for i in range(len(param_content)):
        unique_params.append(
            {
                "param_id": param_content[i][0],
                "unit": param_content[i][1],
                "description": param_content[i][2],
            }
        )

    df_param = pd.DataFrame(data=unique_params)
    return df_station, df_param


def parse_data_file(archive, filename):
    with archive.open(filename) as f:
        file_content = TextIOWrapper(f).readlines()
    section_ends = [-1]
    while is_empty_line(file_content[0]):
        file_content.pop(0)
    for i in range(len(file_content)):
        if is_empty_line(file_content[i]):
            section_ends.append(i - 1)

    sections = []
    for i in range(len(section_ends) - 1):
        clean_section = []
        section_content = file_content[section_ends[i] + 1 : section_ends[i + 1]]
        for j in range(len(section_content)):
            if not is_empty_line(section_content[j]):
                clean_section.append(section_content[j])
        sections.append(clean_section)
    return sections


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-c", "--credentials", required=True)
    args = parser.parse_args()
    input_file = Path(args.input)
    logging.info(input_file)
    configuration = Path(args.credentials)
    if not configuration.suffix in [".yaml", ".yml"]:
        logging.error("invalid configuration!")
        exit(1)
    try:
        archive = zipfile.ZipFile(input_file, "r")
    except:
        logging.error(f"Failed open {input_file} , Aborting.")
        exit(1)
    files_in_zip = archive.namelist()
    data_files = list(filter(lambda k: "_data" in k, files_in_zip))
    legend_files = list(filter(lambda k: "_legend" in k, files_in_zip))
    logging.info(f"found {len(legend_files)} legend files.")
    logging.info(f"found {len(data_files)} data files.")
    assert len(legend_files) == 1
    assert len(data_files) == 1
    conn = postgresql_connect(configuration)
    df_station, df_param = parse_legend_file(archive, legend_files[0])
    logging.info(
        f"{len(df_station)} Stations, {len(df_param)} parameters in {legend_files[0]}"
    )
    # insert stations
    logging.info("Inserting Stations")
    insert_stations(df_station, conn)
    # insert parameters
    logging.info("Inserting Parameters")
    insert_parameters(df_param, conn)
    data_sections = parse_data_file(archive, data_files[0])
    data_section_sio = [StringIO("".join(s)) for s in data_sections]
    for section in data_section_sio:
        df = csvStringIO_to_df(section)
        logging.info(
            f"Inserting Data {df.stn.unique()}: {df.date.min()} to {df.date.max()}"
        )
        insert_data(df, conn)
