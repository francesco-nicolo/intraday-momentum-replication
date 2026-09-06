#!/usr/bin/env python3
"""
make_figures.py: regenerates the three figures of the report from the raw backtest data.

    python make_figures.py

Outputs (under figures/):
  F1_out_of_sample_validation.png   predicted vs measured net profit on the 40 out-of-sample rows,
                                    and residuals in bps of terminal log wealth against slippage
  F2_factorial_design.png           the four cells of the VWAP entry filter x exit structure plane
  F3_net_profit_vs_slippage.png     decay of net profit under additional slippage, all ten rows

Everything is computed from data/*.csv with the same formulas as build_tables.py.

Two rules of layout, because both are easy to get wrong and both cost legibility in the PDF:

  1. A figure is drawn at the width it is printed at (FIG_W below is the report's text block,
     16.2cm), and saved without a tight bounding box so that the file keeps that width. LaTeX
     scales an image down to the text width, so a figure drawn ten inches wide comes out at 64%
     and every label with it; drawn and saved at 6.38in it prints one to one, an 8pt label is an
     8pt label, and the figure fills the text block instead of floating short of it.
  2. No figure carries its own title. The caption under it comes from assemble.py, and a title
     inside the image would print the same sentence twice.
"""
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)

FIG_W = 6.38          # inches: \textwidth of the report, a4paper with 2.4cm margins
DPI = 300
BLUE, ORANGE = "#1f77b4", "#e8710a"
GREY = "0.35"
# one color per strategy, solid for `tight` and dashed for `loose`: five colors to tell apart
# instead of ten, which is what makes F3 readable
STRAT_COLORS = ["#4c72b0", "#dd8452", "#55a868", "#c44e52", "#8172b3"]

plt.rcParams.update({
    "font.size": 8.5,
    "axes.titlesize": 9,
    "axes.labelsize": 8.5,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 7.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linewidth": 0.6,
    "figure.dpi": DPI,
    "savefig.dpi": DPI,
    # no bbox="tight": the saved file must be exactly FIG_W wide, so that LaTeX neither scales it
    # down (shrinking every label with it) nor leaves it short of the text block
    "savefig.pad_inches": 0.01,
})


def log_ret(net_pct):
    return math.log(1 + net_pct / 100.0)


def load():
    df = pd.read_csv(DATA / "backtest_data_strategies.csv")
    df["strat"] = df["strat"].astype(str)
    prime = pd.read_csv(DATA / "backtest_data_prime.csv")
    bench = pd.read_csv(DATA / "backtest_data_benchmarks.csv")
    return df, prime, bench


def declutter(ys, gap):
    """Push labels apart so none overlaps, keeping their order and staying near where they belong."""
    order = np.argsort(ys)
    out = np.array(ys, dtype=float)
    for k in range(1, len(order)):
        i, j = order[k - 1], order[k]
        if out[j] - out[i] < gap:
            out[j] = out[i] + gap
    return out


# ------------------------------------------------------------------------------------------------
# F1: out-of-sample validation of the cost reconstruction
# ------------------------------------------------------------------------------------------------

