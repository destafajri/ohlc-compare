import unittest

import pandas as pd

from ohlc_compare import align_close_series, fetch_candles, normalize_frame, validate_config


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self.payload)


class FetchCandlesTests(unittest.TestCase):
    def test_calls_public_ohlc_api_without_oanda_credentials(self):
        session = FakeSession(
            {
                "candles": [
                    {
                        "time": "2026-09-25T20:50:00Z",
                        "close": "4285.125",
                        "complete": True,
                    }
                ]
            }
        )

        result = fetch_candles(
            session,
            base_url="https://api-get-ohlc-oanda.vercel.app/",
            instrument="XAU_USD",
            granularity="M5",
            count=500,
            complete_only=True,
            timeout_seconds=30,
        )

        self.assertEqual(result["close"].tolist(), [4285.125])
        url, kwargs = session.calls[0]
        self.assertEqual(url, "https://api-get-ohlc-oanda.vercel.app/ohlc")
        self.assertEqual(
            kwargs["params"],
            {"instrument": "XAU_USD", "granularity": "M5", "count": 500},
        )
        self.assertNotIn("headers", kwargs)

    def test_filters_incomplete_api_candles_when_enabled(self):
        session = FakeSession(
            {
                "candles": [
                    {"time": "2026-09-25T20:45:00Z", "close": "10", "complete": True},
                    {"time": "2026-09-25T20:50:00Z", "close": "11", "complete": False},
                ]
            }
        )

        result = fetch_candles(
            session,
            base_url="https://example.test",
            instrument="XAU_USD",
            granularity="M5",
            count=2,
            complete_only=True,
            timeout_seconds=30,
        )

        self.assertEqual(result["close"].tolist(), [10.0])


class AlignCloseSeriesTests(unittest.TestCase):
    def test_keeps_only_common_timestamps_sorted(self):
        a = pd.DataFrame(
            {"time": pd.to_datetime(["2026-01-01T00:05:00Z", "2026-01-01T00:00:00Z"]), "close": [2.0, 1.0]}
        )
        b = pd.DataFrame(
            {"time": pd.to_datetime(["2026-01-01T00:00:00Z", "2026-01-01T00:10:00Z"]), "close": [10.0, 30.0]}
        )

        result = align_close_series({"A": a, "B": b})

        self.assertEqual(list(result.columns), ["A", "B"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result.index[0], pd.Timestamp("2026-01-01T00:00:00Z"))
        self.assertEqual(result.loc[result.index[0], "A"], 1.0)
        self.assertEqual(result.loc[result.index[0], "B"], 10.0)


class NormalizeFrameTests(unittest.TestCase):
    def test_normalizes_each_series_to_requested_base(self):
        frame = pd.DataFrame({"A": [2.0, 3.0], "B": [10.0, 5.0]})

        result = normalize_frame(frame, base=100.0)

        self.assertEqual(result.iloc[0].to_dict(), {"A": 100.0, "B": 100.0})
        self.assertEqual(result.iloc[1].to_dict(), {"A": 150.0, "B": 50.0})

    def test_rejects_zero_first_value(self):
        frame = pd.DataFrame({"A": [0.0, 1.0]})

        with self.assertRaisesRegex(ValueError, "zero"):
            normalize_frame(frame, base=100.0)


class ValidateConfigTests(unittest.TestCase):
    def test_accepts_public_api_config(self):
        config = {
            "api": {"base_url": "https://api-get-ohlc-oanda.vercel.app", "timeout_seconds": 30},
            "market": {"granularity": "M5", "count": 500, "complete_only": True},
            "instruments": [{"name": "XAU_USD", "group": "TARGET"}],
            "plot": {"normalize_base": 100.0, "show": True},
            "output": {"directory": "output", "save_csv": True, "save_png": True},
        }

        validate_config(config)

    def test_rejects_count_above_api_limit(self):
        config = {
            "api": {"base_url": "https://api-get-ohlc-oanda.vercel.app", "timeout_seconds": 30},
            "market": {"granularity": "M5", "count": 5001, "complete_only": True},
            "instruments": [{"name": "XAU_USD", "group": "TARGET"}],
            "plot": {"normalize_base": 100.0, "show": True},
            "output": {"directory": "output", "save_csv": True, "save_png": True},
        }

        with self.assertRaisesRegex(ValueError, "count"):
            validate_config(config)


if __name__ == "__main__":
    unittest.main()
