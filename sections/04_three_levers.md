# §4. The three levers

Given that this is a zero-beta diversifier, is it well built? The repository presents S0 to S4 as a
ladder: each strategy adds something to the previous one and the return rises. This section takes
the ladder apart and asks what each rung is worth on its own.

## 4.1 The design

S2 and S4, the two configurations on which the paper builds its final comparison, differ on
**two** axes rather than one. S2 requires three confirmations at entry (band, EMA, VWAP), the
third of which does not appear in either published description, since equations (7) and (8) of
the paper state two, and it exits on a simple check every 30 minutes. S4 requires two (band, EMA)
and exits on a check every 5 minutes that must be confirmed on four consecutive bars. Comparing
them directly does not say which of the two changes produced the difference.

The two missing cells were built: **S2′** is S2 without the VWAP entry condition, **S4′** is S4
with that condition. Neither is repository code, and their rows sit in a separate, labeled table.

The third axis is not a design choice but a point on which the published descriptions differ, and
it is not where one would expect. The code exits a long position when $P < \max(UB,\ \text{vwap})$,
where $UB$ is the same upper band that authorized the entry. This is exactly what the paper
specifies, in equation (5) and in the pseudocode (Code 1): **paper and implementation agree.** It
is the README that diverges, describing the exit as the price crossing back through the VWAP or
through *the opposite band*, that is, $P < \max(LB,\ \text{vwap})$. The two variants are called
`tight`, the one specified and implemented, and `loose`, the one that exists only in the
repository's prose description. Every cell exists in both.

The `tight` exit is not an idiosyncrasy of the repository: it is the dynamic trailing stop of the
design the strategy descends from, Zarattini, Aziz and Barbon (2024), where the position is closed
when the price crosses back through the boundary of the noise area, in the variant that takes the
higher of that boundary and the intraday VWAP. What is noted here is only its geometry, which does
not depend on which of the two texts one follows. A long entry occurs with $P > UB_t$, and the
exit threshold at the next check is $\max(UB_\tau,\ \text{vwap}_\tau)$: two bands evaluated at
different instants, but they share their anchor, because
$\max(O_{\text{today}},\ C_{\text{yesterday}})$ is fixed at the open and does not change for the
rest of the day. They therefore differ only through $\sigma$, the fourteen-day average of the
absolute excursion from the open at that clock minute, a quantity that grows over the session
because it measures how far the price has typically already moved. In the typical case
$UB_\tau \ge UB_t$, and **the `tight` exit threshold sits at or above the level that authorized
the entry**: the stop distance is zero or negative. It can narrow locally, because $\sigma$ is
estimated on fourteen observations per minute and is noisy between adjacent minutes, so this is
not a structural guarantee; but the gap involved remains a fraction of the band width, not a stop
distance. On this reading, what the exit cadence measures under `tight` is less the whipsaw on the
VWAP than the distance of the stop. How early in the life of a position the condition typically
becomes true is not measured here, since the holding-time distribution was not collected (§8).

This makes `loose` more than a curiosity. The paper motivates the VWAP term by describing it as
"volume-adaptive, institutionally relevant" and as a quantity that "self-widens throughout the
session, giving winning trades room to run". Under the formula the paper itself writes, however,
the term cannot give room to anything: when the VWAP rises above the
band, the `max` selects the VWAP, which is **higher**, and the position is closed *earlier* than
the band alone would close it. The term can only tighten the exit, never loosen it, and this
conclusion does not depend on how often it binds. `loose` is not an arbitrary correction: it is
the reading of the exit under which the published justification holds.

A note on nomenclature, because the term *vwap* appears in three distinct roles: the **entry
filter** (axis 1), the **term inside the `max` of the exit threshold** (present in both variants,
hence constant across the design), and the value `vwap` in the `exit_variant` column of the CSV
files, a name inherited from the data collection that means `loose`. The text always uses `loose`.

[Table: design nomenclature]

## 4.2 The VWAP entry filter is additive

Effect of the VWAP condition alone, in eight-year log return, holding the exit structure fixed:

[Table T8]

The interaction is of order $5\cdot10^{-4}$, that is, 1.3% of the main effect under `tight` and
1.7% under `loose`, and it **changes sign** between the two exit variants: noise, not an effect.
The condition produces the same gain whether or not the S4 exit package is present, and the same
under both thresholds.

