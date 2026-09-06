# §7. Reconciling the paper with the code

Four items in which the published description, the published code and what reproduces today do
not coincide. Two lie in the text of the paper, one concerns the reproducibility of a platform
statistic, and one is a detail of the committed source, stated for completeness.

**1. The Probabilistic Sharpe Ratio does not reproduce.** The paper reports a PSR of 83.4% for
S4, which is exactly what the authors' own `stats` file contains (83.439%). Re-running the same
code today returns **44.342%**, and this is not an isolated case: the same difference, 39 to 46
points, appears on all five strategies (T1). The paper transcribes its own output correctly, so
this is not something the authors could have controlled, and it is the only platform statistic
that does not come back after a lapse of time on the same code, since orders, Sharpe, drawdown,
win rate and turnover all agree to within rounding.

What changed is the platform, not the original work.
Two things follow, and they point in opposite directions. Today's value is well defined and can be
checked: Appendix A, §A.8 reproduces it from the moments of the same run, to within half a point,
once LEAN's own definition is used, in which the PSR is measured against a benchmark Sharpe of 1
rather than against zero. But a statistic that moves by forty points on unchanged code
and unchanged data cannot be cited as evidence for or against anything, which is why Appendix A
computes the Deflated Sharpe Ratio from the raw moments of the returns rather than from it. What
the difference between the two eras is remains unexplained here.

**Provenance of the two sides of this comparison.** An argument that a platform has moved is only
worth as much as the two runs behind it can be dated, so both are recorded here. On the authors'
side the `state` block of each `stats/strat{s}_8y.json` carries the backtest's own timestamps: S1,
S2 and S3 ran on 18 March 2026 between 14:47 and 14:59 UTC, S0 on 20 March at 17:32 and S4 on 23
March at 08:34, on nodes `BACKTESTING-80` and `BACKTESTING-219`, and the order counts in those
same blocks are the ones reproduced in T1. Those files record no engine version, so the build the
authors ran on is not recoverable from them. On this side, the reproduction used the repository at
commit `e60646cd7c05b94b59f555122150dd1aa19ba5e0` and ran between 26 August and 3 September 2026.
The strategy sources have not changed since commit `b960d36` of 23 March 2026: the two commits that
follow it add the paper and the trade files of `DayOfTheWeek/` and touch no code, so the `strats/`
directory of the commit used and of the authors' final state are the same files. What is not fixed
is the engine. The projects are configured to follow QuantConnect's master branch, so each backtest
ran on whichever build was deployed that day: the S0 runs of 26 August report LEAN engine
v2.5.0.0.18034 in their log header, and master stood at v18057 on 4 September, twenty-three builds
later in nine days. Five months of that cadence separate the two columns of the table above. This
dates the gap; it does not explain it.

**2. S2 requires three entry conditions, not two.** Equations (7) and (8) of the paper describe a
"dual confirmation" entry, $P_t > UB_t$ **and** $P_t > EMA_{100}(t)$. In `strategy2.py` the entry
requires three: band **and** VWAP **and** EMA. The difference is in the paper's own text, not only
in the README that summarizes it, and this is the one item of the four that touches the
interpretation of the results: the S2 vs. S4 comparison, half of the final comparison in Table 7,
is confounded on two axes rather than one. It is the reason S2′ and S4′ were constructed (§4, §6).

**3. The 15:58 liquidation does not fire on half-day sessions.** The paper states that all
positions are compulsorily liquidated at 15:58 ET. The branch `hour == 15 and minute >= 58` is
never reached on the seventeen half-day sessions of the window, which close at 13:00, and the
position stays open overnight. The magnitude is negligible, but the statement does not hold as
written on those days. The seventeen dates can be verified one by one against the exchange
calendar, and they account for **17 of the 27 carryover nights** identified by an entirely
independent route in §3, from the $w_{sum}$ shortfall on the benchmark. The other ten have no
verified explanation in this report, and it is more accurate to say so than to round the counts
until they agree.

**4. The EMA warm-up is shorter than the indicator.** The 100-period EMA, described as a
structural trend-confirmation filter, is built with `Resolution.Minute` and 100 periods, while
the warm-up is `SetWarmUp(14, Resolution.Daily)`: 14 daily bars, not 100 one-minute bars. As a
result `ema.IsReady` becomes true only about 86 minutes into the first usable session, not before
the start as the declared warm-up would suggest. Anyone who opens the code can verify this, and
it is stated here for completeness.
