'''
Pulls NYC 311 Service Request records from the Socrata Open Data API and 
writes them into append-only Parquet files under data/raw/.
'''

import argparse 
import json 
import logging 
import os 
import time 
from datetime import datetime, timezone, date
from pathlib import Path 
import pandas as pd 
import requests 
from dotenv import load_dotenv 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

API_ENDPOINT = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
PAGE_SIZE = 50000
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 5 

COLUMNS = [
    'unique_key', 'created_date', 'closed_date', 'agency', 'agency_name',
    'complaint_type', 'descriptor', 'location_type', 'incident_zip', 'incident_address',
    'street_name', 'borough', 'status', 'resolution_action_updated_date', 'community_board',
    'open_data_channel_type', 'latitude', 'longitude'
    ]

DEFAULT_CHECKPOINT_FILE = Path(__file__).parent.parent / 'data' / 'raw' / '_checkpoint.json'
DEFAULT_DATA_DIR = Path(__file__).parent.parent / 'data' / 'raw'
DEFAULT_LOG_FILE = Path(__file__).parent.parent / 'data' / 'raw' / 'ingest_log.csv'
LOG_COLUMNS = ['run_at', 'batch_start', 'batch_end', 'records', 'seconds', 'status', 'detail']

def load_checkpoint(checkpoint_file: Path):
    '''
    Returns the last created_date successfully pulled, or None if this is the first run.
    '''
    if not checkpoint_file.exists():
        return None
    with open(checkpoint_file) as f:
        return json.load(f).get('last_created date')

def save_checkpoint(checkpoint_file: Path, last_created_date: str):
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    with open(checkpoint_file, 'w') as f:
        json.dump({'last_created_date': last_created_date, 'saved_at': datetime.now(timezone.utc).isoformat()}, f)
    logger.info(f"Checkpoint saved: last_created_date: {last_created_date}")

def log_batch_result(log_file: Path, batch_start: str, batch_end: str, records: int, seconds: float, status: str, detail: str=""):
    log_file.parent.mkdir(parents=True, exist_ok=True)
    row = pd.DataFrame([{
        'run_at': datetime.now(timezone.utc).isoformat(),
        'batch_start': str(batch_start),
        'batch_end': str(batch_end),
        'records': records,
        'seconds': round(seconds, 1),
        'status': status,
        'detail': detail
    }])

    row.to_csv(log_file, mode='a', header=not log_file.exists(), index=False)

def month_batches(since: pd.Timestamp, until: pd.Timestamp):
    current = since 
    while current < until:
        next_boundary = (current.replace(day=1) + pd.DateOffset(months=1))
        batch_end = min(next_boundary, until)
        yield current, batch_end 
        current = batch_end

def build_headers() -> dict:
    token = os.environ.get('SOCRATA_APP_TOKEN')
    headers = {"X-App_Token": token} if token else {}
    if not token: 
        logger.warning('No SOCRATA_API_TOKEN, using the shared anonymous rate limit. ' \
        'Get free token here: https://data.cityofnewyork.us/profile/app_tokens'
        )
    return headers 

def fetch_page(headers: dict, since: str, until: str, offset: int, limit: int) -> list:
    where = f"created_date > '{since}' AND created_date <= '{until}'"
    params = {
        '$select': ",".join(COLUMNS),
        '$where': where,
        '$order': "created_date",
        '$limit': limit,
        '$offset': offset
    }
    for attempt in range(1, MAX_RETRIES + 1):
        try: 
            resp = requests.get(API_ENDPOINT, params=params, headers=headers, timeout=60)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            if attempt == MAX_RETRIES:
                logger.error(f"Failed after {MAX_RETRIES} attempts at offset={offset}.")
                raise 
            wait = RETRY_BACKOFF_SECONDS * attempt 
            logger.warning(f"Request error (attempt {attempt} / {MAX_RETRIES}): {e}. Retrying in {wait} seconds...")
            time.sleep(wait)


def fetch_new_records(since: str, until: str, headers: dict, max_records=None) -> pd.DataFrame:
    '''
    Iterates through every record created after `since`, oldest first.
    '''

    all_rows = []
    offset = 0

    while True:
        remaining = None if max_records is None else max_records - len(all_rows)
        if remaining is not None and remaining <= 0:
            break 
        limit = PAGE_SIZE if remaining is None else min(PAGE_SIZE, remaining)

        page = fetch_page(headers, since, until, offset, limit)
        if not page:
            break

        all_rows.extend(page)
        offset += len(page)
        logger.info(f"Pulled {len(all_rows)} records so far...")

        if len(page) < limit:
            break
    if not all_rows:
        return pd.DataFrame(columns=COLUMNS)

    df = pd.DataFrame(all_rows)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA # Socrata omits fields that are null for every row in a page

    return df[COLUMNS]


