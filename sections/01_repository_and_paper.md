# §1. The repository and the paper

`blackswan-quants/intraday-momentum` is a QuantConnect/LEAN repository that implements five
variants (Strategy 0 to Strategy 4) of an intraday momentum strategy on SPY, backtested from
May 10, 2017 to May 10, 2025 (2,012 NYSE sessions) with an initial capital of 100,000 dollars.
The design is in the lineage of Zarattini, Aziz and Barbon (2024), which the paper acknowledges.
Every number in this report refers to that window. The common core, identical in all five, is a
breakout threshold recomputed every minute of the session: an upper band and a lower band derived
from the 14-day moving average of the absolute excursions from the open, and a vol-targeted
leverage

$$\Lambda = \min\!\left(2,\ \frac{0.02}{\sigma_{14g}}\right)$$

that sizes the exposure to target a daily portfolio volatility of 2%. Every position is forcibly
liquidated at 15:58 ET.

The five variants differ along three axes: whether entry requires only the band break or also
confirmation from a trend filter (a 100-period EMA and, in S2 only, the VWAP as well, a third
condition absent from both published descriptions; see §4.1); the cadence at which the exit is
checked, every 30 minutes or every 5; and whether the exit fires on the first violation or only
after the violation has persisted for $N=4$ consecutive checks. The paper presents them as a
progression: S1 speeds up the exit check, S2 adds the trend filter, S3 adds persistence, and S4
combines them all. It reads the decline from S0 to S1 (return from 196% to 177%, win rate from 40%
to 32%, with the Sharpe ratio almost unchanged) as what it calls the Momentum Paradox: a more
aggressive risk control, without a filter on noise, destroys the return it is meant to protect.
The comparison that closes the paper is instead between S4 and the two single-mechanism
configurations, S2 and S3 (Table 7): S4, at 259% with a Sharpe of 1.036, is presented as the
composition of the two mechanisms and described as Pareto-dominant.

This reading rests on an implicit assumption: that each row of the table isolates a single change
relative to the row before it. §4 shows that this assumption does not hold. S2 and S4, the
comparison on which the paper builds its final conclusion, differ on **two** axes at once, not
one; and cadence and persistence, introduced together in the step from S0/S2 to S3/S4, turn out to
be separable in the available data, which is not what the design suggests at first sight.

It also rests on a point of comparison. The paper adopts only one: SPY bought and held, which over
the window returns 166.4% with a Sharpe of 0.47 and a drawdown of 33.7%, and which S0 exceeds
with its 196% (paper, §3.2). The comparison is between a leveraged strategy, whose
leverage rule averages 1.81, and a benchmark at leverage 1. That is the point from which §2 starts.

Before going into the substance, we run an elementary check against the strongest source
available: not the rounded table in the README but `stats/strat{0..4}_8y.json`, the authors' own
backtest output, preserved in the repository.

[Table T1]

Orders, drawdown and win rate match exactly on all five rows; Sharpe matches to within a
thousandth, turnover to within a hundredth of a point. Return matches to within 0.29 percentage
points (pp) in the worst case (S1) and 0.06pp in the best (S4), always on the low side, and the
gap has an identifiable cause: the commissions of the new runs are higher by between 0.24% and
0.51% **at exactly the same order count**, so the difference lies in the fill prices, not in the
strategy. The code in the repository does today what it did for the authors.

**One exception, and only one**: the Probabilistic Sharpe Ratio does not reproduce on any of the
five rows, with a gap of between 39.1 and 45.8 percentage points, 41.3 on average. This is not a
code reproducibility problem, and it is not something the authors could have controlled: it is a
platform statistic that has not remained stable over time. The discussion is
in §7 and in Appendix A, where it becomes the reason for computing the Deflated Sharpe Ratio from
the raw moments rather than citing it.

Beyond that, the issue this report takes up is not the reproducibility of the numbers. It is what
those numbers allow one to conclude, and that is the question the sections that follow answer.

## 1.1 Conventions and units

Three different quantities appear in what follows, and they are fixed here, because confusing
them changes the conclusions by a factor of three.

**Return.** Unless otherwise stated, "return" is the cumulative return over the full eight-year
window, net of commissions, as QuantConnect reports it: the 196.125% of S0 means that 100,000
dollars become 296,125.

**Log return.** When *effects* are compared (how much an entry condition is worth, how much a
cadence costs), the metric is $\ln(1+R)$, and differences between cells are differences of
logarithms. A value of $-0.06508$ means that final wealth is $e^{-0.06508} = 93.7\%$ of the
reference's, that is, 6.3% less; on cumulative return the same gap is worth 18.7 percentage
points, because the return is compounded over eight years. The two readings must not be mixed.

The choice of the logarithm is not cosmetic. The cells of the design start from different levels,
196% under `tight` and 229% under `loose`, and only a proportional measure makes them comparable.
Above all, the factorial design of §4 rests on tests of the form "the interaction is zero,
therefore the two effects are additive": if two independent effects multiply wealth by $(1+a)$ and
$(1+b)$, in percentage points the combined effect is $a+b+ab$, and a spurious interaction equal to
the product would appear; with the values at stake, about ten times the one actually measured. In
logarithms, independent effects add by construction, so an interaction that is zero to the fourth
decimal place means something.

**Basis points (bps) of terminal log wealth.** In §3 the residuals of the cost model are measured
in this unit: 1 bps is 0.01% of the final multiplier. It is needed because the same error in
percentage points weighs differently on a run that closes at $+250\%$ and on one that closes at
$-53\%$, so in percentage points the residuals would not be comparable across rows.

**Costs.** The horizontal axis of every cost chart and cost table is the **additional** slippage:
the 0 bps level is not a backtest without costs, it is a backtest that pays Interactive Brokers
commissions in full and nothing else. The risk-free rate is set at $r_f = 2\%$ and the margin
financing rate at 3.5%, both conventions declared in advance and discussed where they are used.
