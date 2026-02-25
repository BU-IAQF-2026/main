from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class TestResult:
    metric: str
    comparison: str
    n_a: int
    n_b: int
    mean_a: float
    mean_b: float
    t_stat: float
    t_pvalue: float
    var_a: float
    var_b: float
    f_stat: float
    f_pvalue: float


def load_binance(path: Path, value_name: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    out = df[["timestamp", "close"]].rename(columns={"close": value_name})
    return out


def load_kraken(path: Path, value_name: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["datetime_utc"], utc=True)
    out = df[["timestamp", "close"]].rename(columns={"close": value_name})
    return out


def f_test_two_sided(x: pd.Series, y: pd.Series) -> tuple[float, float]:
    x = x.dropna()
    y = y.dropna()
    var_x = np.var(x, ddof=1)
    var_y = np.var(y, ddof=1)
    f_stat = var_x / var_y
    df1 = len(x) - 1
    df2 = len(y) - 1
    cdf_val = stats.f.cdf(f_stat, df1, df2)
    p_two_sided = 2 * min(cdf_val, 1 - cdf_val)
    return f_stat, p_two_sided


def pairwise_tests(df: pd.DataFrame, metric: str) -> list[TestResult]:
    pairs = [("pre", "event"), ("event", "post"), ("pre", "post")]
    results: list[TestResult] = []

    for a, b in pairs:
        xa = df.loc[df["period"] == a, metric].dropna()
        xb = df.loc[df["period"] == b, metric].dropna()

        t_stat, t_p = stats.ttest_ind(xa, xb, equal_var=False)
        f_stat, f_p = f_test_two_sided(xa, xb)

        results.append(
            TestResult(
                metric=metric,
                comparison=f"{a} vs {b}",
                n_a=len(xa),
                n_b=len(xb),
                mean_a=xa.mean(),
                mean_b=xb.mean(),
                t_stat=t_stat,
                t_pvalue=t_p,
                var_a=np.var(xa, ddof=1),
                var_b=np.var(xb, ddof=1),
                f_stat=f_stat,
                f_pvalue=f_p,
            )
        )

    return results


def assign_period(ts: pd.Timestamp) -> str | None:
    pre_start = pd.Timestamp("2023-03-01", tz="UTC")
    event_start = pd.Timestamp("2023-03-10", tz="UTC")
    post_start = pd.Timestamp("2023-03-14", tz="UTC")
    end = pd.Timestamp("2023-03-22", tz="UTC")

    if pre_start <= ts < event_start:
        return "pre"
    if event_start <= ts < post_start:
        return "event"
    if post_start <= ts < end:
        return "post"
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Descriptive statistics + t-test + F-test for USDC basis and Binance-Kraken spread"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("IAQF_Parshva/IAQF/data"),
        help="Directory containing binance/kraken CSV files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory where result CSV files are saved",
    )
    args = parser.parse_args()

    data_dir = args.data_dir
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    b_usd = load_binance(data_dir / "binance_btc_usd.csv", "binance_usd_close")
    b_usdc = load_binance(data_dir / "binance_btc_usdc.csv", "binance_usdc_close")
    k_usdc = load_kraken(data_dir / "kraken_btc_usdc.csv", "kraken_usdc_close")

    df = b_usd.merge(b_usdc, on="timestamp", how="inner").merge(k_usdc, on="timestamp", how="inner")

    df["usdc_basis"] = df["binance_usdc_close"] - df["binance_usd_close"]
    df["usdc_basis_pct"] = 100 * df["usdc_basis"] / df["binance_usd_close"]
    df["binance_kraken_spread"] = df["binance_usdc_close"] - df["kraken_usdc_close"]

    df["period"] = df["timestamp"].map(assign_period)
    df = df[df["period"].notna()].copy()

    metrics = ["usdc_basis", "binance_kraken_spread"]

    overall_stats = (
        df[metrics]
        .agg(["count", "mean", "std"]) 
        .T.rename(columns={"count": "n", "mean": "mean", "std": "std_dev"})
        .reset_index()
        .rename(columns={"index": "metric"})
    )

    period_means = (
        df.groupby("period")[metrics]
        .mean()
        .reindex(["pre", "event", "post"])
        .reset_index()
    )

    test_rows: list[TestResult] = []
    for metric in metrics:
        test_rows.extend(pairwise_tests(df, metric))

    tests_df = pd.DataFrame([r.__dict__ for r in test_rows])

    overall_path = output_dir / "descriptive_overall_stats.csv"
    period_path = output_dir / "descriptive_period_means.csv"
    tests_path = output_dir / "descriptive_tests_t_f.csv"

    overall_stats.to_csv(overall_path, index=False)
    period_means.to_csv(period_path, index=False)
    tests_df.to_csv(tests_path, index=False)

    print("=== Overall Descriptive Statistics ===")
    print(overall_stats.to_string(index=False))
    print("\n=== Pre / Event / Post Means ===")
    print(period_means.to_string(index=False))
    print("\n=== Pairwise Welch t-tests + F-tests (variance) ===")
    print(tests_df.to_string(index=False))
    print("\nSaved:")
    print(f"- {overall_path}")
    print(f"- {period_path}")
    print(f"- {tests_path}")


if __name__ == "__main__":
    main()
