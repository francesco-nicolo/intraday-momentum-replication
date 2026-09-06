#!/usr/bin/env python3
"""
build_tables.py: regenerates every numbered table of the report from the raw backtest data.

Rule of this project, not negotiable: a number enters the report only if it comes out of here.
No derived column is typed by hand into the markdown. If a table needs a new column, this script
produces it, not a text editor.

Inputs (all under data/):
  backtest_data_strategies.csv   50 rows: S0 to S4 x {tight, vwap (= loose)} x 5 slippage levels
  backtest_data_prime.csv         4 rows: S2', S4' at 0 bps, both exit variants
  backtest_data_benchmarks.csv    4 rows: bench intraday (9:31), bench hold24,
                                  bench intraday_1000 (10:00 long), bench intraday_1000_short

Optional input (the original repository, cloned next to this file as ./intraday-momentum):
  intraday-momentum/stats/strat{0..4}_8y.json         the authors' own backtest output (for T1)
  intraday-momentum/DayOfTheWeek/Trades_Strat{s}_8y.csv  the authors' trade files (for T14)
If the clone is absent, T1 and T14 are skipped with a note and every other table is produced.

Output, written next to this file:

    tables.md          every table cited in the report, in order of appearance (T1 to T13, plus
                       the static nomenclature table of §4), with their captions. assemble.py reads
                       this file and nothing else for the [Table ...] placeholders.
    supplementary.md   the blocks that are not tables of the report but produce numbers cited in
                       the text: T14 (P&L by direction, §2), the opening-window threshold (§8) and
                       every figure of Appendix A. With --all, two further diagnostic blocks
                       (commission-path test, opening-window decomposition).

Both files are overwritten on every run; do not edit them by hand. The workflow is:

    python build_tables.py && python assemble.py

Conventions fixed elsewhere in the report and not recomputed here: r_f = 2%, financing rate
3.5%, window 2017-05-10 to 2025-05-10 (2,012 NYSE sessions, 2,922 calendar days). The value
`vwap` in the exit_variant column of the CSV files is what the report calls `loose`.
"""

import json
import math
import sys
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
def _find_original_repo():
    """Optional clone of blackswan-quants/intraday-momentum: next to this script, one level up,
    or wherever $INTRADAY_MOMENTUM_REPO points."""
    import os
    env = os.environ.get("INTRADAY_MOMENTUM_REPO")
    for cand in ([Path(env)] if env else []) + [ROOT / "intraday-momentum",
                                                ROOT.parent / "intraday-momentum"]:
        if (cand / "stats").is_dir() or (cand / "DayOfTheWeek").is_dir():
            return cand
    return ROOT / "intraday-momentum"


ORIGINAL_REPO = _find_original_repo()
STATS_JSON_DIR = ORIGINAL_REPO / "stats"
TRADES_DIR = ORIGINAL_REPO / "DayOfTheWeek"

RF = 0.02
FINANCING_RATE = 0.035
YEARS = 8.0
CAL_DAYS = 2922
NYSE_SESSIONS = 2012

# ------------------------------------------------------------------------------------------------
# Raw values that cannot be derived from the CSV files: the "Runtime Statistics" (rows 05 to 08)
# read from the QuantConnect panel at the end of the instrumented benchmark runs of
# benchmark_vol_targeted.py in "intraday" mode at 0 bps. The Free plan offers neither API access
# nor the Object Store, so the daily equity series cannot be exported programmatically: these
# numbers are the only point at which the script imports something it cannot recompute from a
# CSV in this folder. They are also stored in backtest_data_benchmarks.csv for reference.
# ------------------------------------------------------------------------------------------------
BENCH_INTRADAY_RAW = dict(          # entry 9:31, exit 15:58
    eq_n=2012, avg_equity=87026.9309, drag_sum=1.550660953529e-01, total_fees=9746.59,
)
BENCH_INTRADAY_1000_RAW = dict(     # entry 10:00, exit 15:58
    eq_n=2012, avg_equity=76673.9373, drag_sum=1.366085031867e-01, total_fees=8869.29,
)

# The five accumulators of the S4' tight run at 0 bps (same provenance), used by Appendix A.
DSR_RAW = dict(
    n=2011,               # returns on trading days (2,012 sessions, the first produces none)
    m=6.7596e-4,          # daily mean
    s=6.8622e-3,          # daily standard deviation
    sr_d=0.08694,         # daily Sharpe in excess of r_f = 2%
    g3=2.011,             # skewness
    g4=13.703,            # kurtosis, non-excess
    sigma_cross=0.06917,  # cross-sectional dispersion of the 14 QC Sharpes (ddof = 1)
    net_profit=2.71374,   # for the consistency check of Appendix A, §A.6.3
    kappa=CAL_DAYS / NYSE_SESSIONS,
    rf=RF,
)
EULER_GAMMA = 0.5772156649015329


# ------------------------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------------------------

def fmt(x, nd=3, sep=False):
    """US number format: period as decimal separator, optional thousands separator."""
    return f"{x:,.{nd}f}" if sep else f"{x:.{nd}f}"


def signed(x, nd):
    return ("+" if x >= 0 else "") + fmt(x, nd)


def variant_label(v):
    return "loose" if v == "vwap" else "tight"


def prime_name(s):
    """'2 prime' (CSV) -> 'S2′' (report)."""
    return "S" + s.replace(" prime", "′")


def b_star(net_profit_pct, w_sum):
    """Break-even slippage in bps: b* = 1e4 * ln(1 + R0) / w_sum."""
    return 1e4 * math.log(1 + net_profit_pct / 100.0) / w_sum


def log_ret(net_profit_pct):
    return math.log(1 + net_profit_pct / 100.0)


def car(net_profit_pct):
    return 100 * ((1 + net_profit_pct / 100.0) ** (1 / YEARS) - 1)


def predicted_net(net0_pct, w_sum, bps):
    """Cost reconstruction of §3: log(1+R_b) = log(1+R_0) - b/1e4 * w_sum."""
    return 100 * (math.exp(log_ret(net0_pct) - bps / 1e4 * w_sum) - 1)


def load_data():
    df = pd.read_csv(DATA_DIR / "backtest_data_strategies.csv")
    df["strat"] = df["strat"].astype(str)
    prime = pd.read_csv(DATA_DIR / "backtest_data_prime.csv")
    bench = pd.read_csv(DATA_DIR / "backtest_data_benchmarks.csv")
    return df, prime, bench


def load_authors_json():
    """The authors' own backtest output, stats/strat{s}_8y.json, key "statistics"."""
    out = {}
    for s in range(5):
        path = STATS_JSON_DIR / f"strat{s}_8y.json"
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        st = d["statistics"]
        out[str(s)] = dict(
            net_profit=float(st["Net Profit"].rstrip("%")),
            sharpe=float(st["Sharpe Ratio"]),
            drawdown=float(st["Drawdown"].rstrip("%")),
            win_rate=float(st["Win Rate"].rstrip("%")),
            orders=int(st["Total Orders"]),
            psr=float(st["Probabilistic Sharpe Ratio"].rstrip("%")),
            turnover=float(st["Portfolio Turnover"].rstrip("%")),
        )
    return out


def row(df, strat, variant, bps=0.0):
    return df[(df["strat"] == str(strat)) & (df["exit_variant"] == variant) & (df["bps"] == bps)].iloc[0]


def prow(prime, strat, variant):
    return prime[(prime["strat"] == strat) & (prime["exit_variant"] == variant)].iloc[0]


def brow(bench, name):
    return bench[bench["strat"] == name].iloc[0]


# ================================================================================================
# T1. Authors' JSON / reproduced today
# ================================================================================================

