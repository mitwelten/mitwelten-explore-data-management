# Mitwelten Explore Data Management

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