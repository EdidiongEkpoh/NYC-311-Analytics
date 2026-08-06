# NYC 311 Service Requests

An end-to-end analytics project on NYC's 311 service request data
that features a scheduled ingestion, a tested SQL transformation layer, and a live dashboard.

**Problem Statement**: What Drives Response Time and Complaint Volume Across New York City?

NYC 311 service requests are formal calls for help, inspection, and/or fix sent to the city stemming from a resident. It features issues like noise complaints, cleaning graffiti,  restoring apartment heat, as well as hundreds of others. It's structurally similar to a support-ticket or ops dataset in industry. There are volume patterns, resolution-time variance, and geographic/temporal disparities in service. This project mainly focuses on two angles:

- **Geography** - Does reponse swiftness meaningfully vary by borough or community board, independent of complaint type?
- **Seasonality** - What's cyclical (time of day, day of week, month) versus what's a genuine trend in complaint volume over time? 

## Data 

[NYC Open Data -- 311 Service Requests from 2010 to Present](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2010-to-Present/erm2-nwe9) (Socrata dataset `erm2-nwe9`)

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

1. `src/ingest.py` utilizes the API endpoint (dataset `erm2-nwe9`) to collect NYC 311 service request data in monthly batches, scoped to the user's desired date range and/or max-record cap for testing. Ingesting and grouping the data by month keeps memory bounded regardless of how far back the pull goes.
2. Each monthly batch is written to disk and checkpointed (`data/raw/_checkpoint.json`) before the next chunk starts. If the script is interrupted partway through a large backfill, re-running resumes from the last completed month opposed to starting from scratch.
3. Data is written in a partitioned Parquet files (`data/raw/created_year=YYYY/created_month=MM/part.parquet`), deduplicated on `unique_key` within each write. Partitioning keeps individual files small enough for git diffs and lets downstream tools prune by partition instead of scanning all of the data
4. Every run appends one row per batch to `data/raw/ingest_log.csv` in order to automate documentation.
5. `.github/workflows/ingest.yml` runs the script daily on a schedule (as well as manual trigger via `workflow_dispatch`) and commits new partitions back to the repo. 
6. `dbt/models/staging/311_sources.yml` points directly at the committed Parquet via DuckDB's `read_parquet()`. The warehouse always reflects what's on the disk in the repo. A `freshness` check on this source also verifies the daily GitHub Action is still running.
7. The staging model (`stg_311_service_requests`) deduplicates, casts types, and documents every column, with tests split by severity. It includes hard failures for data integrity problems (duplicate and/or null `unique_key`s), warnings for known and documented issues (`closed_date` occasionally preceding `created_date`).
8. The intermediate model (`int_311_service_requests`) adds response time, day-of-week/time-of-day classifications, and an explicit `is_response_time_valid` flag. It keeps derived/analytical logic separate from the staging's raw data. The `is_response_time_valid` is used to judge the quality of an ingested row based on whether it has a faulty combination of `closed_date` and `created_date` (see #7) rather than just excluding it altogether.
9. Five mart tables that aggregate to provide detail about the geography (`mart_geo_borough.sql`, `mart_geo_borough_overall`, and `mart_geo_community_board.sql`) and seasonality (`mart_time_monthly_volume.sql` and `mart_time_weekday_hour.sql`) variables. 
10. `.github/workflows/dbt_ci.yml` runs `dbt build` on every push so it catches changes that would break the pipeline instantly.


## Setup / How to Run (Ingestion)

