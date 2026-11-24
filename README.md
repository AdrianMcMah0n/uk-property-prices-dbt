# UK property prices: PostgreSQL + dbt pipeline

A small but complete analytics pipeline on open government data: a year of residential property sales in England and Wales is loaded into PostgreSQL (in Docker), cleaned and modelled with dbt, tested, and summarised into an Excel report.

Data: [HM Land Registry Price Paid Data](https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads), full year 2025.

## The problem

Raw public data is rarely ready to use. This file has no header row, codes instead of labels (`D`, `S`, `T`, `F`), dates stored as text, and a mix of ordinary sales with repossessions, buy-to-let and company transfers that distort "typical" prices. Later files can also correct or delete earlier records. Questions like "what does a typical house cost in each county?" need all of that handled first, the same way every time.

## The pipeline

```
gov.uk CSV --load.py--> raw.price_paid --dbt--> staging.stg_price_paid --dbt--> marts.fct_sales
 (172 MB)   (as-is,      (all text)             (typed, decoded,                marts.mart_county_prices
            idempotent)                          latest version)                marts.mart_monthly_prices
                                                                                      |
                                                                          report.py --> Excel
```

| Step | What happens |
|---|---|
| `load.py` | Downloads the file (resumes a broken download), copies it into `raw.price_paid` untouched with PostgreSQL `COPY`. Re-running replaces that file's rows instead of doubling them, and the load is rolled back unless every line of the file became exactly one row. |
| `stg_price_paid` | Types every column, decodes the codes into labels, keeps the latest version of each transaction and drops deleted ones. |
| `fct_sales` | Standard residential sales only (category A). |
| `mart_county_prices` | Per county: sales, median price, share of new builds and flats, first and last sale. |
| `mart_monthly_prices` | Per month and property type: sales, median and mean price. |
| Tests (19) | Unique and not-null keys, allowed values for property type and tenure, no zero or negative prices, no future dates, one row per month and type. |
| `report.py` | Writes the two marts to Excel (aggregates only, no addresses). |

## Result (2025 data)

| | |
|---|---|
| Rows loaded | 992,278 in about 5 seconds |
| Excluded as non-standard sales (category B) | 169,624 |
| Standard residential sales | 822,654 |
| Median price, England and Wales | GBP 299,950 |
| dbt build | 19 of 19 models and tests passed |

Highest and lowest median prices (counties with 1,000+ sales):

| County | Sales | Median price (GBP) | Flats |
|---|---|---|---|
| Windsor And Maidenhead | 2,151 | 546,000 | 26.0% |
| Greater London | 87,088 | 530,000 | 51.9% |
| Surrey | 17,710 | 510,000 | 23.5% |
| ... | | | |
| County Durham | 8,139 | 149,950 | 3.0% |
| City Of Kingston Upon Hull | 3,045 | 144,000 | 5.5% |
| Blackpool | 2,115 | 137,750 | 9.3% |

The full report is in [`sample_output/uk_property_prices.xlsx`](sample_output/uk_property_prices.xlsx).

## Run it

Needs Docker and Python 3.10+.

```bash
docker compose up -d                 # PostgreSQL 16 on localhost:5433
python -m venv .venv
.venv\Scripts\activate               # Windows (macOS / Linux: source .venv/bin/activate)
pip install -r requirements.txt

python load.py 2025                  # or: python load.py monthly  (latest monthly update, 17 MB)
dbt build                            # models + tests (uses ./profiles.yml)
python report.py                     # output/uk_property_prices.xlsx
```

## Design choices

- **Raw stays raw.** The loader does no cleaning, so every transformation is in SQL, version-controlled and tested, and the raw table can always be re-checked against the source file.
- **Idempotent loads.** Each row is stamped with its source file; re-loading a file replaces it in one transaction.
- **Counts are checked, not assumed.** Lines in the file must equal rows loaded, or nothing is committed.
- **Corrections are applied.** Monthly files flag rows as added, changed or deleted; staging keeps only the latest version and removes deletions.
- **Medians, not averages.** A few very expensive sales pull averages up; the median is the typical price.
- **No packages needed.** The one custom test (`unique_combination`) is a short macro in `macros/`.

## Licence and attribution

Code: MIT. Data: Contains HM Land Registry data © Crown copyright and database right 2026. This data is licensed under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). The raw data is not stored in this repository; `load.py` downloads it. The report contains aggregates only, no addresses.
