'''
Exports all dbt mart tables as well as the intermediate table (if materialized
as `table` in `dbt/dbt_project.yml`) to a standalone CSV file in data/exports.
This is for the use of integration into BI tools like Tableau and Power BI.
This script is meant to just be ran manually when needed and makes no
modifications to the data warehouse.
 
Note: the intermediate models (`int_311*`) can only be exported when they are
materialized as `table` in dbt_project.yml. If they are materialized as
`view` (dbt's default), this script will skip them and only export the mart
tables, since `export_table_to_csv` relies on the object existing as a
physical table in the DuckDB catalog.
'''

import argparse 
import logging
from pathlib import Path
import duckdb 
import yaml
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

DEFAULT_DUCKDB_PATH = Path(__file__).parent.parent / 'dbt' / 'nyc311_dev.duckdb'
DEFAULT_EXPORT_DIR = Path(__file__).parent.parent / 'data' / 'exports'
DEFAULT_DBT_PROJECT_FILE = Path(__file__).parent.parent / 'dbt' / 'dbt_project.yml'

def get_intermediate_tables(con) -> list:
    '''
        Gets all tables that match the "int_311*" naming convention.
    '''
    rows = con.execute(
        "SELECT table_name " \
        "FROM information_schema.tables " \
        "WHERE LOWER(table_name) LIKE 'int_311%' "
        "AND table_type = 'BASE TABLE' " \
        "ORDER BY 1" \
        ).fetchall()
    return [r[0] for r in rows]

def get_mart_tables(con) -> list:
    '''
    Gets all tables that match the "mart_*" naming convention.
    '''
    rows = con.execute(
        "SELECT table_name " \
        "FROM information_schema.tables " \
        "WHERE LOWER(table_name) LIKE 'mart_%' " \
        "AND table_type = 'BASE TABLE' " \
        "ORDER BY 1" \
    ).fetchall()
    return [r[0] for r in rows]

def get_intermediate_materialization_type(dbt_project_path: Path) -> str:
    '''
    Reads the dbt_project.yml file and returns the materialization type for the intermediate model.
    '''
    with open(dbt_project_path, 'r') as f:
        dbt_project = yaml.safe_load(f)
    return dbt_project.get('models', {}).get('nyc_311_analytics', {}).get('intermediate', {}).get('+materialized', 'view')
    
    
def export_table_to_csv(con, table_name: str, export_dir: Path) -> int:
    export_path = export_dir / f"{table_name}.csv"    
    con.execute(f"COPY (SELECT * FROM {table_name}) TO '{export_path}' (HEADER, DELIMITER ',') ")
    row_count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    logger.info(f"Exported {table_name} -> {export_path} ({row_count} rows).")
    return row_count 

def main():
    parser = argparse.ArgumentParser(description="Export dbt mart tables to CSV files.")
    parser.add_argument("--duckdb-path", type=Path, default=DEFAULT_DUCKDB_PATH, help="Path to the DuckDB database file.")
    parser.add_argument("--export-dir", type=Path, default=DEFAULT_EXPORT_DIR, help="Directory to save the exported CSV files.")
    parser.add_argument("--dbt-project-file", type=Path, default=DEFAULT_DBT_PROJECT_FILE, help="Path to the dbt_project.yml file.")
    args = parser.parse_args()

    if not args.duckdb_path.exists():
        raise SystemExit(f"DuckDB database file not found: {args.duckdb_path}")
    args.export_dir.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(args.duckdb_path), read_only=True)
    
    mart_tables = get_mart_tables(con)

    if not mart_tables:
        logger.warning("No tables found matching the 'mart_*' naming convention.")

    intermediate_materialization = get_intermediate_materialization_type(args.dbt_project_file)
    intermediate_table = []
    if intermediate_materialization == "table":
        intermediate_table = get_intermediate_tables(con)
        if not intermediate_table:
            logger.warning("No tables found matching the 'int_311*' naming convention.")
    else:
        logger.info(f"Intermediate models are materialized as '{intermediate_materialization}' in dbt_project.yml; skipping export of intermediate tables.") 

    if not mart_tables and not intermediate_table:
        logger.warning("No tables found matching the 'mart_*' or 'int_311*' naming convention.")
        return
    start_time = time.time()
    total_rows = 0
    for table in mart_tables + intermediate_table:
        total_rows += export_table_to_csv(con, table, args.export_dir)
    logger.info(f"Done. {len(mart_tables) + len(intermediate_table)} table(s), {total_rows} total rows exported to {args.export_dir}.")
    logger.info(f"Total time: {time.time() - start_time:.2f} seconds.")
if __name__ == "__main__":
    main()
