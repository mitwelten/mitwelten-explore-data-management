import requests
import json
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import datetime

GBIF_MEDIA_TYPES = ["InteractiveResource", "MovingImage", "Sound", "StillImage"]


def search_in_dict(obj, structure: list):
    if obj is None:
        return None
    if len(structure) == 0:
        return obj
    if len(structure) > 0:
        if type(structure[0]) == str:
            if type(obj) == dict:
                return search_in_dict(obj.get(structure[0]), structure[1:])
        if type(structure[0]) == int:
            if type(obj) == list:
                if len(obj) > structure[0]:
                    return search_in_dict(obj[structure[0]], structure[1:])
    return None


# check field lengths of occ:
def trim_strings(record):
    for k in list(record.keys()):
        if k != "media":
            if isinstance(record[k], str):
                if len(record[k]) > 254:
                    record[k] = record[k][:250] + " ..."
    return record


def get_species_info(species_key):
    headers = {"Accept-Language": "de-CH,de-DE;q=0.9,de;q=0.8,en-US;q=0.7,en;q=0.6"}

    if species_key is None:
        return None
    sp_url = "https://api.gbif.org/v1/species/{}".format(species_key)
    resp = requests.get(sp_url)
    if resp.status_code == 200:
        resp = resp.json()
    else:
        return None

    resp_de = requests.get(sp_url, headers=headers)
    if resp_de.status_code == 200:
        resp_de = resp_de.json()
    else:
        return None
    return dict(
        species_key=species_key,
        kingdom_key=resp.get("kingdomKey"),
        phylum_key=resp.get("phylumKey"),
        class_key=resp.get("classKey"),
        order_key=resp.get("orderKey"),
        family_key=resp.get("familyKey"),
        genus_key=resp.get("genusKey"),
        sc_kingdom=resp.get("kingdom"),
        sc_phylum=resp.get("phylum"),
        sc_class=resp.get("class"),
        sc_order=resp.get("order"),
        sc_family=resp.get("family"),
        sc_genus=resp.get("genus"),
        sc_species=resp.get("species"),
        name_de=resp_de.get("vernacularName"),
        name_en=resp.get("vernacularName"),
    )


def get_dataset_name(dataset_key):
    url = f"https://api.gbif.org/v1/dataset/{dataset_key}"
    res = requests.get(url)
    if res.status_code == 200:
        try:
            return res.json().get("title")
        except:
            return None
    return None


def parse_occurence_results(results):
    parsed_results = []
    for res in results:
        event_date = res.get("eventDate")
        try:
            date_valid = datetime.datetime.fromisoformat(event_date)
        except:
            print("invalid date", event_date)
            continue

        if event_date is not None:
            has_media = len(res.get("media")) > 0
            media = json.dumps(res.get("media")) if has_media else None
            mediaType = None

            if has_media:
                types = []
                if isinstance(media, list):
                    for m in media:
                        if "type" in m:
                            types.append(m.get("type"))

                    mediaType = ",".join(list(set(types)))

            parsed_results.append(
                dict(
                    key=res.get("key"),
                    eventDate=event_date,
                    decimalLatitude=res.get("decimalLatitude"),
                    decimalLongitude=res.get("decimalLongitude"),
                    taxonKey=res.get("taxonKey"),
                    kingdomKey=res.get("kingdomKey"),
                    phylumKey=res.get("phylumKey"),
                    classKey=res.get("classKey"),
                    orderKey=res.get("orderKey"),
                    familyKey=res.get("familyKey"),
                    genusKey=res.get("genusKey"),
                    speciesKey=res.get("speciesKey"),
                    references=res.get("references"),
                    gbifReference=f"https://www.gbif.org/occurrence/{res.get('key')}",
                    datasetKey=res.get("datasetKey"),
                    datasetName=None,
                    datasetReference=f"https://www.gbif.org/dataset/{res.get('datasetKey')}",
                    license=res.get("license"),
                    basisOfRecord=res.get("basisOfRecord"),
                    mediaType=mediaType,
                    media=media,
                )
            )
    return parsed_results


def update_dataset_names(occ: list):
    unique_dataset_keys = list(set([o.get("datasetKey") for o in occ]))
    dk_dn_mapping = {dk: None for dk in unique_dataset_keys}
    for dk in unique_dataset_keys:
        dk_dn_mapping[dk] = get_dataset_name(dk)
    for i in range(len(occ)):
        occ[i]["datasetName"] = dk_dn_mapping[occ[i].get("datasetKey")]
    return occ