def figure_f1(df):
    base = df[df["bps"] == 0.0].set_index(["strat", "exit_variant"])
    rows = []
    for _, r in df[df["bps"] > 0].iterrows():
        key = (r["strat"], r["exit_variant"])
        R0, w = base.loc[key, "net_profit"], base.loc[key, "w_sum"]
        pred = 100 * (math.exp(log_ret(R0) - r["bps"] / 1e4 * w) - 1)
        resid = 1e4 * (log_ret(pred) - log_ret(r["net_profit"]))
        rows.append(dict(strat=r["strat"], variant=r["exit_variant"], bps=r["bps"],
                         measured=r["net_profit"], predicted=pred, resid=resid,
                         w2n=w ** 2 / base.loc[key, "orders"]))
    d = pd.DataFrame(rows)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(FIG_W, 2.9))

    for variant, color, marker, label in [("tight", BLUE, "o", "tight"), ("vwap", ORANGE, "s", "loose")]:
        s = d[d["variant"] == variant]
        ax1.scatter(s["measured"], s["predicted"], c=color, marker=marker, s=13,
                    linewidths=0, label=label, zorder=3)
    lim = [d["measured"].min() - 15, d["measured"].max() + 15]
    ax1.plot(lim, lim, color="0.55", lw=0.7, zorder=2)
    ax1.set_xlim(lim); ax1.set_ylim(lim)
    ax1.set_xlabel("measured net profit (%)")
    ax1.set_ylabel("predicted from the 0 bps run (%)")
    ax1.set_title("A. The 40 out-of-sample rows", loc="left")
    ax1.legend(title="exit threshold", title_fontsize=7.5, loc="lower right", frameon=False)
    ax1.text(0.04, 0.93, "at this scale the error\nis not visible: see B", transform=ax1.transAxes,
             fontsize=7, color=GREY, va="top")

    # the residuals sit on four slippage levels; spread the points of each level so none hides another
    off = d[(d["strat"] == "1") & (d["variant"] == "tight") & (d["bps"] == 2.0)].iloc[0]
    reg = d.drop(off.name)
    levels = sorted(d["bps"].unique())
    pos = {b: i for i, b in enumerate(levels)}
    rng = np.random.default_rng(0)
    for variant, color, marker, label in [("tight", BLUE, "o", "tight"), ("vwap", ORANGE, "s", "loose")]:
        s = reg[reg["variant"] == variant]
        x = np.array([pos[b] for b in s["bps"]], dtype=float)
        x = x + (-0.13 if variant == "tight" else 0.13) + rng.uniform(-0.06, 0.06, len(x))
        ax2.scatter(x, s["resid"], c=color, marker=marker, s=13, linewidths=0, zorder=3)
    xx = np.linspace(-0.3, len(levels) - 0.7, 100)
    bb = np.interp(xx, range(len(levels)), levels)
    ax2.plot(xx, bb ** 2 / 2e8 * d["w2n"].mean() * 1e4, "--", color="0.4", lw=0.9,
             label="$O(b^2)$ term discarded by the model")
    ax2.axhline(0, color="0.55", lw=0.7)
    top = 8
    ax2.set_ylim(-4, top)
    ax2.set_xlim(-0.45, len(levels) - 0.55)
    ax2.scatter([pos[2.0] - 0.13], [top - 0.25], marker="^", c="0.35", s=26, zorder=4, clip_on=False)
    ax2.annotate(f"off scale: S1 tight at 2 bps, residual\n{off['resid']:.0f} bps. That run closes at "
                 f"{off['measured']:.1f}%, where\nthe log amplifies the same "
                 f"{abs(off['predicted']-off['measured']):.3f}pp\nof absolute error",
                 xy=(pos[2.0] - 0.13, top - 0.25), xytext=(-0.3, top - 0.35), fontsize=6.8, color=GREY,
                 va="top", arrowprops=dict(arrowstyle="-", color="0.6", lw=0.6))
    ax2.set_xticks(range(len(levels)))
    ax2.set_xticklabels([("%g" % b) for b in levels])
    ax2.set_xlabel("additional slippage (bps)")
    ax2.set_ylabel("predicted minus measured\n(bps of terminal log wealth)")
    ax2.set_title("B. Residuals", loc="left")
    ax2.legend(fontsize=6.8, loc="lower center", frameon=False)   # colors are keyed in panel A

    fig.tight_layout(w_pad=1.6)
    fig.savefig(OUT / "F1_out_of_sample_validation.png")
    plt.close(fig)


# ------------------------------------------------------------------------------------------------
# F2: the 2x2 plane VWAP entry filter x exit structure, under the two exit thresholds
# ------------------------------------------------------------------------------------------------

def figure_f2(df, prime):
    def lr(strat, variant):
        if "prime" in str(strat):
            r = prime[(prime["strat"] == strat) & (prime["exit_variant"] == variant)].iloc[0]
        else:
            r = df[(df["strat"] == str(strat)) & (df["bps"] == 0.0) & (df["exit_variant"] == variant)].iloc[0]
        return log_ret(r["net_profit"])

    cells = [("S2′", "2 prime", "no VWAP\n30′ simple exit"),
             ("S4", "4", "no VWAP\n5′ + gate $N=4$"),
             ("S2", "2", "VWAP\n30′ simple exit"),
             ("S4′", "4 prime", "VWAP\n5′ + gate $N=4$")]
    x = np.arange(len(cells)); w = 0.36
    fig, ax = plt.subplots(figsize=(FIG_W, 3.1))
    for offset, variant, color, label in [(-w / 2, "tight", BLUE, "tight"), (w / 2, "vwap", ORANGE, "loose")]:
        vals = [lr(s, variant) for _, s, _ in cells]
        ax.bar(x + offset, vals, w, color=color, label=label, zorder=3)
        for xi, v in zip(x + offset, vals):
            ax.text(xi, v + 0.004, f"{v:.3f}", ha="center", va="bottom", fontsize=7, color="0.2")
    ax.set_xticks(x)
    ax.set_xticklabels([f"$\\bf{{{n}}}$\n{lab}" for n, _, lab in cells])
    ax.set_ylim(1.10, 1.345)
    ax.set_ylabel("log return over 8 years")
    ax.legend(title="exit threshold", title_fontsize=7.5, loc="upper left", frameon=False, ncol=2)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(OUT / "F2_factorial_design.png")
    plt.close(fig)


