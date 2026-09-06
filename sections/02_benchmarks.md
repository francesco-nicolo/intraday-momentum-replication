# §2. What the strategy is measured against

A return of 271% over eight years means nothing until one says what it is measured against. The
paper does adopt a point of comparison, SPY bought and held at 166.4%, but without leverage, while
the strategy runs at an average leverage of 1.81: the comparison is between a leveraged portfolio
and one that is not. The Sharpe ratio attached to that benchmark, 0.47, also does not follow from
the numbers reported with it: 166.4% over eight years is 13.0% per year, which with the 16%
volatility stated on the same line gives 0.69. The quoted value appears to be the long-run
historical figure for equities rather than the one for this window, so the "nearly double" that
the paper states for the Sharpe of S0 corresponds to a factor of about 1.2 rather than 1.8. This
section builds two benchmarks in its place, each designed to isolate one thing, before going into
the construction itself. They are what determines which questions are worth asking afterwards.

Both benchmarks share the strategy's leverage rule, $\Lambda = \min(2,\ 0.02/\sigma_{14g})$, and
differ only in what they are meant to isolate. Leverage is matched because it is a free parameter
that anyone can raise: comparing a portfolio at leverage 1.81 with one at leverage 1 measures the
signal and the decision to take more risk together, and does not separate the two. And the whole
rule is matched, not just the average multiplier, because the rule has effects of its own on
compounded return. Further below we measure that volatility targeting costs 9% less than a fixed
leverage of the same mean, and that advantage belongs to the null hypothesis, not to the signal.

One thing about that rule changes how it needs to be understood. On this window and with the repository's
parameters, $\Lambda$ is **at the cap of 2 on 66.1% of days**, with an average of 1.8056: for two
thirds of the time there is no targeting at all, only fixed leverage at the maximum allowed. The
figure comes from the instrumented benchmark, which replicates the rule without a signal, but it
does not depend on the benchmark: the average weight per fill of the fourteen strategy
configurations, $\bar w \in [1.805;\ 1.828]$ in §3.7, is the same average leverage read off their
own orders. The cap is not incidental: the paper's own §2.3 mentions the insufficient buying power
errors that motivated it.

The first benchmark, `intraday`, is long SPY from 9:31 to 15:58 and closes every evening, with no
signal at all: it is the strategy stripped of nothing but its entry and exit logic. The second,
`hold24`, keeps the position overnight as well: it is leveraged buy-and-hold, that is, the
alternative an investor actually has available. Both are needed because they answer two different
questions and neither is sufficient on its own. `hold24` says whether it would have been better to
do something else, but it differs from the strategy on three axes at once (trading window,
direction selection, entry timing) and therefore cannot attribute anything to the signal.
`intraday` differs on one axis only, the presence of the signal, and is therefore the only one of
the two that isolates it.

[Table T2]

## There is a signal

The full-session benchmark, the one entering at 9:31 and reported in T2, loses 18.31%, with a
Sharpe of $-0.154$ and a drawdown of 40.5%. Matched to the strategy's entry time it loses far more,
but the point already holds in this form.

This is the most important result of the section: before this run,
none of the 54 backtests collected up to that point excluded the possibility that
the strategy's return came simply from being long intraday at leverage 1.8.

Instrument and leverage rule are identical; the trading window is not, and the difference was
measured rather than argued. The benchmark enters at 9:31, while the strategy cannot enter before
10:00: the thirty-minute cadence places the first usable evaluation there, as the paper itself
notes in a footnote. Repeating the run with entry at 10:00 and nothing else changed, the matched
benchmark closes at **$-36.08\%$**, not at $-18.31\%$. That it is the same experiment with one
variable moved is confirmed by the controls: `lambda_avg` $= 1.8056$ and `pct_capped` $= 66.1\%$
identical to the last digit, $w_{sum}$ within 0.02%, turnover within 0.01%, order count within
four out of four thousand.

The timing difference was therefore worth 17.8 points, and in the opposite direction to the one
expected on paper: the half-hour between 9:31 and 10:00 works in favor of whoever holds it, and
letting the benchmark keep it was **helping** the benchmark, not penalizing it. The correctly
matched comparison, same window as the strategy, same leverage, no signal, puts $+271.37\%$
vs. the $-36.08\%$ of the long null and the $-30.75\%$ of the short null (next paragraph):
**between 302 and 307 points depending on the direction in which the null hypothesis is held**,
vs. the 289.7 of the unmatched comparison. The number to cite is the narrower of the two,
302.1, because the strategy trades in both directions and the null should be taken in its most
generous version. This is also a first observation about the design of the repository, not only a
methodological qualification: the thirty-minute entry cadence excludes the opening half-hour by
construction, and in this sample that half-hour contributes positively while the rest of the
session does not, and it is worth 17.8 points to a passive leveraged position.

[Table T3]