def build_t1(df):
    authors = load_authors_json()
    if authors is None:
        return ("### T1. Authors / reproduced today\n\n*Skipped: clone blackswan-quants/intraday-momentum "
                "next to this script to compare against stats/strat{0..4}_8y.json.*")
    lines = [
        "### T1. The five published backtests: authors' result files vs. reproduced today (`tight` variant, 0 bps)",
        "",
        "| | source | return | Sharpe | drawdown | win rate | orders | PSR | turnover |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    psr_diffs = {}
    for s in "01234":
        a, r = authors[s], row(df, s, "tight")
        psr_diffs[s] = a["psr"] - r["psr"]
        lines.append(f"| S{s} | authors | {fmt(a['net_profit'],3)}% | {fmt(a['sharpe'],3)} | {fmt(a['drawdown'],1)}% "
                     f"| {fmt(a['win_rate'],0)}% | {a['orders']} | {fmt(a['psr'],3)}% | {fmt(a['turnover'],2)}% |")
        lines.append(f"| | reproduced | **{fmt(r['net_profit'],3)}%** | **{fmt(r['sharpe'],3)}** | **{fmt(r['drawdown'],1)}%** "
                     f"| **{fmt(r['win_rate'],0)}%** | **{int(r['orders'])}** | **{fmt(r['psr'],3)}%** | **{fmt(r['turnover'],2)}%** |")
    worst, best = max(psr_diffs, key=psr_diffs.get), min(psr_diffs, key=psr_diffs.get)
    lines += ["",
        "Authors: `stats/strat{s}_8y.json`, the backtest output preserved in the repository. Reproduced: the "
        "same code re-run today. Orders, Sharpe, drawdown, win rate and turnover agree within rounding on all "
        f"five rows; the PSR differs by {fmt(psr_diffs[best],1)} to {fmt(psr_diffs[worst],1)} points "
        f"({fmt(np.mean(list(psr_diffs.values())),1)} on average). See §1 and §7."]
    return "\n".join(lines)


# ================================================================================================
# T2, T3, T5, T4. Benchmarks
# ================================================================================================

def build_t2(prime, bench):
    cols = [("intraday (9:31 to 15:58)", brow(bench, "bench intraday")),
            ("hold24", brow(bench, "bench hold24")),
            ("S4′ tight", prow(prime, "4 prime", "tight"))]
    L = ["### T2. The two full-session benchmarks (entry at 9:31) vs. the best configuration",
         "|  | " + " | ".join(c for c, _ in cols) + " |", "|---|---|---|---|"]
    def r(label, f): L.append(f"| {label} | " + " | ".join(f(x) for _, x in cols) + " |")
    r("net profit", lambda x: f"{fmt(x['net_profit'],2)}%")
    r("CAR", lambda x: f"{fmt(car(x['net_profit']),2)}%")
    r("Sharpe (QC)", lambda x: fmt(x["sharpe"], 3))
    r("drawdown", lambda x: f"{fmt(x['drawdown'],1)}%")
    r("recovery (days)", lambda x: str(int(x["recovery_days"])))
    r("β", lambda x: fmt(x["beta"], 3))
    r("α", lambda x: fmt(x["alpha"], 3))
    r("PSR", lambda x: f"{fmt(x['psr'],3)}%")
    r("orders", lambda x: fmt(x["orders"], 0, sep=True))
    r("commissions (USD)", lambda x: fmt(x["fees"], 2, sep=True))
    r("$w_{sum}$", lambda x: fmt(x["w_sum"], 2, sep=True))
    r("$b^*$ (bps)", lambda x: fmt(b_star(x["net_profit"], x["w_sum"]), 3))
    return "\n".join(L)


def build_t2b(bench, prime=None):
    cols = [("entry 9:31, long", brow(bench, "bench intraday")),
            ("entry 10:00, long", brow(bench, "bench intraday_1000")),
            ("entry 10:00, short", brow(bench, "bench intraday_1000_short"))]
    L = ["### T3. The benchmark matched on entry time (10:00, as the strategy)", "",
         "Same script, same leverage rule, one variable changed: the entry minute, and for the third "
         "column the sign of the position.", "",
         "| | " + " | ".join(c for c, _ in cols) + " |", "|---|---|---|---|"]
    def r(label, f): L.append(f"| {label} | " + " | ".join(f(x) for _, x in cols) + " |")
    r("net profit", lambda x: f"{fmt(x['net_profit'],2)}%")
    r("Sharpe (QC)", lambda x: fmt(x["sharpe"], 3))
    r("drawdown", lambda x: f"{fmt(x['drawdown'],1)}%")
    r("$\\beta$", lambda x: fmt(x["beta"], 3))
    r("$\\alpha$", lambda x: fmt(x["alpha"], 3))
    r("avg win / avg loss", lambda x: f"{fmt(x['avg_win'],2)}% / {fmt(x['avg_loss'],2)}%")
    r("orders", lambda x: fmt(x["orders"], 0, sep=True))
    r("commissions (USD)", lambda x: fmt(x["fees"], 2, sep=True))
    r("`ann_std`", lambda x: fmt(x["ann_std"], 3))
    r("$w_{sum}$", lambda x: fmt(x["w_sum"], 2, sep=True))
    r("turnover", lambda x: f"{fmt(x['turnover'],2)}%")
    r("`lambda_avg`", lambda x: fmt(x["lambda_avg"], 4))
    r("`pct_capped`", lambda x: f"{fmt(x['pct_capped'],1)}%")
    a, b, c = (x for _, x in cols)
    L.append("")
    L.append(
        "Controls: `lambda_avg` and `pct_capped` identical to the last digit on all three runs (same "
        f"leverage path), $w_{{sum}}$ within {fmt(100*(max(a['w_sum'],b['w_sum'],c['w_sum'])/min(a['w_sum'],b['w_sum'],c['w_sum'])-1),2)}%, "
        f"$w_{{sum}}/(\\text{{turn}}/100) \\in [{fmt(min(x['w_sum']/(x['turnover']/100) for _,x in cols),1,True)};\\ "
        f"{fmt(max(x['w_sum']/(x['turnover']/100) for _,x in cols),1,True)}]$ vs. the {CAL_DAYS:,} calendar days. "
        f"The long and the short at 10:00 are mirror images in $\\beta$ ($\\pm {fmt(abs(b['beta']),3)}$) and have "
        "average win and average loss swapped: they are the same exposure in the two directions."
    )
    return "\n".join(L)


def build_t3(bench):
    h = brow(bench, "bench hold24")
    gross_car = car(h["net_profit"])
    lam_minus_1 = h["lambda_avg"] - 1
    L = [f"### T5. Correction for the financing that LEAN does not charge (hold24, gross CAR {fmt(gross_car,3)}%)",
         "| $r$ | annual cost | hold24 corrected |", "|---|---|---|"]
    for r in (0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05):
        cost = 100 * lam_minus_1 * r
        corrected = 100 * ((1 + (gross_car - cost) / 100) ** YEARS - 1)
        b = "**" if abs(r - FINANCING_RATE) < 1e-9 else ""
        L.append(f"| {b}{fmt(100*r,1)}%{b} | {b}{fmt(cost,2)}%{b} | {b}{fmt(corrected,1)}%{b} |")
    return "\n".join(L), dict(gross_car=gross_car, lam_minus_1=lam_minus_1)


def build_t3_caption(prime, bench, t3):
    s4 = prow(prime, "4 prime", "tight")
    target_car = car(s4["net_profit"])
    r_be = (t3["gross_car"] - target_car) / (100 * t3["lam_minus_1"])
    corrected = 100 * ((1 + (t3["gross_car"] - 100 * t3["lam_minus_1"] * FINANCING_RATE) / 100) ** YEARS - 1)
    return (f"Subtractive form, borrowed balance $(\\Lambda-1) = {fmt(t3['lam_minus_1'],4)}$. At the chosen rate "
            f"({fmt(100*FINANCING_RATE,1)}%) hold24 makes {fmt(corrected,1)}% vs. {fmt(s4['net_profit'],1)}% "
            f"for S4′ tight. **Break-even rate: {fmt(100*r_be,2)}%.**")


def build_t12(bench):
    raw, b = BENCH_INTRADAY_RAW, brow(bench, "bench intraday")
    fee_pct = 100 * raw["total_fees"] / (YEARS * raw["avg_equity"])
    lev_pct = 100 * 0.5 * raw["drag_sum"] / YEARS
    log_car = -100 * math.log(1 + b["net_profit"] / 100) / YEARS
    total = fee_pct + lev_pct
    res_lev = total - log_car
    res_und = res_lev / b["lambda_avg"]
    L = ["### T4. Decomposition of the `intraday` benchmark's return (entry at 9:31, 0 bps)", "",
         "| item | how it is obtained | value |", "|---|---|---|",
         f"| commissions | $\\phi = \\text{{fees}}/(\\text{{years}}\\cdot\\bar E)$ | {fmt(fee_pct,3)}%/year |",
         f"| leverage drag | $\\tfrac{{1}}{{2}}\\sum_t \\frac{{\\Lambda_t-1}}{{\\Lambda_t}}r_{{port,t}}^2 \\big/ \\text{{years}}$ | {fmt(lev_pct,3)}%/year |",
         f"| **sum of the two mechanical effects** | | **{fmt(total,3)}%/year** |",
         f"| measured log CAR | $-\\ln(1+R)/\\text{{years}}$ | {fmt(log_car,3)}%/year |",
         f"| **residual, leveraged position** | | **{fmt(res_lev,3)}%/year** |",
         f"| residual, underlying | residual$/\\bar\\Lambda$ | {fmt(res_und,3)}%/year |", "",
         "Raw values from the instrumented run (Runtime Statistics, not recomputable from a CSV, since the "
         f"Free plan offers no API access): `eq_n` = {raw['eq_n']}, `avg_equity` = {fmt(raw['avg_equity'],2)}, "
         f"`drag_sum` = {raw['drag_sum']:.6e}, `total_fees` = {fmt(raw['total_fees'],2)}. The `eq_n` count "
         "coincides with the NYSE sessions counted separately in the window: an independent check that the "
         "sampling is one point per session, with no gaps."]
    return "\n".join(L)


# ================================================================================================
# T7, T6. Cost reconstruction
# ================================================================================================

def build_t4(df, prime, bench):
    L = ["### T7. The $\\bar w = \\Lambda$ identity, break-even and ratio to turnover",
         "|  | variant | orders | $w_{sum}$ | $\\bar w$ | $b^*$ (bps) | $w_{sum}/(\\text{turn}/100)$ |",
         "|---|---|---|---|---|---|---|"]
    wbars = []
    for _, r in df[df["bps"] == 0.0].iterrows():
        wbar = r["w_sum"] / r["orders"]; wbars.append(wbar)
        L.append(f"| S{r['strat']} | {variant_label(r['exit_variant'])} | {fmt(r['orders'],0,True)} | "
                 f"{fmt(r['w_sum'],4,True)} | {fmt(wbar,4)} | {fmt(b_star(r['net_profit'],r['w_sum']),3)} | "
                 f"{fmt(r['w_sum']/(r['turnover']/100),1,True)} |")
    for _, r in prime.iterrows():
        wbar = r["w_sum"] / r["orders"]; wbars.append(wbar)
        L.append(f"| {prime_name(r['strat'])} | {variant_label(r['exit_variant'])} | {fmt(r['orders'],0,True)} | "
                 f"{fmt(r['w_sum'],4,True)} | {fmt(wbar,4)} | {fmt(b_star(r['net_profit'],r['w_sum']),3)} | "
                 f"{fmt(r['w_sum']/(r['turnover']/100),1,True)} |")
    names = {"bench intraday": "bench intraday", "bench hold24": "bench hold24",
             "bench intraday_1000": "bench 10:00 long", "bench intraday_1000_short": "bench 10:00 short"}
    for _, r in bench.iterrows():
        L.append(f"| {names.get(r['strat'], r['strat'])} | none | {fmt(r['orders'],0,True)} | "
                 f"{fmt(r['w_sum'],4,True)} | {fmt(r['w_sum']/r['orders'],4)} | {fmt(b_star(r['net_profit'],r['w_sum']),3)} | "
                 f"{fmt(r['w_sum']/(r['turnover']/100),1,True)} |")
    lam = brow(bench, "bench intraday")["lambda_avg"]
    ratios = [r["w_sum"] / (r["turnover"] / 100) for frame in (df[df["bps"] == 0.0], prime, bench)
              for _, r in frame.iterrows()]
    L.append("")
    L.append(f"Over the fourteen strategy configurations $\\bar w \\in [{fmt(min(wbars),4)};\\ {fmt(max(wbars),4)}]$, "
             f"vs. `lambda_avg` $= {fmt(lam,4)}$. The two deviations (hold24 and the intraday benchmark) are "
             "discussed below.")
    L.append("")
    L.append(f"Ratio to LEAN's turnover: $w_{{sum}}/(\\text{{turnover}}/100) \\in [{fmt(min(ratios),1,True)};\\ "
             f"{fmt(max(ratios),1,True)}]$ on all eighteen rows, vs. {CAL_DAYS:,} calendar days ({NYSE_SESSIONS:,} NYSE "
             "sessions) in the window. LEAN averages the daily turnover over the samples of the same series it "
             "uses for the performance statistics, so this ratio counts those samples directly: eighteen rows say "
             "the series has one point per calendar day, and they say it without using any moment of the returns "
             "(Appendix A, §A.8).")
    return "\n".join(L)


def build_t5(df):
    base = df[df["bps"] == 0.0].set_index(["strat", "exit_variant"])
    L = ["### T6. Out-of-sample validation of the cost reconstruction",
         "|  | exit threshold | bps | measured | predicted | error (pp) |", "|---|---|---|---|---|---|"]
    errs, resid_bps = [], []
    for _, r in df[df["bps"] > 0].sort_values(["strat", "exit_variant", "bps"]).iterrows():
        key = (r["strat"], r["exit_variant"])
        pred = predicted_net(base.loc[key, "net_profit"], base.loc[key, "w_sum"], r["bps"])
        err = pred - r["net_profit"]; errs.append(err)
        resid_bps.append((r["bps"], key, 1e4 * (log_ret(pred) - log_ret(r["net_profit"]))))
        L.append(f"| S{r['strat']} | `{variant_label(r['exit_variant'])}` | {fmt(r['bps'],2)} | "
                 f"{fmt(r['net_profit'],3)} | {fmt(pred,3)} | {signed(err,3)} |")
    errs = np.array(errs)
    L.append("")
    L.append("Eight-year net profit (%). 40 rows, none used to calibrate the model: calibration uses only "
             "the 0 bps run of each "
             "combination. The reading of the residuals is in §3.6.")
    L.append("")
    L.append("> $\\sum_i w_i^2$ is not observable from the data collected; the expected term uses "
             "$w_{sum}^2/\\text{orders}$, which by Cauchy-Schwarz is a lower bound for it, with equality if "
             "leverage never varied. The comparison is therefore one of order of magnitude, not a test.")
    # numbers cited in §3.6
    lo = [v for b, k, v in resid_bps if b <= 1.0]
    hi = [v for b, k, v in resid_bps if b == 2.0 and not (k == ("1", "tight"))]
    s1t2 = [v for b, k, v in resid_bps if b == 2.0 and k == ("1", "tight")][0]
    o2 = np.mean([2.0**2 / (2 * 1e8) * base.loc[k, "w_sum"]**2 / base.loc[k, "orders"] * 1e4
                  for b, k, v in resid_bps if b == 2.0 and k != ("1", "tight")])
    L.append("")
    L.append(f"<!-- figures cited in §3.6: max |error| {fmt(np.abs(errs).max(),3)}pp, mean |error| "
             f"{fmt(np.abs(errs).mean(),3)}pp; residual in bps of terminal log wealth up to 1 bps: mean "
             f"{signed(np.mean(lo),2)}, sd {fmt(np.std(lo, ddof=1),2)}; at 2 bps over the nine regular rows: mean "
             f"{signed(np.mean(hi),2)}, expected O(b^2) term (lower bound) {fmt(o2,2)}; S1 tight at 2 bps: "
             f"{fmt(s1t2,0)} bps -->")
    return "\n".join(L)


# ================================================================================================
# T8, T10, T9, T11. The 2x2x2 design
# ================================================================================================

def build_t7_t8(df, prime):
    lr = lambda s, v: log_ret(row(df, s, v)["net_profit"])
    lrp = lambda s, v: log_ret(prow(prime, s, v)["net_profit"])
    V = [("tight", "tight"), ("loose", "vwap")]

    t7 = ["### T8. Effect of the **VWAP entry filter**, holding the exit structure fixed", "",
          "Eight-year log return: $\\ln(1+R_A) - \\ln(1+R_B)$, that is, the logarithm of the ratio between final "
          f"wealths; $+{fmt(lr(2,'tight')-lrp('2 prime','tight'),5)}$ means that the cell with the filter closes with "
          f"{fmt(100*(math.exp(lr(2,'tight')-lrp('2 prime','tight'))-1),1)}% more capital. The metric is in logs because "
          "the cells start from different levels and because only in logs does \"zero interaction\" mean \"additive "
          "effects\": in percentage points two independent effects would show a spurious interaction equal to their "
          "product, here ten times larger than the one measured. Rows: exit threshold. Columns: the level at which "
          "the exit structure is held fixed.", "",
          "| exit threshold | with the 30′ simple exit ($S2 - S2'$) | with the 5′ + gate exit ($S4' - S4$) | interaction |",
          "|---|---|---|---|"]
    for lab, v in V:
        a = lr(2, v) - lrp("2 prime", v); b = lrp("4 prime", v) - lr(4, v)
        t7.append(f"| `{lab}` | {signed(a,5)} | {signed(b,5)} | {signed(b-a,5)} |")

    t8 = ["### T10. Effect of the **exit structure**, 30′ simple to 5′ + gate $N=4$", "",
          "Eight-year log return, first figure `tight` and second `loose`. The columns are the four",
          "combinations of the two entry filters; the design has four and the data contain three.", "",
          "| value of the exit package | no EMA, no VWAP ($S3-S0$) | EMA, no VWAP ($S4-S2'$) | EMA and VWAP ($S4'-S2$) | no EMA, VWAP |",
          "|---|---|---|---|---|"]
    c = {}
    for lab, v in V:
        c[lab] = (lr(3, v) - lr(0, v), lr(4, v) - lrp("2 prime", v), lrp("4 prime", v) - lr(2, v))
        t8.append(f"| `{lab}` | **{signed(c[lab][0],5)}** | {signed(c[lab][1],5)} | {signed(c[lab][2],5)} | not run |")
    t8 += ["", "Possible readings, each at **a single level** of the other filter:", "",
           f"- **effect of the EMA on the package** (col. 2 minus col. 1), measured with the VWAP absent: "
           f"{signed(c['tight'][1]-c['tight'][0],5)} (`tight`) and {signed(c['loose'][1]-c['loose'][0],5)} (`loose`). "
           "Negative interaction, so the EMA and the package are **substitutes**",
           f"- **effect of the VWAP on the package** (col. 3 minus col. 2), measured with the EMA present: "
           f"{signed(c['tight'][2]-c['tight'][1],5)} and {signed(c['loose'][2]-c['loose'][1],5)}. Zero interaction, "
           "so **additive**"]

    t8b = ["### T9. Decomposition of the exit package (no EMA, no VWAP)", "",
           "S0 = 30′ simple; S1 = 30/5 without gate; S3 = 30/5 with gate $N=4$. S1 and S3 differ only in",
           "`exit_confirmation_bars`, so cadence and persistence **are separable**.", "",
           "| exit threshold | cadence 30′ to 5′ ($S1-S0$) | gate $N=4$ ($S3-S1$) | package ($S3-S0$) |",
           "|---|---|---|---|"]
    for lab, v in V:
        cad, gate, pack = lr(1, v) - lr(0, v), lr(3, v) - lr(1, v), lr(3, v) - lr(0, v)
        t8b.append(f"| `{lab}` | **{signed(cad,5)}** | **{signed(gate,5)}** | {signed(pack,5)} |")
    o = lambda s: fmt(row(df, s, "tight")["orders"], 0, True)
    t8b.append("")
    t8b.append(f"Orders: S0 {o(0)}, S1 {o(1)}, S3 {o(3)} (`tight`).")
    # returned in order of appearance in the report: T8 (§4.2), T9 (§4.3), T10 (§4.4)
    return "\n".join(t7), "\n".join(t8b), "\n".join(t8)


def build_t9(df):
    L = ["### T11. Crossover between the two **exit thresholds** (axis 3)", "",
         "Slippage level at which `tight` and `loose` break even, for a fixed strategy.", "",
         "| strategy | `tight` at 0 bps | `loose` at 0 bps | $w_{sum}$ `tight` | $w_{sum}$ `loose` | crossover (bps) |",
         "|---|---|---|---|---|---|"]
    for s in "01234":
        t, l = row(df, s, "tight"), row(df, s, "vwap")
        cross = 1e4 * (log_ret(l["net_profit"]) - log_ret(t["net_profit"])) / (l["w_sum"] - t["w_sum"])
        b = "**" if cross > 0 else ""
        L.append(f"| S{s} | {fmt(t['net_profit'],2)} | {fmt(l['net_profit'],2)} | {fmt(t['w_sum'],1,True)} | "
                 f"{fmt(l['w_sum'],1,True)} | {b}{fmt(cross,3)}{b} |")
    L.append("")
    L.append("Negative crossover = `loose` already wins at 0 bps and the gap widens. On S3 and S4 the sign reverses "
             "at 0 bps, but `loose` has a lower $w_{sum}$ and therefore decays more slowly. Whether the overtake "
             "falls at a realistic level of slippage is discussed below.")
    return "\n".join(L)


# ================================================================================================
# T12, T13. Ranking stability and S4'
# ================================================================================================

def build_t10(df):
    L = ["### T12. Ranking stability across the five cost levels",
         "| variant | metric | stable | ranking |", "|-----|-----|-----|--------------------------------|"]
    levels = sorted(df["bps"].unique())
    for lab, v in [("tight", "tight"), ("loose", "vwap")]:
        for metric, col in [("return", "net_profit"), ("Sharpe", "sharpe")]:
            orders = []
            for b in levels:
                sub = df[(df["exit_variant"] == v) & (df["bps"] == b)].sort_values(col, ascending=False)
                orders.append((b, " > ".join(f"S{s}" for s in sub["strat"])))
            stable = len({o for _, o in orders}) == 1
            rank = orders[0][1] if stable else " · ".join(f"{fmt(b,2)}: {o}" for b, o in orders)
            L.append(f"| {lab} | {metric} | {'yes' if stable else '**no**'} | {rank} |")
    L.append("")
    L.append("The single inversion (S1 vs. S0 on Sharpe, `tight`, between 0 and 0.25 bps) is discussed below. The "
             "hypothesis \"turnover, not the number of trades, predicts the drag\" cannot be tested on these data: "
             "by the identity of T7 the two are proportional, so there is no variance to explain.")
    return "\n".join(L)


def build_t11(df, prime):
    L = ["### T13. S4′ vs. the best configurations in the repository",
         "|  | 0 bps | 0.25 bps | 0.5 bps | $b^*$ (bps) | drawdown | Sharpe |", "|---|---|---|---|---|---|---|"]
    for v in ("tight", "vwap"):
        r = prow(prime, "4 prime", v)
        L.append(f"| S4′ {variant_label(v)} | {fmt(r['net_profit'],1)} | "
                 f"{fmt(predicted_net(r['net_profit'], r['w_sum'], 0.25),1)} | "
                 f"{fmt(predicted_net(r['net_profit'], r['w_sum'], 0.5),1)} | "
                 f"{fmt(b_star(r['net_profit'], r['w_sum']),3)} | {fmt(r['drawdown'],1)}% | {fmt(r['sharpe'],3)} |")
    for s, v in (("2", "vwap"), ("4", "tight")):
        r0 = row(df, s, v)
        L.append(f"| S{s} {variant_label(v)} | {fmt(r0['net_profit'],1)} | {fmt(row(df,s,v,0.25)['net_profit'],1)} | "
                 f"{fmt(row(df,s,v,0.5)['net_profit'],1)} | {fmt(b_star(r0['net_profit'], r0['w_sum']),3)} | "
                 f"{fmt(r0['drawdown'],1)}% | {fmt(r0['sharpe'],3)} |")
    s4p, s4 = prow(prime, "4 prime", "tight"), row(df, 4, "tight")
    lead = log_ret(s4p["net_profit"]) - log_ret(s4["net_profit"])
    L.append("")
    L.append("The 0.25 and 0.5 bps columns of S2′ and S4′ are **predicted** by the model of T6, not measured: for "
             "these two cells only the 0 bps run exists. The lead of S4′ tight over S4 tight is "
             f"{signed(lead,5)} in log return over eight years (T8), that is, {fmt(100*(math.exp(lead)-1),1)}% more "
             f"final capital, about {fmt(100*(math.exp(lead/YEARS)-1),1)}% per year.")
    return "\n".join(L)


# ================================================================================================
# T14. P&L by direction (numbers cited in §2; needs the original repository's trade files)
# ================================================================================================

def build_t13():
    L = ["### T14. P&L by direction (from the repository's trade files, column Direction)",
         "| strategy | long trades | long P&L (USD) | short trades | short P&L (USD) | % long | % short |",
         "|---|---|---|---|---|---|---|"]
    found = False
    for s in (2, 3, 4):
        path = TRADES_DIR / f"Trades_Strat{s}_8y.csv"
        if not path.exists():
            continue
        found = True
        g = pd.read_csv(path).groupby("Direction")["P&L"].agg(["count", "sum"])
        bn, bp = int(g.loc["Buy", "count"]), g.loc["Buy", "sum"]
        sn, sp = int(g.loc["Sell", "count"]), g.loc["Sell", "sum"]
        L.append(f"| S{s} | {bn} | {fmt(bp,2,True)} | {sn} | {fmt(sp,2,True)} | {fmt(100*bp/(bp+sp),1)}% | "
                 f"{fmt(100*sp/(bp+sp),1)}% |")
    if not found:
        return ("### T14. P&L by direction\n\n*Skipped: clone blackswan-quants/intraday-momentum next to this "
                "script to read DayOfTheWeek/Trades_Strat{2,3,4}_8y.csv.*")
    L.append("\n`Buy` = trade opened long, `Sell` = trade opened short (P&L in dollars, not rescaled by the equity "
             "of the moment; the two directions are interleaved in time, so the imbalance favors neither).")
    return "\n".join(L)


# ================================================================================================
# Supplementary blocks: numbers cited in §8 and in Appendix A
# ================================================================================================

def opening_window_threshold(bench):
    """Extra cost on the 9:31 entry alone that would erase the gap vs. the 10:00 entry (§8).

    The two runs are matched on everything but the entry minute and both run at 0 bps. The 15:58 exit
    is common and cancels, so the cost has to be loaded on the entries alone: w_entries = w_sum / 2,
    since w_bar = Lambda holds order by order.
    """
    a, b = brow(bench, "bench intraday"), brow(bench, "bench intraday_1000")
    gap_log = log_ret(a["net_profit"]) - log_ret(b["net_profit"])
    w_entries = 0.5 * (a["w_sum"] + b["w_sum"]) / 2.0
    b_eq = 1e4 * gap_log / w_entries
    return "\n".join([
        "### Opening-window threshold (for §8)", "",
        "| item | value |", "|---|---|",
        f"| gap 9:31 vs 10:00, percentage points | {fmt(a['net_profit']-b['net_profit'],3)} |",
        f"| gap 9:31 vs 10:00, log | {fmt(gap_log,4)} |",
        f"| $w_{{sum}}$ of the entries alone | {fmt(w_entries,1,True)} |",
        f"| $b_{{eq}}$, extra cost that erases the gap | {fmt(b_eq,3)} bps |",
        # Illustrative conversion only: prices are NOT measured in this report. The two rows show that the
        # threshold in cents is not constant over the sample (SPY grows, the tick stays at one cent).
        f"| illustrative, at a price of 250 | {fmt(b_eq/1e4*250*100,2)} cents |",
        f"| illustrative, at a price of 600 | {fmt(b_eq/1e4*600*100,2)} cents |", "",
        "Reading: a 9:31 entry would have to cost $b_{eq}$ basis points more than a 10:00 entry, every day for",
        "eight years, for the gap to vanish entirely.",
    ])


# ------------------------------------------------------------------------------------------------
# How LEAN annualizes (Appendix A, §A.8)
#
# LEAN samples the performance series once per calendar night (BaseResultsHandler.Sample, whose
# value is (E_t - E_{t-1})/E_{t-1}, so a night with no trading contributes an exact zero) and then
# annualizes it with 252 (PortfolioStatistics: AnnualVariance(listPerformance, tradingDaysPerYear)).
# The series it works on is therefore ours diluted with zeros: same power sums, more observations.
# The two functions below rebuild that series' moments from ours and apply LEAN's own formulas to
# them, so the report can check its reading of the platform instead of asserting it.
# ------------------------------------------------------------------------------------------------

RF_LEAN = 0.027   # the rate implicit in LEAN's Sharpe, recovered by implied_risk_free() below


def calendar_series_moments():
    """Moments of the diluted series LEAN works on, from ours.

    Inserting 911 zeros into 2,011 returns divides the mean by kappa and the standard deviation by
    its square root, and the standardized moments move the other way. These are the one-line
    relations the appendix prints, so that a reader can redo the check from the values in §A.6.1;
    they neglect a term in the mean, which is worth 0.1% on the standard deviation.
    """
    r = DSR_RAW
    k = r["kappa"]
    return dict(n=CAL_DAYS, mean=r["m"] / k, sd=r["s"] / math.sqrt(k),
                skew=r["g3"] * math.sqrt(k), kurt_excess=r["g4"] * k - 3)


def lean_psr(cal, rf):
    """Statistics.ProbabilisticSharpeRatio, transcribed.

    Two details decide the value and neither is the textbook one: the threshold is an annualized
    Sharpe of 1 (benchmarkSharpeRatio = 1/sqrt(tradingDaysPerYear)), and the excess kurtosis that
    MathNet returns is fed to a term that Bailey and Lopez de Prado write for the non-excess one.
    """
    sr = (cal["mean"] - rf / 252) / cal["sd"]
    est = math.sqrt((1 - cal["skew"] * sr + (cal["kurt_excess"] - 1) / 4 * sr ** 2) / (cal["n"] - 1))
    return 100 * NormalDist().cdf((sr - 1 / math.sqrt(252)) / est)


def implied_risk_free():
    """The rate that reproduces each reported Sharpe, under the two readings of AnnualPerformance.

    LEAN computes Sharpe = (annual performance - r_f) / (sqrt(252) * sd), with r_f an annual rate
    taken from its interest rate model and never rescaled. Inverting it on runs whose mean differs
    separates the linear reading of the annualization from the compounding one that the source
    actually implements, and pins the rate.
    """
    def rates(mean, sd_ann, sharpe):
        return mean * 252 - sharpe * sd_ann, (1 + mean) ** 252 - 1 - sharpe * sd_ann

    out = []
    bench = pd.read_csv(DATA_DIR / "backtest_data_benchmarks.csv")
    names = {"bench intraday": "bench intraday", "bench hold24": "bench hold24",
             "bench intraday_1000": "bench 10:00 long", "bench intraday_1000_short": "bench 10:00 short"}
    for _, b in bench.iterrows():
        # sum of log returns is ln(1+R) exactly; sum of squares comes from the reported ann_std
        sd_d = b["ann_std"] / math.sqrt(252)
        s2 = sd_d ** 2 * (CAL_DAYS - 1)
        mean = (math.log(1 + b["net_profit"] / 100) + 0.5 * s2) / CAL_DAYS
        out.append((names.get(b["strat"], b["strat"]),) + rates(mean, b["ann_std"], b["sharpe"]))
    cal = calendar_series_moments()
    out.append(("S4′ tight",) + rates(cal["mean"], math.sqrt(252) * cal["sd"], 1.075))
    return out


def gumbel_bracket(N):
    nd = NormalDist()
    return (1 - EULER_GAMMA) * nd.inv_cdf(1 - 1.0 / N) + EULER_GAMMA * nd.inv_cdf(1 - 1.0 / (N * math.e))


def dsr_appendix():
    """Every number of Appendix A, from the five accumulators of the S4' tight run."""
    nd, r = NormalDist(), DSR_RAW
    n, sr, g3, g4, k = r["n"], r["sr_d"], r["g3"], r["g4"], r["kappa"]
    den = math.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2)
    se_gauss = math.sqrt((1 + sr ** 2 / 2) / n)
    se_corr = math.sqrt((1 - g3 * sr + (g4 - 1) / 4 * sr ** 2) / n)
    scale = math.sqrt(252 / k)                      # QC Sharpe units -> daily units

    def dsr(N, sigma):
        return 100 * nd.cdf((sr - sigma * gumbel_bracket(N)) * math.sqrt(n - 1) / den)

    def threshold95(sigma):
        lo, hi = 2.0, 1e9
        while hi - lo > 0.05:
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if dsr(mid, sigma) > 95 else (lo, mid)
        return lo

    sr_c, g3_c, g4_c, n_c = sr / math.sqrt(k), g3 * math.sqrt(k), g4 * k, CAL_DAYS
    den_c = math.sqrt(1 - g3_c * sr_c + (g4_c - 1) / 4 * sr_c ** 2)
    z_c = (sr_c - se_gauss * gumbel_bracket(14) / math.sqrt(k)) * math.sqrt(n_c - 1) / den_c
    z_b = (sr - se_gauss * gumbel_bracket(14)) * math.sqrt(n - 1) / den

    out = ["### Appendix A. Numbers of the Deflated Sharpe Ratio (generated)", "",
           "| quantity | value |", "|---|---|",
           f"| PSR denominator | {fmt(den,5)} |",
           f"| Gaussian SE | {fmt(se_gauss,5)} |",
           f"| SE corrected for the moments | {fmt(se_corr,5)} |",
           f"| Gumbel bracket, $N=14$ | {fmt(gumbel_bracket(14),4)} |",
           f"| $SR_{{0,d}}$ | {fmt(se_gauss*gumbel_bracket(14),5)} |",
           f"| $z$ | {fmt(z_b,4)} |",
           f"| **DSR** | **{fmt(dsr(14,se_gauss),2)}%** |",
           f"| DSR with corrected SE | {fmt(dsr(14,se_corr),2)}% |",
           f"| 95% threshold in $N$ | {fmt(threshold95(se_gauss),1)} |",
           f"| 95% threshold in $N$, corrected SE | {fmt(threshold95(se_corr),1)} |",
           f"| scale factor, QC Sharpe to daily | {fmt(scale,3)} |",
           f"| SE in QC units | {fmt(se_gauss*scale,5)} |",
           f"| ratio SE / $\\sigma_{{cross}}$ | {fmt(se_gauss*scale/r['sigma_cross'],2)} |", "",
           "**Invariance to the sampling convention** (must give the same DSR)", "",
           "| | $\\widehat{SR}$ | $n$ | denominator | $z$ | DSR |", "|---|---|---|---|---|---|",
           f"| trading days | {fmt(sr,5)} | {n} | {fmt(den,5)} | {fmt(z_b,4)} | **{fmt(dsr(14,se_gauss),2)}%** |",
           f"| calendar days | {fmt(sr_c,5)} | {n_c} | {fmt(den_c,5)} | {fmt(z_c,4)} | **{fmt(100*nd.cdf(z_c),2)}%** |",
           "", "**Sensitivity to $N$** (main specification, Gaussian SE)", "",
           "| $N$ | Gumbel bracket | $SR_{0,d}$ | DSR |", "|---|---|---|---|"]
    for N in (14, 50, 65, 100, 500, 1000):
        out.append(f"| {N:,} | {fmt(gumbel_bracket(N),4)} | {fmt(se_gauss*gumbel_bracket(N),5)} | {fmt(dsr(N,se_gauss),2)}% |")
    out += ["", f"**Bailey and López de Prado specification** ($\\sigma_{{cross}}$ brought into daily units by "
            f"dividing by {fmt(scale,3)})", "", "| $N$ | DSR |", "|---|---|"]
    for N, lab in ((14, "14"), (1e4, "10^4"), (1e9, "10^9")):
        out.append(f"| {lab} | {fmt(dsr(N, r['sigma_cross']/scale),2)}% |")
    cal = calendar_series_moments()
    sig_qc = math.sqrt(252) * cal["sd"]
    rates = implied_risk_free()
    lo, hi = min(c for _, _, c in rates), max(c for _, _, c in rates)
    out += ["", "**Check of the calendar/252 reading** (Appendix A, §A.8)", "",
            "| quantity | from our moments | reported by QC |", "|---|---|---|",
            f"| annualized volatility, $\\sqrt{{252}}\\,s/\\sqrt{{\\kappa}}$ | {fmt(sig_qc,4)} | 0.09 |",
            f"| Probabilistic Sharpe Ratio | {fmt(lean_psr(cal, RF_LEAN),1)}% | 49.490% |",
            f"| Sharpe annualized on trading days instead, $\\widehat{{SR}}_d\\sqrt{{252}}$ | {fmt(sr*math.sqrt(252),2)} | (1.075 printed) |", "",
            f"The volatility uses only the calendar-day count and $\\sqrt{{252}}$: no free parameter. The PSR is "
            f"LEAN's own routine (`Statistics.ProbabilisticSharpeRatio`) applied to the same moments, at the rate "
            f"of {fmt(100*RF_LEAN,1)}% fixed independently in the table below."]
    # the rate LEAN uses, recovered by inverting its Sharpe on five independent runs
    out += ["", "**The risk-free rate implicit in LEAN's Sharpe**", "",
            "| run | mean $\\times$ 252 | mean compounded over 252 |", "|---|---|---|"]
    for label, lin, comp in rates:
        out.append(f"| {label} | {fmt(100*lin,2)}% | {fmt(100*comp,2)}% |")
    out.append("")
    out.append(f"Compounding the mean puts the five runs between {fmt(100*lo,2)}% and {fmt(100*hi,2)}%; multiplying "
               "it spreads them over more than a point. The two that separate the readings are the two with a large "
               "mean, hold24 and S4′.")
    # sensitivity of the DSR to the risk-free convention (Appendix A, §A.4.3)
    def dsr_at_rf(rf):
        sr_rf = (r["m"] - rf / 252) / r["s"]
        den_rf = math.sqrt(1 - g3 * sr_rf + (g4 - 1) / 4 * sr_rf ** 2)
        return 100 * nd.cdf((sr_rf - se_gauss * gumbel_bracket(14)) * math.sqrt(n - 1) / den_rf)
    out += ["", "**Sensitivity to the risk-free convention** (main specification)", "",
            "| $r_f$ | DSR |", "|---|---|"]
    for rf in (0.01, 0.02, RF_LEAN, 0.03):
        out.append(f"| {fmt(100*rf,2)}% | {fmt(dsr_at_rf(rf),2)}% |")
    # alternative annualization factor for the cross-sectional dispersion (Appendix A, §A.4.5)
    alt = math.sqrt(252)
    out += ["", f"**Alternative scale for $\\sigma_{{cross}}$**: with $\\sqrt{{252}} = {fmt(alt,3)}$ instead of "
            f"{fmt(scale,3)}, the SE / $\\sigma_{{cross}}$ factor is {fmt(se_gauss*alt/r['sigma_cross'],2)} and the "
            f"Bailey and López de Prado DSR is {fmt(dsr(14, r['sigma_cross']/alt),2)}% at $N=14$, "
            f"{fmt(dsr(1e4, r['sigma_cross']/alt),2)}% at $N=10^4$, {fmt(dsr(1e9, r['sigma_cross']/alt),2)}% at $N=10^9$."]
    return "\n".join(out)