### 1. Python environment
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. (Recommended) Get a Free Socrata App Token
Register and sign in [here](https://data.cityofnewyork.us/signup), then click on your display name in the top right corner of the screen 
and go to `Developer Settings`, and then click `Create New App Token`, fill out the required information
and copy and paste the `App Token` in as `SOCRATA_APP_TOKEN` in your .env file. 
Without a token, requests work but share Socrata's throttled anonymous rate limit.
(*Note*: Use an incognito window if the `Create New App Token` button is unresponsive in your browser.)

### 3. First Run
The very first run needs an explicit starting point. The full dataset
back to 2010 is 24M+ rows, but I would recommend just going back as far as 2023 or 2024 at first.

```bash
python src/ingest.py --since 2024-01-01
```

For a quick sanity test before final pull.
```bash
python src/ingest.py --since 2024-01-01 --max-records 5000
```

### 4. Subsequent Runs
```bash
python src/ingest.py
```
Reads `data/raw/_checkpoint.json` and only pulls records created since the
last successful run.

### 5. Automated Daily Runs (GitHub Actions)
Once this repo is pushed to GitHub:
1. Repo Settings -> Secrets and variables -> Actions -> add `SOCRATA_APP_TOKEN`.
2. The workflow in `.github/workflows/ingest.yml` runs daily at 09:00 UTC
   and commits new partition files back to the repo. Trigger it manually
   from the Actions tab to confirm it works before waiting for the schedule.


## Setup / How to run (dbt)

Assumes the ingestion setup above is already done and `data/raw/` has
data in it, the dbt project reads directly from those Parquet files.

### 1. Install Dependencies
Already covered if you did the ingestion setup — `dbt-core` and
`dbt-duckdb` are both in `requirements.txt`. If using VS Code as code editor, 
I'd highly recommend installing the `dbt` extension for faster processing:
```bash
pip install -r requirements.txt
```

### 2. Create a Local dbt Profile
dbt looks for connection details in `~/.dbt/profiles.yml` by default. It's
outside the repo, since this file conventionally holds credentials.

```bash
mkdir -p ~/.dbt
```
Then save the following as `~/.dbt/profiles.yml`:
```yaml
nyc311:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: 'nyc311_dev.duckdb'
      threads: 4
```

### 3. Confirm the Connection
```bash
cd dbt
dbt debug
```
Should report the project and profile as valid, and the DuckDB
connection as `OK`.

### 4. Build
```bash
dbt build
```
Runs every model (staging, intermediate, marts) and every test in
dependency order. Expect a handful of `WARN`s on a full run against real
data — these are documented, known characteristics of the source data
(see step 7 above), not failures. Only an `ERROR` means something's broken.

### 5. Automated Checks (GitHub Actions)
`.github/workflows/dbt_ci.yml` runs `dbt build` on every push to `main`.
Unlike the ingestion workflow, **no repo secret is required**. The
workflow generates its own `~/.dbt/profiles.yml` inline as a step, since
nothing in it is sensitive. Trigger it manually from the Actions tab via
`workflow_dispatch` to confirm it passes.

## Setup / How to run (Dashboard)

Assumes the dbt setup above is already done — the dashboard reads
directly from the `.duckdb` file `dbt build` produces.

### 1. Install Node.js (≥20)
Evidence requires Node ≥18.13, 20, or 22. Check your version:
```bash
node -v
```
If it's below 20, `brew install node` (or `brew upgrade node` if your
existing install came from Homebrew).

### 2. Install dependencies
```bash
cd evidence
npm install
```

### 3. Connect the data source
Evidence reads a DuckDB file placed inside `evidence/sources/nyc311/`:
```bash
dbt build          # from dbt/, if not already done
cp dbt/nyc311_dev.duckdb evidence/sources/nyc311/nyc311.duckdb
npm run sources     # from evidence/ -- extracts each mart into Evidence's cache
```

### 4. Run locally
```bash
npm run dev
```
Opens the dashboard at `http://localhost:3000`.

### 5. Automated deploy (GitHub Actions)
`.github/workflows/dashboard.yml` runs the full chain above plus
`npm run build` and a deploy to GitHub Pages automatically. Dependent on
`dbt_ci.yml` succeeding first (so a broken dbt test blocks a broken
dashboard from publishing). One-time setup required before this works:
Settings -> Pages -> Source -> GitHub Actions.

**[Live Dashboard →](https://edidiongekpoh.github.io/NYC-311-Analytics/)**


## Exporting for Other BI Tools (Tableau, Power BI)

`src/export_csv.py` exports every mart table — and, optionally, the
intermediate model — to standalone CSV files in `data/exports/` (local
only, gitignored). Not part of the automated pipeline; run manually
whenever you actually need fresh CSVs for another tool.

```bash
python src/export_csv.py
```

**To also export the intermediate model** (`int_311__requests_enriched`,
row-level, not aggregated): temporarily set
`intermediate: +materialized: table` in `dbt/dbt_project.yml`, run
`dbt build`, then run the export script.

> **Revert `intermediate` back to `+materialized: view` immediately
> after.** Leaving it as `table` isn't the project's intended state — a
> view always reflects the current data; a table only updates when
> explicitly rebuilt, meaning it can silently drift stale. It also grows
> every `.duckdb` file this project produces (local, CI, and the
> deployed dashboard's build) for no benefit to `dbt_ci.yml` or
> `dashboard.yml`, since only the marts read the intermediate model directly.