One point needs clarifying at once, because it bounds the claim: all four cells of the table have
the EMA filter. What is established is that the VWAP is additive **with respect to the exit
structure, in the presence of the EMA**. The cell that would allow the check in the absence of the
EMA does not exist in the data, and the point returns in §4.4.

The ratio between how much the filter removes and how much it is worth is the interesting part. It
blocks between 1.4% and 1.7% of entries, 22 to 26 trades depending on the cell out of a total of
1,450 to 1,750, and it is worth between 2.8% and 3.4% of log return over eight years. It is not a
filter that improves the average quality of entries: it is a filter that intercepts a small and
systematically poor subset. It is a separate source of edge, not a remedy for a weakness elsewhere
in the strategy.

## 4.3 The exit structure: the cadence costs, the gate offsets it

The repository introduces two things together in moving from S2 to S4: the exit check goes from
30 to 5 minutes (cadence), and confirmation on four consecutive bars is required (persistence).
The two appear inseparable, but the cell that separates them already exists in the repository:
**S1 is S3 without the gate**, identical in everything else, with the same 30/5 intervals, the
same threshold formula, no EMA filter and no VWAP filter. The package therefore decomposes:

[Table T9]

**The cadence is costly under both thresholds.** Moving from a check every 30 minutes to one every
5 brings final wealth to 93.7% of that of S0 under `tight` and 95.3% under `loose`, that is,
$-0.06508$ and $-0.04853$ in log return, which are the values reported in the table, and brings
the order count from 3,594 to 4,900. This is the effect the paper calls the Momentum Paradox, and
it holds under both exit thresholds: it does not depend on the zero-distance threshold of `tight`, so it is not
an artifact of the threshold.

**The gate offsets exactly that cost.** Under `loose` the cadence removes 0.049 and the gate
returns 0.098: the net balance of the package is +0.049, so the gate recovers the cost and adds a
quantity of the same order. Under `tight` the recovery is much larger (+0.238) because the exit
threshold is a stop at zero or negative distance, and persistence is the only thing that keeps a
position open.

The conclusion to take away is not that the gate is worth zero, but **that it is not a standalone
source of edge**: it compensates for a cadence choice made two strategies earlier. The repository
presents S4 as an improvement on S2; on this reading, what S4 does is pay a cost (the 5-minute
cadence) and then buy its remedy (the gate).

## 4.4 The EMA substitutes for the gate, the VWAP does not

The same package measured in the presence of the other two entry filters:

[Table T10]

The second and third columns are identical to each other and different from the first. That is:
**adding the VWAP filter does not change the value of the exit package; adding the EMA filter
brings it to zero.** The EMA × package interaction is $-0.046$ under `tight` and $-0.053$ under
`loose`.

The paper does not leave this point implicit. In the section devoted to
S4 it states that the two mechanisms "are structurally independent: the EMA filter operates at the
entry decision gate, while the persistence counter operates on the exit signal after a position is
open", and that their combination is therefore "not merely additive but potentially synergistic".
From there it draws its formal hypothesis:

> **Hypothesis 1.** *If $Q_{\text{entry}}$ and $Q_{\text{exit}}$ are independently improvable, a
> mechanism that maximises both simultaneously dominates any mechanism that maximises only one.*

The two parts should be kept separate. The **conclusion** holds: S4 does dominate S2 and S3, it
beats both on return and on Sharpe, and it remains the best configuration in the repository. It is
the **premise** that the table above measures, and the data do not support it. If the two
mechanisms were independent the exit package would be worth the same with and without the EMA; if
they were synergistic it would be worth more. It is worth less in both variants, by an amount,
$-0.046$ and $-0.053$, that is two orders of magnitude above the interaction noise measured in
§4.2 on the same scale. They are not independent: they are partially redundant.

What does not hold, then, is not the paper's result but the reason given for it, and with it the
principle that the S0 to S4 ladder presupposes, namely that stacking mechanisms is the way
forward. The paper writes "*potentially* synergistic", and that caution should be acknowledged:
the statement was conditional. It has been tested here, and the measured interaction points the
other way.

The full design would have four columns, one for each combination of the two entry filters, and the
fourth, band + VWAP **without** EMA, does not exist in the data. A limit follows, and it is this:
the EMA turns out to be a substitute for the package **as measured in the absence of the
VWAP**, and the VWAP turns out to be additive **as measured in the presence of the EMA**. Each
conclusion holds at one level of the other filter only, and the two cross-checks, together with the
three-way interaction, would require four backtests that were not run.