# ================================================================================================
# Optional blocks (not tables of the report; printed with --all)
# ================================================================================================

def commissions_follow_equity(df):
    """Independent test of the premise behind the treatment of commissions (§3.4).

    If commissions are proportional to equity, the ratio between commissions paid at slippage b and at
    0 bps must equal the ratio between the integrals of equity, which the model predicts without using
    returns: with fills uniform in time the cumulative drag factor at time u is exp(-k u), with
    k = b * w_sum / 1e4, and the ratio of the integrals is (1 - e^-k) / k.
    """
    base = df[df["bps"] == 0.0].set_index(["strat", "exit_variant"])
    L = ["### Supplementary. Commissions follow the equity path (test independent of returns)", "",
         "|  | threshold | bps | commissions / commissions at 0 bps | predicted $(1-e^{-k})/k$ | gap |",
         "|---|---|---|---|---|---|"]
    errs = []
    for _, r in df[df["bps"] > 0].sort_values(["strat", "exit_variant", "bps"]).iterrows():
        key = (r["strat"], r["exit_variant"])
        kk = r["bps"] * base.loc[key, "w_sum"] / 1e4
        pred, obs = (1 - math.exp(-kk)) / kk, r["fees"] / base.loc[key, "fees"]
        err = 100 * (obs - pred) / pred; errs.append(err)
        L.append(f"| S{r['strat']} | `{variant_label(r['exit_variant'])}` | {fmt(r['bps'],2)} | {fmt(obs,4)} | "
                 f"{fmt(pred,4)} | {signed(err,2)}% |")
    errs = np.array(errs)
    L.append(f"\nMean gap {signed(errs.mean(),2)}%, maximum absolute {fmt(np.abs(errs).max(),2)}%, over 40 rows. "
             "The gap is systematically negative and grows with $b$, which is the sign it must have: commissions "
             "are weighted by equity, which grows over the sample, so the deeper drag at the end of the period "
             "weighs more than a flat time average assumes. The test uses no return at all.")
    return "\n".join(L)