A natural objection is that the benchmark is long-only while the strategy also goes short, so the
comparison is not matched on exposure. This too was measured rather than estimated: the same
benchmark, same 10:00 to 15:58 window, with only the sign of the position reversed, closes at
**$-30.75\%$**. It is the exact mirror of the long run, with $\beta = -0.724$ vs. $+0.724$ and
average win and average loss swapped digit for digit (0.99% / $-0.83\%$ vs. 0.83% /
$-0.99\%$), so the two rows measure the same exposure in the two directions.

**Blind exposure loses in both directions**, and the gap between the two is 5.3 points over eight
years. That, and only that, is the drift term of the window; the rest, more than thirty points and
common to both, is variance drag and commissions, which depend on $\Lambda^2$ and on the number of
fills and do not distinguish the sign of the position. The asymmetry exists and favors the short
side, not the long side as one would have expected, but it is an order of magnitude too small to
make either direction a sensible choice. There is no right side to be on without a signal: it is
the cost of *being there*, not the direction, that determines the outcome.

On the opposite side, the trade files published in the repository rule out the possibility that
the edge lives on the short side: on S4 the 878 long trades produce 137,578 dollars and the 816
short trades 137,500, that is, 50.0% and 50.0% of the P&L, and the split is close to even on S2
and S3 as well (49.6% and 48.8% long).
The P&L is in dollars not rescaled by the equity of the moment, but the two directions are
interleaved in time, so the imbalance favors neither. It is the same fact that can be read in
$\beta = -0.053$: if the strategy were predominantly long, its beta would be a positive fraction of
the intraday benchmark's 0.800.

## Why the intraday benchmark loses

Not because SPY falls: over the same window `hold24` makes $+350.5\%$. It loses because of two
mechanical effects, both independent of the direction of the market. The decomposition that
follows is that of the full-session run, entering at 9:31, the only one of the three instrumented
with the accumulators, and its items should be understood relative to that $-18.31\%$, not to the
matched $-36.08\%$: the mechanism is the same, the magnitudes are not.

Both effects are measured, not estimated. The obvious route, deriving them from the statistics
LEAN reports, would make them inherit LEAN's conventions, and Appendix A, §A.8 shows that at least
one of those conventions is not the one a reader would assume. They are therefore collected inside
the backtest: a single run at 0 bps, with four scalar accumulators updated at every session close
and emitted via `set_runtime_statistic`, the only channel on the Free plan that does not consume
the log quota. The number of samples comes back as 2,012, exactly the independent count of NYSE
sessions in the window, a free check that the sampling is one point per session with no gaps.

**Commissions: 9,746.60 dollars** on an account that starts at 100,000 and closes at 81,691, with
3,997 orders over eight years. The right denominator is not the initial capital. The Interactive
Brokers fee model is per share, and the shares in a trade are worth $\Lambda E/P$: the commission
per trade is $c\,\Lambda E/P$, and relative to equity it is $c\,\Lambda/P$, a quantity that does
not depend on the size of the account. Total commissions are then proportional to the **integral
of equity over time**, not to the starting capital, and dividing by 100,000 would overstate the
rate, because the account shrank over the whole window. With an average equity of 87,027 over the
2,012 sessions the integral is $\int_0^8 E_t\,dt = 696{,}215$, and the result is

$$\phi = \frac{\text{commissions}}{\text{years}\cdot\bar E} = \frac{9{,}746.59}{8 \cdot 87{,}027} = 1.400\%\ \text{per year}$$

**Leverage drag.** Holding $\Lambda$ times the exposure does not multiply the compounded return by
$\Lambda$. Over a single session the log return of the leveraged position is
$\ln(1+\Lambda r) \approx \Lambda r - \tfrac12\Lambda^2r^2$, while $\Lambda$ times the log return
of the underlying is $\Lambda r - \tfrac12\Lambda r^2$: the difference, what leverage costs
**beyond** simple rescaling, is $\tfrac12\Lambda(\Lambda-1)r^2$. Since the portfolio return is
$r_{port} = \Lambda r$, the same quantity can be written with the portfolio series alone:

$$\tfrac12\,\Lambda_t(\Lambda_t-1)\,r_t^2 \;=\; \tfrac12\,\frac{\Lambda_t-1}{\Lambda_t}\,r_{port,t}^2$$

and this is the form accumulated session by session inside the run. The sum built this way never
passes through `ann_std`, so it does not inherit LEAN's annualization convention (Appendix A,
§A.8). Divided by the number of years, it is 0.969% per year.

**The arithmetic.** The two drags are logarithmic and add to each other, so they must be compared
with the log CAR, $-\ln(1+R)/8 = 2.528\%$, and not with the simple CAR; mixing the two scales is
worth a few tenths of a point:

$$1.400\% + 0.969\% = 2.369\% \qquad \text{vs.} \qquad 2.528\%$$

[Table T4]

