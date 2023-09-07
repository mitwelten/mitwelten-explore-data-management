from enum import Enum
import requests
from urllib.parse import urlencode
import logging
import datetime

logging.basicConfig(
    format="%(asctime)s.%(msecs)03d %(levelname)s : %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)

BASE_URL = "https://data.mitwelten.org/api/v3/"


class TimeSeriesResult:
    def __init__(self, timestamps=[], values=[]):
        self.timestamps = timestamps
        self.values = values
        self.total = sum(values)


class TimeOfDayResult:
    def __init__(self, minute_of_day=[], values=[]):
        self.minute_of_day = minute_of_day
        self.values = values
        self.formatted_time = [
            str(datetime.timedelta(seconds=m * 60)) for m in self.minute_of_day
        ]


##### Birds ######


def taxon_key_lookup(name: str):
    names = name.lower().split()
    name = " ".join([names[0].title()] + names[1:])
    logging.info(f"taxon key lookup for {name}")
    # get taxon_key
    url = f"{BASE_URL}taxonomy/sci/{name}"
    req = requests.get(url)
    if req.status_code != 200:
        logging.error(f"invalid request. status code={req.status_code} for url {url}")
        return TimeSeriesResult()
    taxonomy_tree = req.json()
    return taxonomy_tree[0].get("datum_id")


def get_bird_detections(
    taxon_key: int = None,
    name: str = None,
    confidence: float = 0.7,
    bucket_width="1d",
    time_from=None,
    time_to=None,
    distinct_species=False,
) -> TimeSeriesResult:
    if taxon_key is None:
        if name:
            taxon_key = taxon_key_lookup(name)
        else:
            logging.error("No name or taxon_key provided.")
            return TimeSeriesResult()
    params = dict(
        conf=confidence, bucket_width=bucket_width, distinctspecies=distinct_species
    )
    if time_from:
        params["from"] = time_from
    if time_to:
        params["to"] = time_to
    url = f"{BASE_URL}birds/{taxon_key}/date?{urlencode(params)}"
    req = requests.get(url)
    if req.status_code != 200:
        logging.error(f"invalid request. status code={req.status_code} for url {url}")
        return TimeSeriesResult()
    detections = req.json()
    return TimeSeriesResult(detections.get("bucket"), detections.get("detections"))


def get_bird_tod(
    taxon_key: int = None,
    name: str = None,
    confidence: float = 0.7,
    bucket_width_m=60,
    time_from=None,
    time_to=None,
    distinct_species=False,
) -> TimeOfDayResult:
    if taxon_key is None:
        if name:
            taxon_key = taxon_key_lookup(name)
        else:
            logging.error("No name or taxon_key provided.")
            return TimeOfDayResult()
    params = dict(
        conf=confidence, bucket_width_m=bucket_width_m, distinctspecies=distinct_species
    )
    if time_from:
        params["from"] = time_from
    if time_to:
        params["to"] = time_to
    url = f"{BASE_URL}birds/{taxon_key}/time_of_day?{urlencode(params)}"
    req = requests.get(url)
    if req.status_code != 200:
        logging.error(f"invalid request. status code={req.status_code} for url {url}")
        return TimeOfDayResult()
    detections = req.json()
    return TimeOfDayResult(detections.get("minuteOfDay"), detections.get("detections"))


class PollinatorCat(str, Enum):
    all = None
    apis = "honigbiene"
    apidae = "wildbiene"
    bombus = "hummel"
    muscidae = "fliege"
    syrphidae = "schwebfliege"


def get_pollinator_detections(
    cat: PollinatorCat = None,
    confidence: float = 0.7,
    bucket_width="1d",
    time_from=None,
    time_to=None,
) -> TimeSeriesResult:

    params = dict(
        conf=confidence,
        bucket_width=bucket_width,
    )
    if time_from:
        params["from"] = time_from
    if time_to:
        params["to"] = time_to
    if cat:
        params["pollinator_class"] = cat.value
    url = f"{BASE_URL}pollinators/date?{urlencode(params)}"
    req = requests.get(url)
    if req.status_code != 200:
        logging.error(f"invalid request. status code={req.status_code} for url {url}")
        return TimeSeriesResult()
    detections = req.json()
    return TimeSeriesResult(detections.get("bucket"), detections.get("detections"))


def get_pollinator_tod(
    cat: PollinatorCat = None,
    confidence: float = 0.7,
    bucket_width_m=60,
    time_from=None,
    time_to=None,
) -> TimeOfDayResult:

    params = dict(
        conf=confidence,
        bucket_width_m=bucket_width_m,
    )
    if time_from:
        params["from"] = time_from
    if time_to:
        params["to"] = time_to
    if cat:
        params["pollinator_class"] = cat.value
    url = f"{BASE_URL}pollinators/time_of_day?{urlencode(params)}"
    req = requests.get(url)
    if req.status_code != 200:
        logging.error(f"invalid request. status code={req.status_code} for url {url}")
        return TimeOfDayResult()
    detections = req.json()
    return TimeOfDayResult(detections.get("minuteOfDay"), detections.get("detections"))


"""
print(get_bird_detections(name="apus").total)
print(get_bird_detections(taxon_key=212).total)
print(get_bird_tod(taxon_key=212, bucket_width_m=30).formatted_time)
det = get_pollinator_tod(cat=PollinatorCat.bombus)
print(det.formatted_time, det.values)

"""
