# NYC 311 Service Requests

An end-to-end analytics project on NYC's 311 service request data
that features a scheduled ingestion, a tested SQL transformation layer, and a live dashboard.

`Main Problem Statement`: What Drives Response Time and Complaint Volume Across New York City

## Data 

**Source**: [NYC Open Data -- 311 Service Requests from 2010 to Present](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2010-to-Present/erm2-nwe9) (Socrata dataset `erm2-nwe9`)

### Raw Data Dictionary via `src/ingest.py`

| Column | Description |
|---|---|
| `unique_key` | Unique ID for the service request |
| `created_date` / `closed_date` | Timestamps the request was opened / closed |
| `agency` / `agency_name` | Responding city agency |
| `complaint_type` / `descriptor` | Complaint category and sub-category |
| `location_type` | Type of location (e.g. "Street/Sidewalk", "Residential Building") |
| `incident_zip` / `incident_address` / `street_name` / `borough` | Location fields |
| `status` | Current status (Open, Closed, etc.) |
| `resolution_action_updated_date` | Last time the resolution status changed |
| `community_board` | NYC community board |
| `open_data_channel_type` | How the request was filed (phone, app, web, etc.) |
| `latitude` / `longitude` | Geocoded location |

Full field definitions: [dataset's official data dictionary](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2010-to-Present/erm2-nwe9/about_data).

## Project Workflow 

1. `src/ingest.py` utilizes the API endpoint (dataset erm2-nwe9) to collect NYC 311 service request day in batches of months (depending on user's desired date range and/or max records pulled.)
2. ...


## Setup / How to run (Week 1: ingestion only)

### 1. Python environment
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. (An available option, but not a necessity) Get a free Socrata app token
Register and sign in [here](https://data.cityofnewyork.us/signup), then go to `Developer Settings`, and 
then click `Create New App Token` and paste it in as `SOCRATA_APP_TOKEN` in your .env. Without a
token, requests work but share Socrata's throttled anonymous rate limit.
(*Note*: The `Create New App Token` button was unresponsive for me as of July 25th, 2026. However, I have been 
able to make calls to the API seamlessly without it.)

### 3. First run
The very first run needs an explicit starting point. The full dataset
back to 2010 is 24M+ rows, but I would recommend just going back as far as 2023 or 2024 at first.

```bash
python src/ingest.py --since 2024-01-01
```

For a quick sanity test before final pull.
```bash
python src/ingest.py --since 2024-01-01 --max-records 1000000
```

### 4. Subsequent runs
```bash
python src/ingest.py
```
Reads `data/raw/_checkpoint.json` and only pulls records created since the
last successful run.

### 5. Automated daily runs (GitHub Actions)
Once this repo is pushed to GitHub:
1. Repo Settings -> Secrets and variables -> Actions -> add `SOCRATA_APP_TOKEN`.
2. The workflow in `.github/workflows/ingest.yml` runs daily at 09:00 UTC
   and commits new partition files back to the repo. Trigger it manually
   from the Actions tab to confirm it works before waiting for the schedule.
