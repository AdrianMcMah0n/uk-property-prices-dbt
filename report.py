"""Read the dbt marts and write a small Excel report (no addresses, only aggregates).

    python report.py
"""
from pathlib import Path

import pandas as pd
import psycopg
from openpyxl.styles import Font

from load import DSN

QUERIES = {
    "By county": "select * from public_marts.mart_county_prices order by median_price_gbp desc",
    "By month and type": "select * from public_marts.mart_monthly_prices order by sale_month, property_type",
}


def query(conn, sql: str) -> pd.DataFrame:
    cur = conn.execute(sql)
    return pd.DataFrame(cur.fetchall(), columns=[d.name for d in cur.description])


def main() -> None:
    out = Path("output")
    out.mkdir(exist_ok=True)
    with psycopg.connect(DSN) as conn:
        frames = {name: query(conn, sql) for name, sql in QUERIES.items()}
        totals = query(conn, "select count(*) as sales, percentile_cont(0.5) within group (order by price_gbp)::int "
                             "as median_price from public_marts.fct_sales").iloc[0]

    path = out / "uk_property_prices.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as xl:
        for name, df in frames.items():
            df.to_excel(xl, sheet_name=name, index=False)
            ws = xl.sheets[name]
            ws.freeze_panes = "A2"
            for c in ws[1]:
                c.font = Font(bold=True)
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = max(12, len(str(col[0].value)) + 2)

    county = frames["By county"]
    sales, median = int(totals["sales"]), int(totals["median_price"])
    print(f"Standard residential sales: {sales:,}; median price GBP {median:,}")
    print("\nHighest median price (counties with 1,000+ sales):")
    print(county[county.sales >= 1000].head(5)[["county", "sales", "median_price_gbp", "flats_pct"]].to_string(index=False))
    print("\nLowest median price (counties with 1,000+ sales):")
    print(county[county.sales >= 1000].tail(5)[["county", "sales", "median_price_gbp", "flats_pct"]].to_string(index=False))
    print(f"\nSaved {path}")


if __name__ == "__main__":
    main()