EMA filter and persistence gate are **substitutes**: they do the same job, keeping out or closing
breakouts that do not continue, and having both does not pay twice. The VWAP condition is
different: it acts on something neither of the other two intercepts.

Hence the answer to the opening question. Under the specified and implemented threshold, the best
of the fourteen is S4′: it is S4 plus the only one of the three entry conditions that does not
overlap with the others, and therefore the only one that can add its full contribution. The lead is
not uniform across the two axes, however: under `loose` the exit package is worth zero and S2,
which is repository code, is on a par with S4′ (259.7 vs. 258.6 at 0 bps). The full comparison is
in §6.

The design also points to a cell that has not been tried. If the EMA filter and the gate are
substitutes, the combination gate + VWAP **without** EMA, that is, S3 with the VWAP filter added,
would avoid the overlap and keep the two levers independent. It has not been measured, and it
cannot be predicted either: estimating it would mean extrapolating the effect of the VWAP to a
level of the EMA at which it was never measured, that is, assuming exactly the interaction that is
missing. The statement that S4′ is the best should therefore be read for what it is: the best
among the configurations tried, not among those possible. The limit is stated in §8.

## 4.5 How much the zero-distance threshold weighs

A prediction of this analysis that the data did not bear out, reported as such.

Under `tight` the exit threshold sits at or above the level that authorized the entry, so the
condition should become true early in the life of most positions: the cadence would then stop
measuring the readiness to react to a reversal and measure instead how long a position the
threshold has already condemned is allowed to run, half an hour vs. five minutes. If the gap
between S0 and S1 were entirely due to this, then under `loose`, where the threshold is genuinely
distant and fires only on a real retracement, the gap should close.

It does not close: it goes from 0.06508 to 0.04853, so **the zero-distance threshold explains 25% of
it** and the rest is genuine. The 5-minute monitoring really is costly, and the paper's qualitative
conclusion survives the threshold, even against the alternative this analysis was testing.

The paper does not stop at recording the phenomenon, however: it gives it a mechanism. "*VWAP is a
slow-moving quantity that generates brief, transient violations of the composite exit condition
with no predictive value [...] Strategy 1 frequently closes valid positions on these transient
violations, the classic whipsaw outcome.*" On the paper's account, the cost comes from the VWAP
term.

This analysis cannot put that to the test, and the reason matters, because the check seems
within reach and is not. The exit condition is $P < \max(\cdot,\ \text{vwap})$, where the
first term is $UB$ under `tight` and $LB$ under `loose`; $LB$ is anchored below the open while the
VWAP is an average of the prices traded during the session, so for a long position the maximum
under `loose` is the VWAP in the great majority of cases. One would then be tempted to read the
smaller cost of S1 under `loose`, 0.04853 vs. 0.06508, as evidence against the stated
mechanism: the cost is smaller precisely where the VWAP is in charge.

**It is not such evidence.** The two variants differ not only in *which* term binds but also in
*how far* the threshold is from the entry level, and a more distant threshold is crossed less often
whatever the quantity that defines it. The smaller cost under `loose` is what one would predict
from the distance alone, without ever mentioning the VWAP: the two effects push in the same
direction and cannot be separated with these cells. Add that under `tight` the VWAP is not absent
(when, on a day of sustained rally, it rises above $UB$, it binds there too), and that the paper's
mechanism concerns the *rate* of transient violations while what is measured here is the *total*
cost.

What the data establish is therefore the fact and not the mechanism: the five-minute cadence has a
cost, and it has a cost even where the threshold is at a real distance. Attributing that cost to
the VWAP rather than to the denser sampling of a noisy series would require a cell the repository
does not contain, namely the same cadence with an exit condition free of the VWAP term. It is the
one statement of the paper about S1 that this report leaves standing without being able to either
confirm or rule out.

On the ordering between the two variants the picture reverses as we move from S0 to S2 to S3 and
S4. On S0, S1 and S2, `loose` returns more than `tight` already at 0 bps. On S3 and S4 it returns
less, but it has a lower $w_{sum}$ and therefore decays more slowly as costs rise:

[Table T11]

The crossover falls at **0.209 bps** on S3 and **0.357 bps** on S4. Whether that is inside the
range of realistic execution costs rests on an assumption this report does not measure: 0.25 to
0.5 bps per fill is used throughout as a working range for a liquid ETF traded at the market, not
a calibrated figure (§8). If costs fall in that range, `loose` wins everywhere, including where it
lost at zero cost, and the exit that appears only in the README's description is better than the
one the paper specifies.

[Figure F2]