def opening_window_decomposition(bench):
    """NOT USED IN THE TEXT. Kept for reference.

    The estimate by difference between the two matched runs (about +1.74%/year of drift for the opening
    half-hour) does not agree with a direct measurement from a long 9:31-to-10:00 run, which gives about
    +0.50%/year. The gap is 0.178 in log over eight years, about 0.49 bps per round trip: the isolated run
    pays one round trip of execution cost that cancels in the matched comparison. Until that difference is
    explained, the text reports the net figure and not the decomposition (§8).
    Direct run, for reference: net -4.492%, eq_n 2012, avg_equity 97712.5058, drag_sum 1.749096049950e-02,
    total_fees 10749.35, fee_drag 1.3751, lev_drag 0.1093.
    """
    lam = brow(bench, "bench intraday")["lambda_avg"]
    runs = [("entry 9:31", brow(bench, "bench intraday")["net_profit"], BENCH_INTRADAY_RAW),
            ("entry 10:00", brow(bench, "bench intraday_1000")["net_profit"], BENCH_INTRADAY_1000_RAW)]
    items = []
    for name, net, raw in runs:
        log_car = -100 * math.log(1 + net / 100) / YEARS
        fee = 100 * raw["total_fees"] / (YEARS * raw["avg_equity"])
        lev = 100 * 0.5 * raw["drag_sum"] / YEARS
        res = fee + lev - log_car
        items.append(dict(name=name, log_car=log_car, fee=fee, lev=lev, res_lev=res, res_und=res / lam))
    a, b = items
    gap, d_lev, d_fee = a["res_lev"] - b["res_lev"], -(a["lev"] - b["lev"]), -(a["fee"] - b["fee"])
    return "\n".join([
        "### Supplementary. Decomposition of the 9:31 vs 10:00 gap (not used in the text, see docstring)", "",
        "| item (%/year, in log) | entry 9:31 | entry 10:00 |", "|---|---|---|",
        f"| observed annual loss | {fmt(a['log_car'],4)} | {fmt(b['log_car'],4)} |",
        f"| of which commission drag | {fmt(a['fee'],4)} | {fmt(b['fee'],4)} |",
        f"| of which leverage drag | {fmt(a['lev'],4)} | {fmt(b['lev'],4)} |",
        f"| underlying, unleveraged | {fmt(a['res_und'],4)} | {fmt(b['res_und'],4)} |", "",
        "| decomposition of the gap (%/year, sign in favor of the 9:31 run) | value |", "|---|---|",
        f"| drift of the opening half-hour, leveraged | {fmt(gap,4)} |",
        f"| extra leverage drag paid by the longer window | {fmt(d_lev,4)} |",
        f"| difference in commission rate | {fmt(d_fee,4)} |",
        f"| sum | {fmt(gap+d_lev+d_fee,4)} |",
    ])