The two mechanical effects therefore explain 94% of the loss, and the residual is $-0.159\%$ per
year on the leveraged position, that is, $-0.088\%$ per year on the underlying.

> The second figure divides the first by $\bar\Lambda$, which treats leverage as a constant. It
> is not one: $\Lambda_t$ is set from the trailing volatility of the same series whose returns it
> multiplies, so the exact conversion carries a covariance term that the division drops,
> $E[\Lambda_t x_t]/\bar\Lambda = E[x_t] + \operatorname{Cov}(\Lambda_t, x_t)/\bar\Lambda$. That
> the two are not independent is measured two paragraphs below, on the second moment: cutting
> $\Lambda_t$ exactly when $r_t^2$ is large is what makes the drag 9% lower than at a constant
> leverage of the same mean. The $-0.088\%$ is therefore the order of magnitude of the unleveraged
> residual, not an identity, and nothing in the section rests on its second digit.

That residual is the **compounded** return of a passive, unleveraged intraday position: it says
that anyone long from 9:31 to 15:58 for eight years, without leverage and without costs, would
have ended flat to within a tenth of a point per year. It does not say that the arithmetic daily
mean is zero; that mean is positive, and it is consumed by its own variance drag until the
compounded return reaches zero. The distinction matters because the session is not homogeneous:
"SPY does not drift intraday" does not hold segment by segment; "a passive position over the
whole session ends flat" is what was measured. The return SPY actually delivered
over the window, 166.4% (paper, §3.2), that is, 13.0% per year, therefore lives almost entirely
overnight, the segment this comparison does not measure; that the equity premium of US stocks
accrues overnight rather than during trading hours is documented well beyond this window (Cooper,
Cliff and Gulen, 2008; Lou, Polk and Skouras, 2019).

One last observation on the drag, which is a fact about the sizing rule and not about the
benchmark. At constant leverage, with $\bar\Lambda = 1.8056$, the formula would give 1.07% per
year; measured, it gives 0.969%, 9% less. The difference is the leverage rule at work: $\Lambda_t$
is cut precisely on the days when $r_t^2$ is large, and the drag weights the squares. **Volatility
targeting costs less than a fixed leverage of the same mean**, and the margin is measurable.

From this follows the property that makes the strategy interesting. A strategy that goes flat
every evening does not touch the equity premium by construction, and indeed it has
$\beta = -0.053$. It does not participate in the market: it extracts return from a window whose
compounded return is zero. The zero beta is not the result of an optimization; it is a consequence
of the schedule. The schedule has five exceptions in eight years, all on half-day sessions where
the 15:58 liquidation branch is never reached (§7, item 3); §8 bounds what they are worth.

## The opportunity cost

The uncomfortable question remains. `hold24` makes $+350.5\%$ vs. $+271.4\%$, and it is almost
immune to costs: its break-even is at 218 bps of slippage vs. the strategy's 2.2, because
`set_holdings` rebalances only the delta and the notional traded is therefore two orders of
magnitude smaller. Under any cost assumption the gap widens rather than closes.

One correction, however, works in the opposite direction. LEAN does not charge interest on the
borrowed balance, and with $\Lambda_{avg} = 1.8056$ `hold24` stays borrowed for 0.8056 units of
equity every night for eight years. The correction is subtractive on the CAR, because interest
accrues on the balance at the start of the period and not on the realized return:
$E_{t+1} = E_t\,(1 + g - (\Lambda-1)r)$.

[Table T5]

At the declared convention, $r = 3.5\%$ (average T-bill rate over the window plus a retail-account
spread), `hold24` makes 272.9% vs. 271.4%. The rate at which the two break even is 3.58%, that
is, inside the range the sensitivity table covers.

The asymmetry deserves stating, otherwise the correction looks chosen for convenience: it hits
`hold24` in full and barely touches the strategy, because brokers charge interest on the overnight
balance and the strategy is flat every evening.

But the conclusion that holds is not that the strategy wins. It is that the return gap between the
two is of the same order as the uncertainty on the one cost item the backtest does not charge, and
therefore does not support an argument in either direction.

## What remains

The comparison that holds is the other one, and it does not depend on $r$. Same instrument, same
window, same leverage rule: drawdown 9.0% vs. 40.2%, $\beta = -0.053$ vs. 1.323,
$\alpha = +0.101$ vs. $+0.043$, PSR 49.5% vs. 6.9%. Recovery from the maximum drawdown
takes 343 days vs. 714. The two PSRs are measured in the same session and on the same version
of the platform, so they are comparable with each other; §7 explains why they should not be
compared with the published ones.

The defensible formulation is therefore this: it is not a better way of earning from the market,
it is a source of return almost orthogonal to the market at a quarter of the drawdown. "271
vs. 350" is the less informative comparison, and the columns that show it are above.

The rest of the report answers a different question, one that only makes sense after this one:
given that this is a zero-beta diversifier, is it well built?
