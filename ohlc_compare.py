from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import requests
import yaml
from dotenv import load_dotenv


OANDA_MAX_COUNT = 5000


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("Config root must be a mapping/object.")
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    required_sections = ["oanda", "market", "instruments", "plot", "output"]
    missing = [section for section in required_sections if section not in config]
    if missing:
        raise ValueError(f"Missing config section(s): {', '.join(missing)}")

    market = config["market"]
    count = int(market.get("count", 0))
    if not 1 <= count <= OANDA_MAX_COUNT:
        raise ValueError(f"market.count must be between 1 and {OANDA_MAX_COUNT}.")

    instruments = config["instruments"]
    if not isinstance(instruments, list) or not instruments:
        raise ValueError("instruments must be a non-empty list.")

    names = []
    for item in instruments:
        if not isinstance(item, dict) or not item.get("name"):
            raise ValueError("Each instrument must be an object with a non-empty name.")
        names.append(str(item["name"]))
    if len(names) != len(set(names)):
        raise ValueError("Instrument names must be unique.")

    base = float(config["plot"].get("normalize_base", 100.0))
    if base <= 0:
        raise ValueError("plot.normalize_base must be greater than zero.")


def fetch_candles(
    session: requests.Session,
    *,
    base_url: str,
    token: str,
    instrument: str,
    granularity: str,
    count: int,
    price: str,
    complete_only: bool,
    timeout_seconds: float,
) -> pd.DataFrame:
    url = f"{base_url.rstrip('/')}/v3/instruments/{instrument}/candles"
    response = session.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        params={"granularity": granularity, "count": count, "price": price},
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()

    candles = payload.get("candles", [])
    rows: list[dict[str, Any]] = []
    for candle in candles:
        if complete_only and not candle.get("complete", False):
            continue

        price_key = {"M": "mid", "B": "bid", "A": "ask"}.get(price.upper())
        if price_key is None:
            raise ValueError("market.price must be one of M, B, or A.")
        component = candle.get(price_key)
        if not component or "c" not in component:
            continue

        rows.append({"time": candle["time"], "close": float(component["c"])})

    if not rows:
        raise RuntimeError(f"No usable candles returned for {instrument}.")

    frame = pd.DataFrame(rows)
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    frame = frame.drop_duplicates(subset=["time"], keep="last")
    return frame.sort_values("time").reset_index(drop=True)


def align_close_series(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        raise ValueError("No instrument data to align.")

    aligned: pd.DataFrame | None = None
    for instrument, frame in frames.items():
        required = {"time", "close"}
        if not required.issubset(frame.columns):
            raise ValueError(f"{instrument} frame must contain time and close columns.")

        series = (
            frame[["time", "close"]]
            .drop_duplicates(subset=["time"], keep="last")
            .sort_values("time")
            .set_index("time")
            .rename(columns={"close": instrument})
        )
        aligned = series if aligned is None else aligned.join(series, how="inner")

    assert aligned is not None
    aligned = aligned.sort_index()
    if aligned.empty:
        raise RuntimeError("No common timestamps across the configured instruments.")
    return aligned


def normalize_frame(frame: pd.DataFrame, base: float = 100.0) -> pd.DataFrame:
    if frame.empty:
        raise ValueError("Cannot normalize an empty frame.")

    first = frame.iloc[0]
    if (first == 0).any():
        zero_columns = ", ".join(first.index[first == 0])
        raise ValueError(f"Cannot normalize series with zero first value: {zero_columns}")

    return frame.divide(first).multiply(float(base))


def plot_normalized(
    normalized: pd.DataFrame,
    *,
    title: str,
    normalize_base: float,
    figsize: tuple[float, float],
    dpi: int,
    png_path: Path | None,
    show: bool,
) -> None:
    fig, ax = plt.subplots(figsize=figsize)

    for column in normalized.columns:
        ax.plot(normalized.index, normalized[column], label=column, linewidth=1.25)

    ax.axhline(normalize_base, linewidth=0.8, alpha=0.5)
    ax.set_title(title)
    ax.set_xlabel("UTC time")
    ax.set_ylabel(f"Normalized close (first common candle = {normalize_base:g})")
    ax.grid(True, alpha=0.25)
    ax.legend(ncol=4, frameon=False)
    fig.autofmt_xdate()
    fig.tight_layout()

    if png_path is not None:
        png_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(png_path, dpi=dpi, bbox_inches="tight")

    if show:
        plt.show()
    else:
        plt.close(fig)


def run(config_path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    config = load_config(config_path)
    load_dotenv()

    oanda = config["oanda"]
    token_env_var = str(oanda.get("token_env_var", "OANDA_API_TOKEN"))
    token = os.getenv(token_env_var)
    if not token:
        raise RuntimeError(
            f"Missing OANDA API token. Set {token_env_var} in your environment or .env file."
        )

    market = config["market"]
    output = config["output"]
    plot = config["plot"]

    instrument_names = [str(item["name"]) for item in config["instruments"]]
    frames: dict[str, pd.DataFrame] = {}

    with requests.Session() as session:
        for instrument in instrument_names:
            print(f"Fetching {instrument} ...")
            frames[instrument] = fetch_candles(
                session,
                base_url=str(oanda["base_url"]),
                token=token,
                instrument=instrument,
                granularity=str(market["granularity"]),
                count=int(market["count"]),
                price=str(market.get("price", "M")),
                complete_only=bool(market.get("complete_only", True)),
                timeout_seconds=float(oanda.get("timeout_seconds", 30)),
            )
            print(f"  received {len(frames[instrument])} usable candles")

    aligned = align_close_series(frames)
    normalized = normalize_frame(aligned, base=float(plot.get("normalize_base", 100.0)))

    out_dir = Path(output.get("directory", "output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"ohlc_compare_{market['granularity']}_{market['count']}"

    if bool(output.get("save_csv", True)):
        aligned.to_csv(out_dir / f"{stem}_aligned_close.csv", index_label="time")
        normalized.to_csv(out_dir / f"{stem}_normalized.csv", index_label="time")

    png_path = out_dir / f"{stem}.png" if bool(output.get("save_png", True)) else None

    first = aligned.index[0]
    last = aligned.index[-1]
    title = str(
        plot.get(
            "title",
            f"OANDA {market['granularity']} — normalized close comparison",
        )
    )
    title = f"{title}\n{len(aligned)} common candles | {first} – {last}"

    figsize_values = plot.get("figsize", [15, 8])
    plot_normalized(
        normalized,
        title=title,
        normalize_base=float(plot.get("normalize_base", 100.0)),
        figsize=(float(figsize_values[0]), float(figsize_values[1])),
        dpi=int(plot.get("dpi", 180)),
        png_path=png_path,
        show=bool(plot.get("show", True)),
    )

    print(f"Common aligned candles: {len(aligned)}")
    print(f"Period: {first} -> {last}")
    print("\nEnd change from normalized base:")
    print((normalized.iloc[-1] - float(plot.get("normalize_base", 100.0))).round(3).to_string())
    print(f"\nOutput directory: {out_dir.resolve()}")

    return aligned, normalized


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch OANDA candles, align timestamps, normalize prices, and plot cross-market movement."
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to YAML config file (default: config.yaml)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.config)
