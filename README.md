# OHLC Compare

Simple Python tool to compare multiple OANDA instruments on one normalized chart.

The program does **not** connect to OANDA directly and does **not** need an OANDA token on your local machine. Market data is fetched through:

`https://api-get-ohlc-oanda.vercel.app/ohlc`

The default configuration compares:

- **Target:** `XAU_USD`
- **USD / counter:** `EUR_USD`, `USD_JPY`, `GBP_USD`, `USD_CHF`
- **Rates:** `USB02Y_USD`, `USB10Y_USD`
- **Precious metal:** `XAG_USD`

The default example fetches **500 M5 candles per instrument**.

## How it works

```text
ohlc-compare (local Python)
        |
        | HTTPS GET /ohlc
        v
api-get-ohlc-oanda.vercel.app
        |
        | OANDA credentials stay server-side
        v
      OANDA
```

For each configured instrument the program:

1. Calls the public `/ohlc` API.
2. Optionally removes the incomplete/current candle.
3. Keeps only timestamps present in **every** instrument.
4. Normalizes each close-price series so the first common candle equals `100`.
5. Displays a comparison chart.
6. Saves aligned closes, normalized data, and the PNG chart to `output/`.

Different instruments can have different trading/session availability, so the common aligned candle count can be lower than the requested count. This is expected.

## Requirements

- Python 3.11+ recommended
- Internet access to `api-get-ohlc-oanda.vercel.app`

No local OANDA account ID, API token, `.env`, or other secret is required.

## Local setup

Clone the repository:

```bash
git clone https://github.com/destafajri/ohlc-compare.git
cd ohlc-compare
```

Create and activate a virtual environment.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run

```bash
python ohlc_compare.py
```

Or explicitly choose a config file:

```bash
python ohlc_compare.py --config config.yaml
```

The program prints the number of common candles, aligned time range, and end change from the normalized base for every instrument.

## Configuration

All runtime parameters are in `config.yaml`.

### API endpoint

```yaml
api:
  base_url: https://api-get-ohlc-oanda.vercel.app
  timeout_seconds: 30
```

Normally you do not need to change this. If you deploy your own compatible instance, replace `base_url` with that deployment URL.

### Timeframe and candle count

```yaml
market:
  granularity: M5
  count: 500
  complete_only: true
```

Examples:

```yaml
# 1,000 M15 candles
market:
  granularity: M15
  count: 1000
  complete_only: true
```

```yaml
# 5,000 M5 candles
market:
  granularity: M5
  count: 5000
  complete_only: true
```

The `/ohlc` endpoint accepts a maximum of **5000 candles per request**. The program validates the same limit locally.

Common granularities include `M1`, `M5`, `M15`, `H1`, `H4`, and `D`.

### Instruments

```yaml
instruments:
  - name: XAU_USD
    group: TARGET
  - name: EUR_USD
    group: USD_COUNTER
  - name: USD_JPY
    group: USD_COUNTER
  - name: GBP_USD
    group: USD_COUNTER
  - name: USD_CHF
    group: USD_COUNTER
  - name: USB02Y_USD
    group: RATES
  - name: USB10Y_USD
    group: RATES
  - name: XAG_USD
    group: PRECIOUS_METAL
```

`group` is currently metadata for readability. Every listed instrument is plotted.

### Normalization

```yaml
plot:
  normalize_base: 100
```

The calculation is:

```text
normalized[t] = close[t] / first_common_close * normalize_base
```

This lets instruments with very different nominal prices share one chart. It does not imply equal volatility or equivalent economic exposure.

### Chart display

For desktop use:

```yaml
plot:
  show: true
```

For a server, cron job, or other headless environment:

```yaml
plot:
  show: false
```

PNG/CSV output can still be generated when `show: false`.

## Output

Default output:

```text
output/
├── ohlc_compare_M5_500.png
├── ohlc_compare_M5_500_aligned_close.csv
└── ohlc_compare_M5_500_normalized.csv
```

Configure it with:

```yaml
output:
  directory: output
  save_csv: true
  save_png: true
```

### Aligned close CSV

Contains the original close price for every instrument after exact timestamp intersection.

### Normalized CSV

Contains the same aligned observations normalized to the configured base, default `100`.

## Example API request

The Python program effectively makes requests such as:

```text
https://api-get-ohlc-oanda.vercel.app/ohlc?instrument=XAU_USD&granularity=M5&count=500
```

The comparison program currently uses the `close` field from each returned candle.

## Tests

Run:

```bash
python -m unittest discover -s tests -v
```

Tests cover:

- the HTTP contract used for `/ohlc`
- no OANDA authorization header/token required locally
- incomplete candle filtering
- exact timestamp intersection
- normalization
- zero-base protection
- maximum candle-count validation

## Notes

- The upstream API currently serves OANDA midpoint candles.
- `complete_only: true` is recommended for reproducible analysis.
- `USB02Y_USD` and `USB10Y_USD` are OANDA bond/rate price instruments, not direct Treasury yield series.
- Price-level overlays are useful for visual comparison. For quantitative research, prefer returns, rolling correlation, and lead/lag analysis over correlation of raw price levels.
- Availability of the comparison tool now depends on the configured HTTP API being reachable. If that API is unavailable, the local program cannot fetch fresh candles.

## Related project

OANDA API service:

https://github.com/destafajri/api-get-ohlc-oanda

## License

No license has been added yet.
