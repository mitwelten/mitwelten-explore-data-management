# Mitwelten Explore Data Management

## API usage

API Documentation: [data.mitwelten.org/api/v3/docs](https://data.mitwelten.org/api/v3/docs)

* [Python examples](api-usage/python/)
* [R examples](api-usage/R/)
* JavaScript examples on ObservableHQ
  * [most active birds](https://observablehq.com/@timeo-wullschleger/mitwelten-most-active-birds)
  * [daily bird detections visualizes as calendar plot](https://observablehq.com/@timeo-wullschleger/mitwelten-birds-calendar)
  * [bird detections by taxon id](https://observablehq.com/@timeo-wullschleger/mitwelten-detected-birds)


## Data ingest

Install the dependencies to run the scripts:
```sh
cd mitwelten-explore-data-management/ingest
pip install -r requirements.txt
```

### GBIF-Cache-DB update

Execute the cells in the [update_gbif_cache](ingest/gbif/update_gbif_cache.ipynb) notebook.

### Insert new meteo measurements

1. Download a dataset from IDAWEB
2. Navigate to `ingest/meteo/`
   ```sh
   cd mitwelten-explore-data-management/ingest/meteo/
   ```
3. Make a copy of the file and edit the credentials
   ```sh
   cp credentials.example.yaml credentials.yaml
   nano credentials.yaml
   ```
4. Execute the insert script
   ```sh
   python insert_from_zip.py -c credentials.yaml  -i /path/to/the/zip.file
   ```
   Required arguments:
   - `-c`: path to the credentials file
   - `-i`: path to the downloaded zip file