# ------------------------------------------------------------------------------------------------
# F3: decay of net profit under additional slippage
# ------------------------------------------------------------------------------------------------

def figure_f3(df, bench):
    levels = sorted(df["bps"].unique())
    x = np.arange(len(levels))
    fig, ax = plt.subplots(figsize=(FIG_W, 4.0))

    # a band of clear space above the curves for the two notes and the legend
    ymin, ymax = -78.0, 305.0
    ends, series = [], []
    for i, s in enumerate("01234"):
        for variant, ls, label in [("tight", "-", "tight"), ("vwap", (0, (4, 2)), "loose")]:
            d = df[(df["strat"] == s) & (df["exit_variant"] == variant)].sort_values("bps")
            y = d["net_profit"].to_numpy()
            ax.plot(x, y, linestyle=ls, marker="o", ms=2.6, lw=1.2, color=STRAT_COLORS[i], zorder=3)
            ends.append(y[-1]); series.append((f"S{s} {label}", STRAT_COLORS[i]))

    # the ten curves end within a few points of one another: label them at the right edge, spread
    # just enough not to overlap, instead of asking the reader to match ten entries in a legend
    placed = declutter(ends, gap=0.033 * (ymax - ymin))
    for (name, color), y0, y in zip(series, ends, placed):
        ax.annotate(name, xy=(x[-1], y0), xytext=(x[-1] + 0.14, y), fontsize=7.4, color=color,
                    va="center", annotation_clip=False,
                    bbox=dict(facecolor="white", edgecolor="none", pad=0.8),
                    arrowprops=dict(arrowstyle="-", color=color, lw=0.5, alpha=0.55,
                                    shrinkA=1, shrinkB=1))

    bi = bench[bench["strat"] == "bench intraday"].iloc[0]
    h = bench[bench["strat"] == "bench hold24"].iloc[0]
    ax.axhline(0, color="0.6", lw=0.7)
    ax.axhline(bi["net_profit"], color="0.45", lw=0.8, ls=":")
    ax.text(0.06, bi["net_profit"] + 6, f"bench intraday ({bi['net_profit']:.1f}%)", fontsize=7.2,
            color=GREY, va="bottom",
            bbox=dict(facecolor="white", edgecolor="none", pad=1.0))
    b_star_h = 1e4 * log_ret(h["net_profit"]) / h["w_sum"]
    ax.text(0.01, 0.985, f"bench hold24: {h['net_profit']:.1f}%  ($b^*\\approx${b_star_h:.0f} bps, off scale)",
            transform=ax.transAxes, fontsize=7.2, color=GREY, va="top")

    ax.set_xticks(x)
    ax.set_xticklabels([("%g" % b) for b in levels])
    ax.set_xlim(-0.15, len(levels) - 0.55)
    ax.set_xlabel("additional slippage (bps)")
    ax.set_ylabel("net profit (%)")
    ax.set_ylim(ymin, ymax)
    ax.grid(axis="x", visible=False)
    solid = plt.Line2D([], [], color="0.35", ls="-", lw=1.2)
    dashed = plt.Line2D([], [], color="0.35", ls=(0, (4, 2)), lw=1.2)
    ax.legend([solid, dashed], ["tight", "loose"], title="exit threshold", title_fontsize=7.5,
              loc="upper right", frameon=False, ncol=2)
    fig.tight_layout()
    fig.subplots_adjust(right=0.855)
    fig.savefig(OUT / "F3_net_profit_vs_slippage.png")
    plt.close(fig)


if __name__ == "__main__":
    df, prime, bench = load()
    figure_f1(df)
    figure_f2(df, prime)
    figure_f3(df, bench)
    print("figures written to", OUT)
