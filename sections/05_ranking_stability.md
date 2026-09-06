# §5. Ranking stability

The question is whether the conclusions of the previous sections survive when slippage is added,
and the answer is that they survive almost entirely: the ranking of the repository's five
strategies is stable within each exit variant across all five cost levels collected, both by
return and by Sharpe. This is a result in the paper's favor, and it deserves recording as such.
There is a single exception, and it is worth setting out.

[Table T12]

Under `tight`, the ranking by return is S4 > S3 > S2 > S0 > S1 at every level, from 0 to 2 bps.
Under `loose` it is S2 > S4 > S3 > S0 > S1, again unchanged. For Sharpe the same holds across the
whole table except at one point: at 0 bps, under `tight`, S1 has a Sharpe of 0.841 vs. 0.835
for S0 (0.842 vs. 0.835 in the authors' file), and therefore sits above the baseline. At 0.25
bps of additional slippage the order reverses, 0.585 vs. 0.665, and it does not reverse back
at any of the subsequent levels. It is the only inversion in the whole eight-year table.

It concerns the comparison, S0 vs. S1, on which the paper builds the Momentum Paradox, and it is
not a point against the paper. The authors make no claim on that step of Sharpe: their sentence is
"*degrading total return (196% → 177%), Sharpe (0.835 → 0.84, a near wash), and win rate (40% →
32%)*", and the parenthesis is theirs. They are right, and more completely than the word "near"
suggests: +0.005 on a quantity whose standard error, from the moments in Appendix A, is two orders
of magnitude larger, is exactly a wash. The Momentum Paradox does not rest on that number anyway
but on the return, which loses nineteen points and never moves in the ranking: S1 remains last at
all five cost levels.

What costs add is that the one ambiguous ordering stops being ambiguous. At 0.25 bps the Sharpe
of S1 is no longer a wash but a clear deterioration, and all four metrics of that step move in the
stated direction. **Costs do not overturn the paper's conclusion: they sharpen it.** It is the case
in which the strategy most penalized by costs is also the one the paper identified as the weakest,
and the coincidence is not accidental: S1 has 4,900 orders vs. the baseline's 3,594, that is,
the highest $w_{sum}$ of the fourteen configurations, so it is the row that decays fastest as soon
as the cost rises.

[Figure F3]

## 5.1 The same standard, applied to the paper's own ranking

The paper breaks its trades down by weekday and reports the ordering Friday > Wednesday >
Thursday > Tuesday > Monday, reading it as "a robust feature of market microstructure rather than
a mislead caused by overfitting" (paper, §5.5, Table 9). The selection question this report
applies to itself in §A.3 — fourteen configurations searched, one reported — applies to any
ranking over five groups. Applying it to one's own results and not to the ranking one is checking
would make the severity selective, so it is applied here as well.

The authors' own files answer it. Aggregating `DayOfTheWeek/Trades_Strat{2,3,4}_8y.csv` by entry
date, with P&L net of the fee column, so that the several trades of one day count once and
within-day correlation cannot inflate anything, and testing each weekday's mean session return
against zero:

[Table: Day-of-the-week on S4: mean session return by weekday]

The ordering reproduces the paper's exactly. Friday's mean carries $p = 0.0011$ on its own and
0.0054 once multiplied by the five groups the maximum was selected from, so it stands at the 1%
level under the most conservative correction available; Monday is indistinguishable from zero
($p = 0.44$), consistent with the paper's reading of it as the weakest session. The ranking
survives the standard this report applies to itself, and that is a result in the paper's favor.

One check falls out of the same reconstruction at no cost. Compounding those session returns from
the trade files alone, with no backtest involved, returns cumulative eight-year figures of
227.331%, 252.214% and 259.235% for S2, S3 and S4, against the 227.320%, 252.248% and 259.235% of
the authors' result files: within four hundredths of a point on the first two and coinciding to
the third decimal on the third. It is an independent verification of three rows of T1, reached
from the trade lists rather than from a re-run.
