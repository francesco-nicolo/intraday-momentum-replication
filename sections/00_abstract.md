# §0. Abstract

`blackswan-quants/intraday-momentum` implements five variants of an intraday momentum strategy on
SPY and presents them as a progression that culminates in Strategy 4, which the paper describes as
Pareto-dominant. This report re-runs the five published backtests, checks them against the
authors' own result files, adds fifty-three more, and reaches four conclusions.

First, there is a signal. A benchmark with no signal at all, on the same instrument, with the same
leverage rule and the same trading window, loses 36.1% over the period in which the strategy gains
271.4%, and it loses in both directions: 30.7% with the position reversed. Aligning the
benchmark's entry time with the strategy's own removes a further 17.8 points from the benchmark:
the opening half-hour, which the thirty-minute cadence excludes by construction, is worth that much
to a passive leveraged position in this sample. The edge is more sensitive to execution costs than
its size suggests, however. Reconstructing the effect of transaction costs in closed form from a
single backtest, the 271.4% falls to zero at 2.2 basis points of slippage per trade, while
leveraged buy-and-hold at the same leverage survives up to 218.

Second, the comparison on raw return is the less informative one. The strategy's 271% sits below
the 350% of leveraged buy-and-hold, but the gap is about the size of the margin interest that the
backtest does not charge, so it does not support an argument in either direction. The rest of the
comparison does hold: a beta of -0.05 and a quarter of the drawdown, 9.0% vs. 40.2%, because a
strategy that is flat every night does not touch an equity premium that, over this window, lives
almost entirely overnight.

Third, the persistence gate does not appear to be a standalone source of edge. It offsets a cost
that the five-minute exit check introduces, and the cell that separates the two effects was already
in the repository, in Strategy 1, although it had not been used for that purpose.

Fourth, the best of the fourteen configurations examined is not in the repository, but it is one
line away from Strategy 4 and its lead is small. Adding to Strategy 4 an entry condition that is
present in the code of Strategy 2 but absent from both published descriptions gives S4′, which
closes with 3.4% more capital over eight years, about 0.4% per year, on the strength of the 22 to
26 trades the condition blocks, at the price of a slightly deeper drawdown; whether that lead
survives outside this sample is not tested here. Corrected for selection across fourteen trials
with the Deflated Sharpe Ratio, S4′ remains distinguishable from search noise, although the test
is against a zero edge, not against Strategy 4. That check matters because the one significance
statistic the paper reports, QuantConnect's PSR, no longer reproduces on the platform today.
