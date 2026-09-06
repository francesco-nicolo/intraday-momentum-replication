# §8. Limitations

This report does not establish that S4′ holds up over time. All fourteen configurations are
measured on a single window, 2017-05-10 to 2025-05-10, and the best of the fourteen emerges from a
condition, the VWAP entry filter, that blocks only 1.4% to 1.7% of entries. That is exactly the
case in which the full sample can mislead, because an advantage concentrated on a few dozen trades
is more sensitive to the sub-window on which it is measured than an advantage spread over three
thousand. No rolling-window or out-of-sample analysis over time was carried out. The Deflated
Sharpe Ratio of Appendix A answers a different question, and answers it well (whether the best of
fourteen is distinguishable from selection noise), but it does not answer this one: it is not a
temporal validation, and it is declared as such in its own limitations. This is not a gap that
separates this report from the paper, since the "subperiod analysis on rolling 2-year windows to
detect strategy decay" appears among the paper's own lines of future work, §6.7; but sharing an
open question is not the same as having closed it. It remains the check that both lack, and it is
the first thing to do.

A second gap lies in the design. Of the four combinations of the two entry filters the sample
covers three (band + VWAP **without** EMA is missing), so each of the two conclusions of §4.4 holds
at one level of the other filter only, and the three-way interaction is not measurable. The
missing cell is also the only one the design points to as a possible candidate to beat S4′, and it
cannot be estimated without assuming precisely the interaction that is absent.

One more cell is missing, and its absence prevents attributing a mechanism rather than an
effect. To establish whether the cost of the five-minute cadence comes from the VWAP term, as the
paper suggests, or from the denser sampling of a noisy series, one would need the same cadence
with an exit condition free of the VWAP. The repository does not contain it, and the two available
variants do not stand in for it because they also differ in the distance of the threshold: §4.5
therefore establishes that the cadence has a cost, not why it does. For the same reason the
statement in §4.1 that the `tight` threshold typically binds early in the life of a position is a
geometric argument, not a measurement: the holding-time distribution of the trades was not
collected.

Half of the measured cells describe an exit that no formal specification defines. The `loose`
variant is not the paper's exit (§4.1 shows that on `tight` paper and code agree) but a reading of
the README's prose description. The reasons for measuring it are good, since it is the variant
under which the VWAP genuinely binds the exit and therefore the only one in which the published
justification of that term can be checked; but the results that concern it (the crossover, S4′
`loose`, half of §4.5) need to be understood as counterfactuals on a configuration that exists only as a
reading of the README's prose, not as measurements of what the repository does.

The cost reconstruction of §3 holds for this specific code architecture, in which entries and
exits read `data[symbol].close` and not a fill price. If a future version of the signal read
actual execution prices, the invariance of the trade sequence with respect to slippage would fall,
and with it the whole one-backtest method.

The cost model itself is linear in $b$ and uniform across all fills, regardless of time of day,
order size or the volatility regime of the moment. It models neither market impact nor any
dependence on intraday liquidity, which for the same notional traded could weigh differently on an
entry at 9:31 and one at 15:55. The level of additional slippage a real execution would incur is
not measured either: the 0.25 to 0.5 bps range used in §4.5 and §6 is a working assumption for a
liquid ETF traded at the market, and the crossovers of T11 sit inside it, so the conclusion that
`loose` wins at realistic costs is conditional on that assumption. The break-even levels
themselves are not.