def write_partitioned(df: pd.DataFrame, data_dir: Path):
    '''
    Appends new rows to monthly Parquet partitions 
    (created_year=YYYY/created_month=MM/part.parquet). It merges with whatever is 
    already in that partition.
    '''

    if df.empty:
        logger.info("No new records to write.")
        return 

    df['created_date'] = pd.to_datetime(df['created_date'])
    df['year'] = df['created_date'].dt.year 
    df['month'] = df['created_date'].dt.month 

    for (year, month), group in df.groupby(['year', 'month']):
        partition_dir = data_dir / f"created_year={year}" / f"created_month={month:02d}"
        partition_dir.mkdir(parents=True, exist_ok=True)
        part_path = partition_dir / 'part.parquet'

        group = group.drop(columns=['year', 'month'])
        if part_path.exists():
            existing = pd.read_parquet(part_path)
            combined = pd.concat([existing, group], ignore_index=True)
            combined = combined.drop_duplicates(subset='unique_key', keep='last')
        else:
            combined=group 

        combined.to_parquet(part_path, index=False)
        logger.info(f"Wrote {len(combined)} rows to {part_path}.")


def main():
    parser = argparse.ArgumentParser(description='Incrementally pulls NYC 311 data into partitioned Parquet file.')
    parser.add_argument(
        '--since',
        type=str,
        default=None,
        help='Force a starting created_date (YYYY-MM-DD), overriding the checkpoint. ' \
        'Use this for the very first run to dictate how much history is pulled.'
    )
    parser.add_argument(
        '--max-records',
        type=int,
        default=None,
        help='Cap the number of records pulled.'
    )
    parser.add_argument('--data-dir', type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument('--checkpoint-file', type=Path, default=DEFAULT_CHECKPOINT_FILE)
    parser.add_argument('--log-file', type=Path, default=DEFAULT_LOG_FILE)
    args = parser.parse_args()

    load_dotenv()
    headers = build_headers()

    since_str = args.since or load_checkpoint(args.checkpoint_file)
    if since_str is None:
        raise SystemExit('No checkpoint founded (--since not provided). ' \
        'If this is the first run, pick a starting point explictly (e.g -- since 2025-01-01).')

    since = pd.Timestamp(since_str)
    until = pd.Timestamp.today()
    batches = list(month_batches(since, until))

    if not batches:
        logger.info('Nothing new since last checkpoint.')
        return 
    if args.max_records is None:
        logger.info(f"Backfilling {len(batches)} months from {since.date()} to {until.date()}.")
    else:
        logger.info(f"Backfilling {args.max_records} records since {since.date()}.")

    total_records = 0 
    total_batches = 0
    for batch_start, batch_end in batches:
        if args.max_records is not None and total_records >= args.max_records:
            logger.info(f"Reached maximum records ({args.max_records}) stopping before {batch_start.strftime('%Y-%m')}.")
            break
        batch_budget = None if args.max_records is None else args.max_records - total_records
        t0 = time.time() 
        try:
            df = fetch_new_records(batch_start.date().isoformat(), batch_end.date().isoformat(), headers, max_records=batch_budget)
            elapsed = time.time() - t0

            if df.empty:
                logger.info(f"[{batch_start.strftime('%Y-%m')}] No records in this range.")
                log_batch_result(args.log_file, batch_start, batch_end, 0, elapsed, 'empty')
                save_checkpoint(args.checkpoint_file, batch_end.date().isoformat())
                continue 

            write_partitioned(df, args.data_dir)
            latest_fetched = pd.Timestamp(df['created_date'].max())
            save_checkpoint(args.checkpoint_file, latest_fetched.date().isoformat())


                
            total_records += len(df)
            total_batches += 1
            log_batch_result(args.log_file, batch_start, batch_end, len(df), elapsed, 'success')
            logger.info(f"[{batch_start.strftime('%Y-%m')}] {len(df)} records written in {elapsed:.1f} seconds.")

        except Exception as e:
            elapsed = time.time() - t0 
            log_batch_result(args.log_file, batch_start, batch_end, 0, elapsed, 'failed', detail=str(e))
            logger.error(f"[{batch_start.strftime('%Y-%m')}] Failed after {elapsed:.1f} seconds: {e}.")
            logger.error("Checkpoint was not advanced past this batch. Re-running the script, will retry starting from here.")
            raise 

    logger.info(f"Done. {total_records} total records across {total_batches} batch(es). See {args.log_file} for elapsed times per batch.")
if __name__ == '__main__':
    main()
    