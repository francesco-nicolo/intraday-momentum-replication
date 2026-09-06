# §6. S4′: a configuration the repository does not include

§4 decomposes the repository's design and finds that the VWAP entry filter is additive edge,
separate from everything else. If it is, the best configuration is not S4: it is S4 with that
condition added, S4′, and it was never run in the repository because no cell crosses all three
entry filters with the persistence-based exit structure at the same time.

[Table T13]

At 0 and at 0.25 bps the leading configuration is S4′ `tight`. At 0.5 bps S4′ `loose` takes the
lead, since it has a lower $w_{sum}$ and therefore decays more slowly, and the top three close to
within two percentage points: 176.7 vs. 174.8 for S4′ `tight` and 174.6 for S2 `loose`. In one
form or the other S4′ is therefore first at all three levels, but it is not always the same
variant, and the highest break-even of the fourteen configurations does not belong to S4′ `tight`
(2.178 bps) but to S4′ `loose`: **2.462 bps**.

Two questions follow, and they are separate. Among the cells that are in the repository, the best
at 0 bps is S2 `loose`, not S4 `tight`: 259.7% vs. 259.2%, and 2.372 bps of break-even vs. 2.088.
Completing the factorial then adds **11.7 percentage points of return** over that best repository
cell, 271.4% for S4′ `tight` against 259.7%, and **0.09 bps of cost tolerance**, 2.462 for S4′
`loose` against 2.372. The second figure is small in absolute terms but it is 3.8% of the
available margin, on a family whose break-evens all lie between 1.15 and 2.46 bps.

The size of the lead should be kept in view. Over S4 `tight`, the paper's own final configuration,
S4′ `tight` gains $+0.033$ in log return over eight years (T8), that is, 3.4% more final capital,
about 0.4% per year, and the whole of it comes from the 22 to 26 trades the entry condition blocks
(§4.2). One caveat cuts against the result, because the table shows it: **S4′ does not dominate S4
in the Pareto sense.** Return, Sharpe and break-even improve; the drawdown worsens, 9.0% vs. 8.4%.
The dominance the paper reports for S4 cannot be repeated for S4′ here. The Deflated Sharpe Ratio
of Appendix A, which finds S4′ distinguishable from selection noise, tests it against a zero edge,
not against S4: whether the margin between the two survives outside this sample is a question
these data do not answer (§8). S4′ is best read as S4 plus a small increment of consistent sign,
not as a different strategy.

That the 0.25 and 0.5 bps columns of the two constructed cells are predicted by the model of §3
rather than measured is consistent with the rest of the method, since the cost model was validated
on forty independent rows; but it is the only part of the table that does not come from a direct
backtest, and §8 records it as such.

The register in which this result is presented matters as much as the result itself. It is not
"this analysis beat the repository": the condition that separates S4′ from S4 is already written
in the repository, in S2, and crossing it with the exit structure of S4 required no new idea, only
a cell of the factorial that had not been run. This is why S2′ and S4′ stay in a separate table and are labeled as
constructions of this report rather than as repository code. The distinction between "what the
repository measured" and "what the factorial implies" is the point of the section, not a
formatting detail.