One cost is not in the model at all, and it is worth saying why it need not be. The strategy is
short about half the time it is in the market: on S4, 816 of its 1,694 trades are short (48.2%),
and they account for 45.7% of the time at market, counting the positions that open and close in
the same session, with a mean holding period of 112 minutes against 124 on the long side. Stock
borrow, however, accrues on short positions held at the close of business, and the schedule that
gives the strategy its zero beta keeps it out of that charge almost entirely. Over the eight years
exactly five positions survive to the next session, all of them opened on half-day sessions where
the 15:58 liquidation branch is never reached (§7, item 3), and **only one of the five is short**:
913 shares of SPY carried over the Christmas holiday of 2018, a notional of 194,000 dollars held
for two nights. On an instrument that is general collateral the charge on that one position is a
few dollars over the whole window — 2.69 at a borrow rate of 0.25% annualized, 10.78 at 1% — so
the item is below the resolution of every comparison in this report. The same fact disposes of a
second one: a strategy that is short on 48% of its trades but never over a weekend carries no
exposure to recall or to a borrow rate that moves, which is what makes short exposure costly in
practice on names that are not general collateral. This is a property of the schedule, not a
result of the analysis, and it is recorded here because the cost sections would otherwise appear
to have overlooked it.

Two limits concern the result on the opening half-hour in §2, and they deserve stating alongside
it. The first: the gap between entry at 9:31 and entry at 10:00 is measured, 17.8 points, but it
is a net figure, not a decomposition. The extra half-hour brings together the drift of the window
and the additional variance that a leveraged position pays as drag, and the two terms have opposite
signs. Separating them was attempted in two ways, by difference between the two matched runs and
with a run on the opening half-hour alone, and the two estimates do not agree with each other: the
gap is of the order of one round trip of execution cost, which cancels in the matched comparison
and does not in the isolated run. The text therefore reports the net figure and not its
components. The second: the two runs that produce it both run at zero slippage, and the only
friction charged is the per-share commission, identical at any time of day. In reality the spread
at 9:31 is wider than at 10:00, so the run matched to the open receives a discount it would not
have in practice: the 17.8 points are an upper bound. The cost model just described does not
correct for this, because it applies a single $b$ to all fills and has no time-of-day dimension;
switching it on, the two runs would worsen by almost the same amount and the gap would stay where
it is.

The distance to be covered can be bounded, however. Since the 15:58 exit is common to both runs
and cancels, the cost has to be loaded on the entries alone, whose $w_{sum}$ is half of the total:
for the gap to vanish, an extra cost of **0.684 bps** on every 9:31 entry would be needed, paid
every day for eight years. The threshold is kept in basis points because that is where it is
invariant: converted to cents it has no single value, since SPY grew a great deal over the sample
while the tick stayed at one cent. The same threshold is worth fewer cents in 2017 than in 2025,
and the constraint, if it binds, binds at the start of the sample. It is nonetheless a wide
threshold for an instrument on which one cent covers the whole quote for most of the session, and
this is why the result of §2 is reported rather than withdrawn. How large the opening extra-spread
on SPY actually is, however, is not measured here; it is a judgment about the instrument, not a
datum of this report.

The report covers a single instrument (SPY), a single time window and a single rate regime. The
risk-free rate $r_f = 2\%$ and the financing rate of 3.5% are both conventions declared explicitly,
not calibrations. Neither is load-bearing: the Deflated Sharpe Ratio moves only between 99.6% and
98.0% for risk-free rates between 1% and 3% (Appendix A, §A.4.3), and the financing rate is a
common-sense choice over a reported sensitivity range (T5), not a measured value.

Two clarifications on the provenance of the numbers. The 0.25 and 0.5 bps columns of S2′ and S4′
are predicted and not measured (§6): they are the only part of the report that does not come from
a direct backtest. And the reproduction took place on a platform that has moved in the meantime:
relative to the authors' backtest files, commissions come out higher by between 0.24% and 0.51%
and the return lower by up to 0.29pp, in addition to the PSR gap discussed in §7. These are small
differences of constant sign, but they rule out treating the last digits of any comparison as
exact.

Finally, the Deflated Sharpe Ratio corrects for selection **within** the family of fourteen
configurations, not for the choice to study this family in the first place: that selection, the
publication of a strategy because it worked, took place upstream, and no downstream correction can
recover it. It is a structural limit of any analysis built on someone else's code, not specific to
this report, but it needs saying, because otherwise the DSR risks being read as a stronger
guarantee than it is.