def parse_species_keys_from_results(results, unique=True):
    species_keys = []
    for res in results:
        species_key = res.get("speciesKey")
        if species_keys is not None:
            species_keys.append(species_key)

    if unique:
        return list(set(species_keys))
    else:
        return species_keys


def request_occurencies(
    taxon_key,
    offset,
    limit,
    coordinates: tuple = None,
    radius_km=None,
    date_range: tuple = None,
    country=None,
    media_type=None,
    gadm_gid=None,
    decimal_latitude=None,
    decimal_longitude=None,
    parse=False,
    key_only=False,
):
    if type(taxon_key) == list:
        taxon_key = ",".join(str(x) for x in taxon_key)
    url = "https://api.gbif.org/v1/occurrence/search?taxonKey={taxon_key}".format(
        taxon_key=taxon_key
    )

    if coordinates is not None and radius_km is not None:
        assert type(coordinates) == tuple
        url += "&geoDistance={center_lat},{center_lon},{dist_km}km".format(
            center_lat=coordinates[0], center_lon=coordinates[1], dist_km=radius_km
        )

    if date_range is not None:
        assert type(date_range) == tuple

        if len(date_range) == 2:
            date_range = date_range[0] + "," + date_range[1]
        elif len(date_range) == 1:
            date_range = date_range[0]

        url += "&eventDate={date_range}".format(date_range=date_range)
    if country is not None:
        url += "&country={country}".format(country=country)

    if media_type is not None:
        assert media_type in GBIF_MEDIA_TYPES
        url += "&mediaType={media_type}".format(media_type=media_type)

    if gadm_gid is not None:
        url += "&gadmGid={gadm_gid}".format(gadm_gid=gadm_gid)

    if decimal_latitude is not None:
        assert type(decimal_latitude) == tuple
        lat_min = min(decimal_latitude)
        lat_max = max(decimal_latitude)
        url += "&decimalLatitude={lat_min},{lat_max}".format(
            lat_min=lat_min, lat_max=lat_max
        )

    if decimal_longitude is not None:
        assert type(decimal_longitude) == tuple
        lon_min = min(decimal_longitude)
        lon_max = max(decimal_longitude)
        url += "&decimalLongitude={lon_min},{lon_max}".format(
            lon_min=lon_min, lon_max=lon_max
        )

    url += "&offset={offset}&limit={limit}".format(offset=offset, limit=limit)

    # print(url)
    resp = requests.get(url)
    if resp.status_code == 200:
        try:
            resp_json = resp.json()

            if key_only:
                return parse_species_keys_from_results(
                    resp_json.get("results"), unique=False
                )
            if parse == False:
                return resp_json
            parsed = parse_occurence_results(resp_json.get("results"))
            return parsed
        except Exception as e:
            print("exc!", e)
            return None
    return None


def get_number_of_occurencies(
    taxon_key,
    coordinates: tuple = None,
    radius_km=None,
    date_range: tuple = None,
    country=None,
    media_type=None,
    gadm_gid=None,
    decimal_latitude=None,
    decimal_longitude=None,
):
    if type(taxon_key) == list:
        taxon_key = ",".join(str(x) for x in taxon_key)
    url = "https://api.gbif.org/v1/occurrence/search?taxonKey={taxon_key}".format(
        taxon_key=taxon_key
    )

    if coordinates is not None and radius_km is not None:
        assert type(coordinates) == tuple
        url += "&geoDistance={center_lat},{center_lon},{dist_km}km".format(
            center_lat=coordinates[0], center_lon=coordinates[1], dist_km=radius_km
        )

    if date_range is not None:
        assert type(date_range) == tuple

        if len(date_range) == 2:
            date_range = date_range[0] + "," + date_range[1]
        elif len(date_range) == 1:
            date_range = date_range[0]

        url += "&eventDate={date_range}".format(date_range=date_range)
    if country is not None:
        url += "&country={country}".format(country=country)

    if media_type is not None:
        assert media_type in GBIF_MEDIA_TYPES
        url += "&mediaType={media_type}".format(media_type=media_type)

    if gadm_gid is not None:
        url += "&gadmGid={gadm_gid}".format(gadm_gid=gadm_gid)

    if decimal_latitude is not None:
        assert type(decimal_latitude) == tuple
        lat_min = min(decimal_latitude)
        lat_max = max(decimal_latitude)
        url += "&decimalLatitude={lat_min},{lat_max}".format(
            lat_min=lat_min, lat_max=lat_max
        )

    if decimal_longitude is not None:
        assert type(decimal_longitude) == tuple
        lon_min = min(decimal_longitude)
        lon_max = max(decimal_longitude)
        url += "&decimalLongitude={lon_min},{lon_max}".format(
            lon_min=lon_min, lon_max=lon_max
        )

    url += "&offset={offset}&limit={limit}".format(offset=0, limit=1)

    # print(url)
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json().get("count")
    return None


