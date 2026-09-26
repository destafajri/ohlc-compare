# OHLC Compare

Simple Python tool to fetch OHLC candles from the OANDA REST API, synchronize multiple instruments by timestamp, normalize their close prices to a common base, and plot them on one chart.

The default config compares:

- **Target:** `XAU_USD`
- **USD / counter:** `EUR_USD`, `USD_JPY`, `GBP_USD`, `USD_CHF`
- **Rates:** `USB02Y_USD`, `USB10Y_USD`
- **Precious metal:** `XAG_USD`

The default example fetches **500 M5 candles per instrument**.

## What the program does

1. Reads parameters from `config.yaml`.
2. Reads the OANDA API token from `.env`.
3. Downloads candles for every configured instrument.
4. Optionally removes incomplete/current candles.
5. Keeps only timestamps available in **all** instruments (exact intersection).
6. Normalizes each close-price series so its first common candle equals `100`.
7. Displays a comparison chart.
8. Saves aligned closes, normalized data, and the chart to `output/`.

Because OANDA instruments can have different trading/session availability, the number of common candles can be lower than the requested candle count. This is expected.

## Requirements

- Python 3.11+ recommended
- OANDA practice or live account
- OANDA personal access token

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

Create your local secret file:

### macOS / Linux

```bash
cp .env.example .env
```

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

Edit `.env` and replace the placeholder with your actual OANDA token:

```dotenv
OANDA_API_TOKEN=your-real-token-here
```

`.env` is already excluded by `.gitignore` and should never be committed.

## Run

```bash
python ohlc_compare.py
```

Or use another config file:

```bash
python ohlc_compare.py --config config.yaml
```

The program prints the number of common candles, time range, and normalized end change for each instrument.

## Configuration

All non-secret runtime parameters live in `config.yaml`.

### Change timeframe and candle count

```yaml
market:
  granularity: M15
  count: 1000
  price: M
  complete_only: true
```

Common OANDA granularities include `M1`, `M5`, `M15`, `H1`, `H4`, and `D`.

The OANDA candles endpoint supports a maximum of **5000 candles per request**. This program intentionally validates that limit.

### Change instruments

```yaml
instruments:
  - name: XAU_USD
    group: TARGET
  - name: EUR_USD
    group: USD_COUNTER
  - name: USD_JPY
    group: USD_COUNTER
  - name: USB10Y_USD
    group: RATES
  - name: XAG_USD
    group: PRECIOUS_METAL
```

`group` is documentation metadata for humans; the current plot includes every configured instrument.

### Change normalization

```yaml
plot:
  normalize_base: 100
```

Normalization is:

```text
normalized[t] = close[t] / first_common_close * normalize_base
```

This makes instruments with very different nominal prices directly comparable by relative movement. It does **not** mean their volatility or economic exposure is equivalent.

### Practice vs live OANDA

Practice/demo:

```yaml
oanda:
  base_url: https://api-fxpractice.oanda.com
```

Live:

```yaml
oanda:
  base_url: https://api-fxtrade.oanda.com
```

Use a token that belongs to the matching OANDA environment.

## Output

By default the program creates:

```text
output/
├── ohlc_compare_M5_500.png
├── ohlc_compare_M5_500_aligned_close.csv
└── ohlc_compare_M5_500_normalized.csv
```

You can control this in `config.yaml`:

```yaml
output:
  directory: output
  save_csv: true
  save_png: true
```

To run without opening the chart window, useful on a server or scheduler:

```yaml
plot:
  show: false
```

The PNG and CSV files can still be saved.

## Tests

The tests cover the core local transformation logic without calling OANDA:

```bash
python -m unittest discover -s tests -v
```

They verify timestamp intersection, normalization behavior, zero-base protection, and OANDA candle-count validation.

## Notes

- The program uses **close prices** for the comparison chart.
- Default `price: M` uses OANDA midpoint candles.
- With `complete_only: true`, the unfinished current candle is excluded.
- Alignment uses an exact timestamp intersection across all configured instruments to avoid comparing mismatched bars.
- `USB02Y_USD` and `USB10Y_USD` are OANDA rate/bond-price instruments; they should not be interpreted as direct Treasury yields.
- Price-level overlays are useful visually. For quantitative trading research, return correlation, rolling correlation, and lead/lag tests are generally more appropriate than correlation of raw price levels.

## License

No license has been added yet.