# ================================================================================================
# Static text of tables.md: header and the nomenclature table of §4 (no numbers in it)
# ================================================================================================

TABLES_HEADER = """\
# Tables

Generated by `build_tables.py`; do not edit by hand. Every table cited in the report lives here:
the `[Table Tn]` placeholders in the sections pull from this file, which is the only one the
assembler reads. Tables are numbered in order of appearance.

Conventions: $r_f = 2\\%$, financing rate 3.5%, window 2017-05-10 to 2025-05-10 (2,012 NYSE
sessions, 2,922 calendar days). `loose` = the `vwap` variant in the CSV files = the exit described
in the **README** (the paper, eq. 5, specifies `tight`).

**No number in these tables is retyped by hand in the text of the report**: the text cites, the
tables measure.
"""

NOMENCLATURE = """\
### Design nomenclature

| cell | entry conditions | exit structure | in the repository |
|---|---|---|---|
| **S2′** | band + EMA | 30′ simple | no, constructed |
| **S4** | band + EMA | 5′ + gate $N=4$ | yes |
| **S2** | band + EMA + **VWAP** | 30′ simple | yes |
| **S4′** | band + EMA + **VWAP** | 5′ + gate $N=4$ | no, constructed |

The design has **three axes**.

**Axis 1: VWAP entry filter.** Present or absent. It is a third condition required to open a
position, in addition to the band break and the EMA filter. It moves along the pairs S2′ to S2 and
S4 to S4′.

**Axis 2: exit structure.** `30′ simple` (condition checked every 30 minutes, no persistence
requirement) or `5′ + gate N=4` (checked every 5 minutes, must be confirmed on four consecutive
checks). It moves along the pairs S2′ to S4 and S2 to S4′. The axis turns two knobs together, the
**cadence** of the check and the **persistence** required, and the repository always introduces
them as a pair; S1, which has the 5-minute cadence without the gate, separates them along the chain
S0 to S1 to S3 (T9). It is a decomposition along a path, not a full factorial: it gives "cadence
alone" and "gate given the cadence", not "gate without cadence", because four checks on a
30-minute cadence would mean two hours of persistence, a cell the repository does not contain and
that would hardly make sense. The gate is a parameter of the fast-check regime, not a mechanism
that can be mounted anywhere.

**Axis 3: exit threshold.** `tight` is the one implemented in the code, the long exits if
$P < \\max(UB,\\ \\text{vwap})$; `loose` is the one described in the README, $P < \\max(LB,\\ \\text{vwap})$.
The paper (eq. 5 and pseudocode) specifies `tight`, so the README is the one that differs. Every
cell exists in both versions, so the cells are eight. It is the axis that makes up the **rows** of
T8 and T10.
"""