def get_species_keys_from_occurences(
    taxon_key,
    coordinates: tuple = None,
    radius_km=None,
    date_range: tuple = None,
    country=None,
    media_type=None,
    gadm_gid=None,
    decimal_latitude=None,
    decimal_longitude=None,
    total_limit=100000,
    unique=True,
):
    species_keys = []
    offset = 0
    limit = 100
    resp = request_occurencies(
        taxon_key,
        offset=offset,
        limit=limit,
        coordinates=coordinates,
        radius_km=radius_km,
        date_range=date_range,
        country=country,
        media_type=media_type,
        gadm_gid=gadm_gid,
        decimal_latitude=decimal_latitude,
        decimal_longitude=decimal_longitude,
    )
    species_keys += parse_species_keys_from_results(resp.get("results"), unique=unique)
    eor = resp.get("endOfRecords")
    if eor == False:
        remaining_records = resp.get("count") - (limit + offset)
        assert remaining_records < (total_limit - (limit + offset))

        no_steps = int(round(remaining_records / limit + 0.5))
        offset += limit
        offsets = [offset + (limit * i) for i in range(no_steps)]
        with ThreadPoolExecutor(max_workers=None) as executor:
            thread_results = [
                executor.submit(
                    request_occurencies,
                    taxon_key,
                    offset=offset_t,
                    limit=limit,
                    coordinates=coordinates,
                    radius_km=radius_km,
                    date_range=date_range,
                    country=country,
                    media_type=media_type,
                    gadm_gid=gadm_gid,
                    decimal_latitude=decimal_latitude,
                    decimal_longitude=decimal_longitude,
                    parse=False,
                    key_only=True,
                )
                for offset_t in offsets
            ]
        for future in thread_results:
            if unique:
                species_keys = list(set(species_keys + future.result()))

            else:
                species_keys += future.result()

    return species_keys


def get_occurences(
    taxon_key,
    coordinates: tuple = None,
    radius_km=None,
    date_range: tuple = None,
    country=None,
    media_type=None,
    gadm_gid=None,
    decimal_latitude=None,
    decimal_longitude=None,
    total_limit=100000,
):
    parsed_results = []

    offset = 0
    limit = 100
    resp = request_occurencies(
        taxon_key,
        offset=offset,
        limit=limit,
        coordinates=coordinates,
        radius_km=radius_km,
        date_range=date_range,
        country=country,
        media_type=media_type,
        gadm_gid=gadm_gid,
        decimal_latitude=decimal_latitude,
        decimal_longitude=decimal_longitude,
    )
    parsed_results += parse_occurence_results(resp.get("results"))

    eor = resp.get("endOfRecords")
    if eor == False:
        remaining_records = min(
            resp.get("count") - (limit + offset), total_limit - limit
        )

        no_steps = int(round(remaining_records / limit + 0.5))
        offset = limit

        offsets = [offset + (limit * i) for i in range(no_steps)]

        with ThreadPoolExecutor(max_workers=None) as executor:
            thread_results = [
                executor.submit(
                    request_occurencies,
                    taxon_key,
                    offset=offset_t,
                    limit=limit,
                    coordinates=coordinates,
                    radius_km=radius_km,
                    date_range=date_range,
                    country=country,
                    media_type=media_type,
                    gadm_gid=gadm_gid,
                    decimal_latitude=decimal_latitude,
                    decimal_longitude=decimal_longitude,
                    parse=True,
                )
                for offset_t in offsets
            ]
        for future in thread_results:
            parsed_results += future.result()

    return parsed_results
