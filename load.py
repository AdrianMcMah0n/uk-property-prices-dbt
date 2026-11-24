"""Download HM Land Registry Price Paid Data and load it, untouched, into raw.price_paid.

    python load.py 2025        # one full year (about 170 MB)
    python load.py monthly     # the latest monthly update (about 17 MB)

Idempotent: rows from the same source file are deleted and re-loaded in one transaction, so running it
twice never doubles the data. All cleaning and typing happens later, in dbt.
"""
import sys
import time
from pathlib import Path

import psycopg
import requests

BASE = "http://prod.publicdata.landregistry.gov.uk.s3-website-eu-west-1.amazonaws.com/"
DSN = "host=localhost port=5433 dbname=property user=analytics password=analytics"
COLUMNS = ["transaction_id", "price", "date_of_transfer", "postcode", "property_type", "old_new", "duration",
           "paon", "saon", "street", "locality", "town_city", "district", "county", "ppd_category_type",
           "record_status"]
DDL = f"""
create schema if not exists raw;
create table if not exists raw.price_paid (
    {", ".join(f"{c} text" for c in COLUMNS)},
    source_file text not null,
    loaded_at timestamptz not null default now()
);
"""


def download(name: str, folder: Path) -> Path:
    path = folder / name
    if path.exists():
        print(f"using cached {path} ({path.stat().st_size / 1e6:.1f} MB)")
        return path
    folder.mkdir(exist_ok=True)
    part = path.with_suffix(".part")
    have = part.stat().st_size if part.exists() else 0
    headers = {"Range": f"bytes={have}-"} if have else {}
    print(f"downloading {name}" + (f", resuming after {have / 1e6:.1f} MB" if have else "") + " ...")
    with requests.get(BASE + name, stream=True, timeout=60, headers=headers) as r:
        r.raise_for_status()
        resumed = r.status_code == 206  # the server honoured the Range header
        with part.open("ab" if resumed else "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    part.rename(path)  # only a complete download gets the real name
    print(f"saved {path} ({path.stat().st_size / 1e6:.1f} MB)")
    return path


def load(path: Path) -> int:
    t0 = time.monotonic()
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute(DDL)
        cur.execute("delete from raw.price_paid where source_file = %s", (path.name,))
        removed = cur.rowcount
        # the file has no header: COPY it into a temporary table, then insert with the file name stamped on
        cols = ", ".join(COLUMNS)
        cur.execute(f"create temp table incoming ({', '.join(f'{c} text' for c in COLUMNS)}) on commit drop")
        with cur.copy(f"copy incoming ({cols}) from stdin with (format csv)") as copy:
            with path.open("rb") as f:
                while chunk := f.read(1 << 20):
                    copy.write(chunk)
        cur.execute(f"insert into raw.price_paid ({cols}, source_file) select {cols}, %s from incoming", (path.name,))
        loaded = cur.rowcount
        with path.open("rb") as f:
            lines = sum(1 for _ in f)
        if loaded != lines:  # every line of the file must become exactly one row
            raise SystemExit(f"row count mismatch: file has {lines:,} lines, loaded {loaded:,}; nothing committed")
    print(f"loaded {loaded:,} rows from {path.name} (replaced {removed:,}) in {time.monotonic() - t0:.1f} s")
    return loaded


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "2025"
    name = "pp-monthly-update-new-version.csv" if which == "monthly" else f"pp-{which}.csv"
    load(download(name, Path("data")))