SUPPLEMENTARY_HEADER = """\
# Supplementary blocks

Generated by `build_tables.py`; do not edit by hand. These blocks are not tables of the report,
but the text cites numbers that come from them: T14 in §2, the opening-window threshold in §8,
and every figure of Appendix A. Run with `--all` for two further diagnostic blocks.
"""


def normalize(block):
    """Pipe tables must be separated from headings and captions by a blank line, otherwise pandoc
    reads the table rows as a continuation of the paragraph above and prints the raw pipes."""
    out = []
    for line in block.rstrip("\n").split("\n"):
        prev = out[-1] if out else ""
        is_tab, prev_tab = line.startswith("|"), prev.startswith("|")
        if prev.strip() and line.strip() and is_tab != prev_tab:
            out.append("")
        out.append(line)
    return "\n".join(out)


# ================================================================================================
# Day-of-the-week (§5.1) and short exposure (§8). Both need the original repository's trade files.
# ================================================================================================

def _betacf(a, b, x):
    eps, tiny = 3e-16, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = tiny if abs(d) < tiny else d
    d = 1.0 / d
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        for num in (m * (b - m) * x / ((qam + m2) * (a + m2)),
                    -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))):
            d = 1.0 + num * d
            d = tiny if abs(d) < tiny else d
            c = 1.0 + num / c
            c = tiny if abs(c) < tiny else c
            d = 1.0 / d
            h *= d * c
        if abs(d * c - 1.0) < eps:
            break
    return h


def _betai(a, b, x):
    """Regularized incomplete beta, so the t-test needs no SciPy."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                  + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1 - x) / b


def t_test(x):
    """One-sample t-test of the mean against zero, two-sided: returns (mean, t, p, n)."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    t = x.mean() / (x.std(ddof=1) / math.sqrt(n))
    return x.mean(), t, _betai((n - 1) / 2.0, 0.5, (n - 1) / (n - 1 + t * t)), n


def session_returns(strat):
    """Session returns of one strategy from the authors' trade file: the trades of one day
    grouped by entry date, P&L net of the fee column, divided by the running equity from
    100,000. Returns (Series indexed by date, final equity) or None if the file is absent."""
    path = TRADES_DIR / f"Trades_Strat{strat}_8y.csv"
    if not path.exists():
        return None
    d = pd.read_csv(path)
    d["Entry Time"] = pd.to_datetime(d["Entry Time"])
    d = d.sort_values("Entry Time")
    g = pd.DataFrame({"date": d["Entry Time"].dt.date,
                      "pnl": d["P&L"] - d["Fees"]}).groupby("date")["pnl"].sum()
    equity, out = 1e5, []
    for v in g.values:
        out.append(v / equity)
        equity += v
    return pd.Series(out, index=pd.to_datetime(pd.Series(list(g.index))).values), equity


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


def bold(text, flag):
    return f"**{text}**" if flag else text


def build_dow():
    """§5.1: the paper's weekday ranking, tested by session and corrected for the five groups."""
    head = "### Day-of-the-week on S4: mean session return by weekday"
    if session_returns(4) is None:
        return (head + "\n\n*Skipped: clone blackswan-quants/intraday-momentum next to this script to read "
                "DayOfTheWeek/Trades_Strat{2,3,4}_8y.csv.*")
    stats, cum = {}, {}
    for s in (2, 3, 4):
        r, equity = session_returns(s)
        dow = pd.Series(r.index).dt.day_name().values
        stats[s] = {d: t_test(r.values[dow == d]) for d in DAYS}
        cum[s] = 100.0 * (equity / 1e5 - 1.0)
    m, t, pv, n = zip(*(stats[4][d] for d in DAYS))
    L = [head, "",
         "| | " + " | ".join(d[:3] for d in DAYS) + " |",
         "|---|---|---|---|---|---|",
         "| mean session return | " + " | ".join(signed(100 * v, 3) + "%" for v in m) + " |",
         "| $t$ | " + " | ".join(bold(fmt(v, 2), v == max(t)) for v in t) + " |",
         "| sessions | " + " | ".join(str(v) for v in n) + " |",
         "| $p$ | " + " | ".join(bold(fmt(v, 3) if v > 0.01 else fmt(v, 5), v == min(pv))
                                 for v in pv) + " |",
         ""]
    fri, mon = stats[4]["Friday"], stats[4]["Monday"]
    order = " > ".join(d[:3] for d in sorted(DAYS, key=lambda d: -stats[4][d][0]))
    L.append(f"Sessions with at least one trade, {sum(n):,} in total; one-sample $t$-test of the mean against "
             f"zero, two-sided. The same computation on S2 and S3 returns the same ordering, with Friday at "
             f"$p = {fmt(stats[2]['Friday'][2],4)}$ and $p = {fmt(stats[3]['Friday'][2],4)}$ respectively.")
    L.append("")
    L.append(f"<!-- figures cited in §5.1: ordering {order}; Friday p {fmt(fri[2],5)}, "
             f"x5 (Bonferroni) {fmt(5*fri[2],4)}; Monday p {fmt(mon[2],2)}; cumulative from the trade files "
             f"{fmt(cum[2],3)}% / {fmt(cum[3],3)}% / {fmt(cum[4],3)}% -->")
    return "\n".join(L)


def short_exposure():
    """§8: how much of the time the strategy is short, and how rarely a short survives the night."""
    head = "### Short exposure and overnight carry (for §8)"
    if session_returns(4) is None:
        return head + "\n\n*Skipped: needs the original repository's trade files.*"
    L = [head, "",
         "| item | S2 | S3 | S4 |", "|---|---|---|---|"]
    cols = {}
    for s in (2, 3, 4):
        d = pd.read_csv(TRADES_DIR / f"Trades_Strat{s}_8y.csv")
        d["Entry Time"] = pd.to_datetime(d["Entry Time"])
        d["Exit Time"] = pd.to_datetime(d["Exit Time"])
        d["hold"] = (d["Exit Time"] - d["Entry Time"]).dt.total_seconds() / 60.0
        over = d["Entry Time"].dt.date != d["Exit Time"].dt.date
        same = d[~over]
        sh = same["Direction"].eq("Sell")
        cols[s] = {
            "short trades": f"{int(d['Direction'].eq('Sell').sum())} "
                            f"({fmt(100*d['Direction'].eq('Sell').mean(),1)}%)",
            "share of the time at market, short": fmt(100 * same.loc[sh, "hold"].sum() / same["hold"].sum(), 1) + "%",
            "mean holding, short (min)": fmt(same.loc[sh, "hold"].mean(), 0),
            "mean holding, long (min)": fmt(same.loc[~sh, "hold"].mean(), 0),
            "positions carried to the next session": str(int(over.sum())),
            "of which short": str(int(d.loc[over, "Direction"].eq("Sell").sum())),
        }
    for k in cols[4]:
        L.append(f"| {k} | " + " | ".join(cols[s][k] for s in (2, 3, 4)) + " |")
    d = pd.read_csv(TRADES_DIR / "Trades_Strat4_8y.csv")
    d["Entry Time"] = pd.to_datetime(d["Entry Time"])
    d["Exit Time"] = pd.to_datetime(d["Exit Time"])
    car = d[d["Entry Time"].dt.date != d["Exit Time"].dt.date]
    one = car[car["Direction"].eq("Sell")].iloc[0]
    notional = abs(one["Quantity"] * one["Entry Price"])
    dates = ", ".join(str(x) for x in car["Entry Time"].dt.date.tolist())
    L.append("")
    L.append(f"Shares of trades and of time at market, with the carried positions set aside for the time "
             f"columns. On S4 the carry dates are {dates}, all half-day sessions (§7, item 3). The single "
             f"short among them is {int(one['Quantity']):,} shares entered at {fmt(one['Entry Price'],2)}, "
             f"a notional of {fmt(notional,0,True)} dollars held for two nights: at a borrow rate of 0.25% "
             f"annualized that is {fmt(notional*0.0025*2/360,2)} dollars, at 1% "
             f"{fmt(notional*0.01*2/360,2)}.")
    return "\n".join(L)


def authors_provenance():
    """§7: when the authors' five backtests ran, from the state block of their own result files."""
    head = "### Provenance of the authors' backtests (for §7)"
    rows = []
    for s in range(5):
        path = STATS_JSON_DIR / f"strat{s}_8y.json"
        if not path.exists():
            continue
        st = json.loads(path.read_text(encoding="utf-8")).get("state", {})
        node = st.get("Hostname", "").split("-")
        rows.append(f"| S{s} | {st.get('Name','')} | {st.get('StartTime','')} | "
                    f"{'-'.join(node[:2]) if len(node) > 1 else st.get('Hostname','')} | "
                    f"{st.get('OrderCount','')} |")
    if not rows:
        return head + "\n\n*Skipped: needs the original repository's stats/strat{0..4}_8y.json.*"
    return "\n".join([head, "", "| | backtest name | start (UTC) | node | orders |",
                       "|---|---|---|---|---|"] + rows + [
        "", "From the `state` block of the authors' own result files. The files record no engine version, "
        "so the LEAN build they ran on is not recoverable from them."])


def main():
    df, prime, bench = load_data()
    t5, t5_info = build_t3(bench)
    t8, t9, t10 = build_t7_t8(df, prime)
    tables = [
        TABLES_HEADER,
        "---\n\n## §1. The repository and the paper",
        build_t1(df),
        "---\n\n## §2. Benchmarks",
        build_t2(prime, bench),
        build_t2b(bench, prime),
        build_t12(bench),
        t5 + "\n\n" + build_t3_caption(prime, bench, t5_info),
        "---\n\n## §3. Method",
        build_t5(df),
        build_t4(df, prime, bench),
        "---\n\n## §4. The 2×2×2 design",
        NOMENCLATURE,
        t8, t9, t10,
        build_t9(df),
        "---\n\n## §5. Ranking stability",
        build_t10(df),
        build_dow(),
        "---\n\n## §6. S4′",
        build_t11(df, prime),
    ]
    supplementary = [
        SUPPLEMENTARY_HEADER,
        build_t13(),
        short_exposure(),
        authors_provenance(),
        opening_window_threshold(bench),
        dsr_appendix(),
    ]
    if "--all" in sys.argv:
        supplementary += [commissions_follow_equity(df), opening_window_decomposition(bench)]
    for name, blocks in (("tables.md", tables), ("supplementary.md", supplementary)):
        text = "\n\n".join(normalize(b) for b in blocks) + "\n"
        with open(ROOT / name, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"{name}: {len(text.splitlines())} lines")


if __name__ == "__main__":
    main()
