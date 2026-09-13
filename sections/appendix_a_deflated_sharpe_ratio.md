# Deflated Sharpe Ratio on S4′ tight

*Methodological appendix to the independent analysis of `blackswan-quants/intraday-momentum`*

---

## A.1 The problem

One result of this report is that the best configuration among those examined, S4′, that is, S4
with the VWAP entry filter added, reaches a Sharpe of 1.075 vs. 1.036 for S4 and 0.835 for the S0
baseline.

This result was obtained **by selecting the maximum over fourteen configurations**. Selection
introduces a bias that has nothing to do with the quality of the strategy: the maximum of $N$
noisy estimates is systematically above the mean of the population they come from, even when that
population has a mean of exactly zero.

The most direct analogy: fourteen perfectly fair coins, a hundred tosses each, and one keeps the
coin with the most heads. That coin will show a frequency of heads above 50%. Not because it is
biased, but because it is the maximum of fourteen draws.

The right question is therefore not *"is 1.075 a high Sharpe?"* but:

> **How high would the best of the fourteen have been if none of the fourteen had any edge?**

This appendix computes that threshold and compares the observed result against it.

---

## A.2 Why the PSR reported by QuantConnect is not enough

For every backtest QuantConnect reports the **Probabilistic Sharpe Ratio** (Bailey and López de
Prado, 2012), which addresses a different and equally real problem: the sample Sharpe is an
estimate, and its uncertainty depends on the length of the series, on skewness and on the thickness
of the tails. The PSR measures how far the sample Sharpe stands above a fixed threshold, in units
of its own sampling error:

$$\text{PSR}(SR^*) = \Phi\!\left[\frac{(\widehat{SR} - SR^*)\sqrt{n-1}}{\sqrt{1 - \hat\gamma_3\widehat{SR} + \frac{\hat\gamma_4 - 1}{4}\widehat{SR}^{\,2}}}\right]$$

where $\hat\gamma_3$ and $\hat\gamma_4$ are the skewness and the (non-excess) kurtosis of the
returns, $n$ the number of observations and $\Phi$ the standard normal CDF.

One point on how this quantity is to be read, because it propagates to everything below. The
expression standardizes the distance between an estimate and a threshold and passes it through
$\Phi$, so the number it returns is at once the complement of a one-sided p-value and, reading
$\widehat{SR}$ as a pivotal statistic for a location parameter, the confidence that $SR$ exceeds
$SR^*$. The two readings agree for as long as $SR^*$ is a constant fixed in advance, which is the
case for the PSR. They stop agreeing once the threshold is itself estimated from the same data,
which is the case for the deflated version used here; §A.10 states the consequence. The figure of
§A.6.2 is therefore reported as a test statistic with a nominal level, not as a probability
attached to the parameter.

The limitation is that the PSR looks at **one** strategy at a time and does not know how many were
tried. Applying it to all fourteen and reporting the best means reporting the maximum of fourteen
PSRs, that is, falling back into the original problem.

The **Deflated Sharpe Ratio** (Bailey and López de Prado, 2014) is the same formula with the
threshold changed: instead of $SR^* = 0$ one uses $SR_0$, the maximum Sharpe expected under the
null hypothesis $H_0$, which from here on always denotes the following: **all** the configurations
tried have exactly zero edge.

$$\boxed{\;\text{DSR} = \text{PSR}(SR_0)\;}$$

### A.2.1 A second reason, independent of the first: the platform PSR does not reproduce

There is a second reason, distinct from multiple selection, not to build the DSR on the PSR that
QuantConnect reports in its interface: that number has not remained stable over time on the same
code.

The repository preserves `stats/strat{0..4}_8y.json`, the authors' backtest output. Re-running
the same code without modifications, over the same period, five months later — their runs are of
March 2026, these of August and September 2026, and §7 records the provenance of both:

| | PSR in the authors' file | PSR re-run today | difference |
|---|---|---|---|
| S0 | 61.589% | 21.510% | 40.1 points |
| S1 | 67.736% | 21.982% | 45.8 points |
| S2 | 75.319% | 33.461% | 41.9 points |
| S3 | 81.164% | 41.219% | 39.9 points |
| S4 | **83.439%** | **44.342%** | 39.1 points |

It is the only statistic that moves. Compared with the same file, which reports 3 to 4
significant figures rather than the rounded values of the README, orders (exact, e.g. 3,388 on
S4), Sharpe (within 0.001), Sortino, drawdown, win rate, $\alpha$, $\beta$, annualized standard
deviation and Portfolio Turnover all agree. The strategy sources are unchanged since commit
`b960d36` and the order counts match exactly on all five rows, so the inputs to the computation are
the same on the two dates up to the fill-price differences documented in §1, which move the returns
by at most 0.29pp and cannot account for forty points of PSR. What is not fixed between the two
dates is the engine build, since the projects follow QuantConnect's master branch. The reading this
supports is that the figure moved on the platform's side rather than in the code; which build, and
what in it, is not recoverable from the result files, and §7 dates the gap without explaining it.

This is the practical reason, in addition to the statistical one of §A.2, why the DSR of this
appendix does not start from the PSR reported in the interface of any backtest, neither of our
own fourteen nor of the March runs preserved in the repository. It starts from the five scalar
accumulators of §A.5, computed locally from the daily returns of the same run: a quantity that does
not depend on which version of QuantConnect's pipeline produced it. The full detail of this
comparison is in §7 (T1).

---

## A.3 The null threshold $SR_0$

Under $H_0$ the $N$ sample Sharpes are draws from a distribution with mean zero and standard
deviation $\sigma$. The expected value of their maximum is a problem in extreme value theory: for
Gaussian draws the maximum converges to a Gumbel distribution, and the closed-form approximation
is

$$SR_0 = \sigma\left[(1-\gamma)\,\Phi^{-1}\!\left(1 - \frac{1}{N}\right) + \gamma\,\Phi^{-1}\!\left(1 - \frac{1}{N e}\right)\right]$$

with $\gamma \approx 0.5772$ the Euler-Mascheroni constant. The two terms are the quantiles
corresponding to the mode and the mean of the limiting Gumbel, combined with weight $\gamma$. For
$N = 14$ the quantity in brackets is 1.7384.

The relevant property is that $\Phi^{-1}$ grows **logarithmically** in $N$: the threshold rises
very slowly as the number of trials increases.

---

## A.4 Parameters: choice and justification

### A.4.1 Number of trials, $N = 14$

The fourteen configurations for which a 0 bps backtest exists: S0, S1, S2, S3, S4, S2′, S4′, each
in the two exit variants `tight` and `loose`.

Twelve of these belong to the initial design. The two prime cells (S2′, S4′) were **constructed
along the way**, after observing the results of S2 and S4, to separate two axes that were
confounded in the original comparison, entry filter and exit structure. This is data-driven
research, not a design fixed in advance, and it is declared as such: the motivation was one of
experimental design, not of expected result, but the cells were added after looking at the
numbers.

No configuration was explored and discarded: the fourteen are the entire search space and all are
reported. The variants at $b > 0$ do not count as separate trials, because they are not
independent searches but deterministic transformations of the 0 bps rows through the cost
reconstruction.

$N = 14$ is also **conservative** with respect to the independence assumption: the trials share
instrument, window, leverage rule and most of the logic, so the number of effectively independent
trials is below 14, which would lower $SR_0$.

### A.4.2 Null dispersion, $\sigma$: two specifications

**Main specification (conservative).** Under $H_0$ the relevant dispersion is the standard error
of the sample Sharpe of one independent trial:

$$\text{SE}(\widehat{SR}_d) \approx \sqrt{\frac{1 + \widehat{SR}_d^{\,2}/2}{n}} = 0.02234$$

already in daily units. This is the specification on which the conclusions rest.

**Bailey and López de Prado specification.** The authors prescribe the **cross-sectional**
standard deviation of the $N$ sample Sharpes; over the fourteen values at 0 bps it is
$\sigma_{\text{cross}} = 0.06917$ in QC Sharpe units.

Here this specification is **not informative**, for a reason that matters: the fourteen
trials are minor variants of one another, so they produce nearly identical Sharpes.
$\sigma_{\text{cross}}$ measures the variability *between variants*, not the sampling variability
that an independent trial would have under the null hypothesis, and it is in fact smaller than the
theoretical standard error by a **factor of 4.25**: $0.06917$ vs.
$0.02234 \times 13.173 = 0.29430$, both in QC units. The resulting figure is so high as to be
insensitive to any $N$, which is in itself the symptom that the threshold is too low. It is
reported in §A.7 for completeness, not as a result.

Two details, both in the conservative direction and therefore worth stating:

- The SE used is the Gaussian one. The version corrected for the actual moments is
  $\sqrt{(1 - \hat\gamma_3\widehat{SR}_d + \frac{\hat\gamma_4-1}{4}\widehat{SR}_d^{\,2})/n} = 0.02055$,
  that is, smaller. Using 0.02234 raises the threshold.
- $\sigma_{\text{cross}}$ is computed over the fourteen Sharpes **including the maximum**, which
  slightly inflates the dispersion and therefore the threshold.

### A.4.3 Risk-free rate, $r_f = 2\%$

A convention already declared elsewhere in the report, applied as $r_f/252$ per trading day. It is
not calibrated on anything: it is fixed a priori, and it is ours, not the platform's, whose own
rate over this window is about 2.7% (§A.8). Its effect on the result is bounded either way: the rate
enters only through the excess return in $\widehat{SR}_d$, and the DSR of §A.6.2 is 99.6% at
$r_f = 1\%$, 99.0% at 2%, 98.4% at about 2.7%, and 98.0% at 3%.

Not to be confused with the margin financing rate discussed elsewhere (3.5%): that is the cost of
borrowed capital, this is the term subtracted in the numerator of the Sharpe ratio. They are two
different quantities that happen to live in the same section of a backtest.

### A.4.4 Number of observations, $n = 2011$

Daily equity returns, sampled on **trading days** between 2017-05-10 and 2025-05-10. There are
2,012 trading days in the window, and the first observation produces no return.

LEAN's series instead contains 911 observations with identically zero return (weekends and
holidays): they are not observations, they are padding, and the series on trading days is the
statistically correct one.

**The result does not depend on the choice, however**, and it is worth showing this explicitly,
since elsewhere in the report LEAN's sampling convention is documented as a source of confusion.
Under dilution by a factor $\kappa$, here $\kappa = 2922/2012 = 1.45229$, all the quantities that
enter the DSR transform in a coordinated way:

$$\widehat{SR} \to \frac{\widehat{SR}}{\sqrt{\kappa}}, \qquad \sqrt{n-1} \to \sqrt{\kappa}\,\sqrt{n-1}, \qquad \hat\gamma_3 \to \hat\gamma_3\sqrt{\kappa}, \qquad \hat\gamma_4 \to \hat\gamma_4\,\kappa$$

The numerator $\widehat{SR}\sqrt{n-1}$ is invariant because it is, in essence, total return over
total risk. The denominator is invariant up to one term: $\hat\gamma_3\widehat{SR}$ and
$\hat\gamma_4\widehat{SR}^{\,2}$ are both invariant under these transformations, but the constant
$-1$ inside $(\hat\gamma_4-1)/4$ is the single piece that does not rescale with the moments, and it
is what produces the 0.92150 against 0.92182 of the table below. Because it multiplies
$\widehat{SR}^{\,2}$, its effect on the DSR is of order $10^{-5}$. And the threshold $SR_0$ rescales by $1/\sqrt{\kappa}$
as well, because the SE goes as $1/\sqrt{n}$.

| | $\widehat{SR}$ | $n$ | denominator | $z$ | DSR |
|---|---|---|---|---|---|
| trading days | 0.08694 | 2011 | 0.92150 | 2.3402 | **99.04%** |
| calendar days | 0.07214 | 2922 | 0.92182 | 2.3401 | **99.04%** |

There is therefore no knob to turn: the conclusion is the same whichever convention is adopted.
The invariance holds to the precision reported rather than exactly. Besides the constant $-1$
above, the dilution of the moments is itself an approximation, because the $m^2$ term in
$m_2 = \sum_i r_i^2/n - m^2$ scales with $\kappa^2$ and not with $\kappa$, and the same applies to
the centring terms of the third and fourth moments. Redoing the whole calculation on the calendar
series from the raw power sums, with none of these approximations, gives 99.0% again.

**Corollary.** What makes the DSR of this appendix invariant is that its threshold $SR_0$ is built
from the standard error and therefore rescales with the sampling, together with everything else.
A statistic whose threshold is a fixed number instead does not survive the change: LEAN's reported
Sharpe subtracts an annual risk-free rate that does not dilate with $\kappa$, and its PSR compares
against the constant $1/\sqrt{252}$ (§A.8). Both are convention-dependent for the same reason, and
that is why this appendix uses neither.

Sampling is scheduled one minute before the close, hence **after** the forced liquidation at
15:58: returns are measured with the portfolio already flat. The exception is the seventeen
half-day sessions of §7, where the liquidation branch never fires and the sample is taken at 12:59
with the position still open: seventeen observations out of 2,011.

### A.4.5 Units

$\widehat{SR}_d$ is computed by us per observation on trading days; $\sigma_{\text{cross}}$
instead derives from QuantConnect's Sharpes, annualized with a different convention. The two
scales are not linked by a simple factor, because the risk-free term does not rescale with the
rest: §A.8 gives the relation in full. To convert a **dispersion**, however, the additive offset
cancels and the correct factor is the multiplicative part alone. That part is
$\sqrt{252}/\sqrt{\kappa} = \sqrt{252/\kappa} = 13.173$, namely LEAN's annualizer $\sqrt{252}$
applied to a standard deviation already reduced by $\sqrt{\kappa}$ through the calendar-day
sampling. In the main specification the question does not arise at all: the SE
is computed directly in daily units on the series we measured, so the result that supports the
conclusions does not depend on LEAN's annualization convention.

---

## A.5 Instrumentation

The QuantConnect Free plan offers neither API access nor the Object Store, so the daily return
series cannot be exported programmatically. It is not needed: skewness and kurtosis are derived
from five scalar accumulators.

```python
def record_equity_moment(self):
    if self.is_warming_up:
        return
    v = self.portfolio.total_portfolio_value
    if v <= 0:
        return
    if self.prev_equity is not None and self.prev_equity > 0:
        r = v / self.prev_equity - 1.0
        self.ret_n += 1
        self.ret_s1 += r
        self.ret_s2 += r * r
        self.ret_s3 += r * r * r
        self.ret_s4 += r * r * r * r
    self.prev_equity = v
```

The five values are emitted via `set_runtime_statistic`, a channel that does not consume the
10 kb log quota of the Free plan. Exponential formatting with 12 digits: the sums of fourth powers
are of order $10^{-5}$ and fixed-point formatting would zero them out.

From these, the sample moments:

$$m_1 = \frac{S_1}{n}, \qquad m_2 = \frac{S_2}{n} - m_1^2, \qquad
\hat\gamma_3 = \frac{S_3/n - 3m_1 S_2/n + 2m_1^3}{m_2^{3/2}}$$

$$\hat\gamma_4 = \frac{S_4/n - 4m_1 S_3/n + 6m_1^2 S_2/n - 3m_1^4}{m_2^{2}}$$

Cost: **one backtest**, on S4′ tight at 0 bps.

---

## A.6 Results

### A.6.1 Measured quantities

| quantity | value |
|---|---|
| $n$ | 2011 |
| daily mean $m$ | $6.7596\cdot 10^{-4}$ |
| daily standard deviation $s$ | $6.8622\cdot 10^{-3}$ |
| $\hat\gamma_3$ (skewness) | **+2.011** |
| $\hat\gamma_4$ (kurtosis, non-excess) | **13.703** |

One quantity is derived rather than measured, and a choice enters with it that does not enter
above, the risk-free rate of §A.4.3: the sample Sharpe per observation,
$\widehat{SR}_d = (m - r_f/252)/s = 0.08694$.

### A.6.2 Main result

With $\text{SE} = 0.02234$ and $N = 14$:

$$SR_{0,d} = 0.02234 \times 1.7384 = 0.03884$$

$$z = \frac{(0.08694 - 0.03884)\sqrt{2010}}{\sqrt{1 - 2.011 \cdot 0.08694 + \frac{13.703 - 1}{4}\cdot 0.08694^2}} = \frac{2.1570}{0.9215} = 2.341$$

$$\boxed{\text{DSR} = \Phi(2.341) = \mathbf{99.04\%}}$$

With the SE corrected for the actual moments (0.02055) the value rises to **99.36%**.

**How the figure should be stated.** It is a confidence level in the sense of §A.2, equivalently
the complement of a one-sided p-value, and not a posterior probability, so the defensible wording
is: *under the null hypothesis that all fourteen
configurations have a true Sharpe of zero, the observed maximum is incompatible with selection
noise at the 1% level* ($z = 2.34$, $p = 0.0096$, one-sided). This says the same thing as
"DSR = 99.04%" and claims nothing the construction does not support. The level is nominal rather
than exact, for the reason given in §A.10.

### A.6.3 Consistency check of the instrumentation

The results of this appendix rest entirely on the five accumulators, and so far nothing verifies
their correctness. The check that follows is free and uses only numbers already available; its
scope, what it establishes and what it does not, is delimited below.

The compounded return over the whole period is $\prod_i(1+r_i)$, and its logarithm expands into
the power sums already collected:

$$\sum_i \ln(1+r_i) = S_1 - \frac{S_2}{2} + \frac{S_3}{3} - \frac{S_4}{4} + O(S_5)$$

| order | value | relative gap |
|---|---|---|
| 1 | 1.359364699 | $3.6\cdot 10^{-2}$ |
| 2 | 1.311556089 | $3.7\cdot 10^{-4}$ |
| 3 | 1.312055857 | $1.25\cdot 10^{-5}$ |
| **4** | **1.312039632** | $\mathbf{1.4\cdot 10^{-7}}$ |

vs. $\ln(1 + 2.71374) = 1.312039455$, derived from the net profit reported by QuantConnect.

**What this verifies.** Two things. First, the **endpoints**: the first sample starts from
$V_0 = 100{,}000$ and the last coincides with the final equity that produces the reported
+271.374%. Second, and more important, the **mutual consistency of the four accumulators**: if
$S_3$ or $S_4$ contained an error, the corresponding term would not close the residual of the
previous one. That the agreement improves by two orders of magnitude in going from the third to
the fourth term (a factor above ninety) instead of leveling off rules out systematic errors in the
higher moments, which are exactly the ones on which the DSR denominator rests.

**What this does not verify.** The check can say nothing about *which* instants were sampled,
because the product telescopes. Every $r_i$ is built on `prev_equity`, that is, on the last
recorded value and not on the previous day's, so

$$\prod_i (1+r_i) = \frac{V_{\text{last}}}{V_{\text{first}}}$$

for **any** subset of instants. If a day were skipped, `prev_equity` would not update and the next
return would cover two sessions: the product would remain identical, $n$ would drop to 2010 and
the check would pass anyway. The same holds if sampling occurred at 15:00 rather than at 15:59.

**The check on $n$ has to be done separately**, and it is needed, because $\sqrt{n-1}$ enters the
$z$ of §A.6.2 directly. An independent count of NYSE sessions between 2017-05-10 and 2025-05-10
gives **2,012** (the last is May 9, since the 10th falls on a Saturday), hence 2,011 returns: this
coincides with `ret_n`.

**One further gap, closed elsewhere.** Everything above compares the accumulators with each other
and with the endpoints; all of it is internal to the five numbers, and none of it confronts them
with a quantity computed by anyone else. §A.8 does exactly that: it reproduces LEAN's annualized
volatility, its Sharpe and its PSR from $s$, $\hat\gamma_3$ and $\hat\gamma_4$, against figures the
platform computed from its own series. Had the sampling taken different instants, those moments
would not be ours diluted by $\kappa$ and none of the three would land. The constraint is coarse,
the printed volatility carries two significant figures and the half point on the PSR is already
absorbed by the band on the platform's risk-free rate, but it is the only external check on the
moments in this appendix, and it bears on precisely the point the telescoping argument leaves
open.

---

## A.7 Sensitivity to the number of trials

| $N$ | Gumbel bracket | $SR_{0,d}$ | DSR |
|---|---|---|---|
| 14 | 1.7384 | 0.03884 | **99.04%** |
| 50 | 2.2763 | 0.05086 | 96.04% |
| **65** | 2.3751 | 0.05306 | **95.03%** |
| 100 | 2.5306 | 0.05654 | 93.04% |
| 500 | 3.0525 | 0.06820 | 81.91% |
| 1,000 | 3.2551 | 0.07272 | 75.54% |

The exact 95% threshold falls at $N = 65.5$. The conclusion therefore stays above 95% up to
**$N \approx 65$ trials**, vs. the actual 14: a margin of about a factor of five on the number
of configurations it would have been legitimate to explore. With the SE corrected for the moments
the threshold moves to $N \approx 117$.

It is a solid margin but not an unlimited one, and this is the correct formulation of the result.

**For comparison, the Bailey and López de Prado specification.** Bringing
$\sigma_{\text{cross}} = 0.06917$ into daily units, that is, dividing it by 13.173 (§A.4.5), the
DSR is 99.99% at $N = 14$, 99.94% at $N = 10^4$ and 99.63% at $N = 10^9$: no number of trials
brings the conclusion down. This total insensitivity is not robustness; it is the diagnostic
symptom that the cross-sectional dispersion is too small to be a sensible null dispersion when
the trials are as correlated as these. The number is reported for completeness, not offered as a
result.

---

## A.8 How LEAN annualizes, and what its printed figures mean

Three statistics of the same run are quoted from QuantConnect elsewhere in this report, the
annualized volatility, the Sharpe ratio and the PSR, and all three depend on a convention of the
platform rather than on the strategy. The convention is visible in the source, and the moments
measured above are enough to check that it has been read correctly.

LEAN samples the performance series once per calendar night, not once per session (`BaseResultsHandler.Sample`, whose value is $(E_t - E_{t-1})/E_{t-1}$, so a night with no trading contributes an exact zero), and annualizes that series with 252 (`PortfolioStatistics`: `AnnualVariance(listPerformance, tradingDaysPerYear)`).

The series it works on is therefore ours **diluted**: 2,011 real returns spread over 2,922 observations, the other 911 being zero, so $m_{\text{cal}} = m/\kappa$ and $s_{\text{cal}} = s/\sqrt{\kappa}$ with $\kappa = 2922/2012 = 1.45229$. The risk-free rate is subtracted as an annual figure and does not rescale with $\kappa$, so the reported Sharpe is

$$SR_{QC} = \frac{(1 + m/\kappa)^{252} - 1 - r_f}{\sqrt{252/\kappa}\;s}$$

The numerator is compounded and not linear, because `Statistics.AnnualPerformance` raises the mean
plus one to the power `tradingDaysPerYear`; see below on how that was established.

Written with a linear numerator the same expression becomes
$\sqrt{252/\kappa}\,(m - \kappa\,r_f/252)/s$, which is algebraically transparent and shows where
each $\kappa$ acts: the first is LEAN's annualizer $\sqrt{252}$ applied to a series that has
$252\kappa = 366$ observations per year, the second is a risk-free rate charged 366 times a year at
a daily rate calibrated on 252, that is, an effective $\kappa r_f = 3.92\%$. It is not, however,
what LEAN computes, and two warnings are in order for anyone checking the arithmetic. At
$r_f = 2.70\%$ the linear form returns 0.999 against the 1.075 printed. And at the $r_f = 2\%$ of
this report it returns 1.076, which lands on the printed value through the cancellation of two
errors and must not be taken as a reproduction. The compounded form at 2.70% gives 1.078, and that
is the reproduction.

The check is that this reproduces what QuantConnect prints, from our moments and nothing else:

| quantity | from our moments | reported by QC |
|---|---|---|
| annualized volatility, $\sqrt{252}\,s/\sqrt{\kappa}$ | 0.0904 | 0.09 |
| Sharpe, LEAN's convention, $r_f = 2.70\%$ | 1.078 | 1.075 |
| Probabilistic Sharpe Ratio | 49.8% | 49.490% |
| *(for contrast)* Sharpe on trading days, $\widehat{SR}_d\sqrt{252}$, linear | 1.38 | — |

The first line has no free parameter: $\kappa$ comes from the calendar and $s$ from the
measurement. The second and third add only the platform's risk-free rate, and the third runs LEAN's
own routine (`Statistics.ProbabilisticSharpeRatio`) on the same diluted moments, landing within
half a point of the printed value; together they settle the reading of the convention. The fourth
line is not a reproduction but a comparison: the same run annualized on the days it actually
traded, which is what the printed figure understates, here and for every QC Sharpe in this report.
It uses the linear annualization, so it is not on the convention of the lines above; under LEAN's
compounded form the same series on trading days would give 1.52. Either number makes the point.
The QC figures are quoted as printed throughout, for comparability with the paper.

Two details are needed to reproduce the PSR, and they matter for §7. LEAN sets its
`benchmarkSharpeRatio` to $1/\sqrt{252}$, that is, it measures the PSR against a **Sharpe of 1**
rather than against zero, so the number it prints is not the probability that the true Sharpe is
positive. And the risk-free rate it uses is not a convention but its interest rate model: the
Sharpe inverted on five independent runs of this report puts it between **2.69% and 2.72%**, the
short rate over this window. That inversion also settles how the numerator is annualized.
`Statistics.AnnualPerformance` raises the mean plus one to the power `tradingDaysPerYear`, which
compounds it, while the summary comment above the method describes the linear form instead; under
the compounding form the five runs agree on the rate, under the linear one they spread over more
than a point, so the runs and the source say the same thing.

This says nothing about the strategy, and it changes no result of this report: it fixes how the
platform statistics quoted elsewhere should be interpreted. The risk-free rate the report adopts for its
own Deflated Sharpe Ratio, $r_f = 2\%$, remains a convention declared in advance (§A.4.3), not a
quantity taken from the platform.

---

## A.9 Comment

### A.9.1 Positive skewness works in favor, the tails barely matter

The denominator is 0.9215, and it decomposes as follows:

$$1 \underbrace{- \hat\gamma_3\widehat{SR}_d}_{-0.1748} + \underbrace{\frac{\hat\gamma_4-1}{4}\widehat{SR}_d^{\,2}}_{+0.0240} = 0.8492 \quad\Rightarrow\quad \sqrt{0.8492} = 0.9215$$

Without skewness the denominator would be 1.012, that is, the DSR would be lower. The
contribution of skewness is **seven times** that of kurtosis, even though the kurtosis is 13.7
(excess: 10.7): the kurtosis term enters squared in $\widehat{SR}_d$, which is 0.087, and
vanishes numerically. The ratio is a consequence of the daily frequency and not a general
hierarchy: skewness multiplies $\widehat{SR}_d$ and kurtosis multiplies $\widehat{SR}_d^{\,2}$, so
on annual Sharpes, where $\widehat{SR} \approx 1$, the order reverses and the kurtosis term is the
one that dominates.

The common intuition is that fat tails penalize the Sharpe ratio as an indicator; here the
penalty exists but is second order, while positive skewness dominates.

### A.9.2 The skewness is consistent with the rest of the picture

$\hat\gamma_3 = +2.01$ means many small losses and few large wins: the canonical profile of a
momentum strategy. It is consistent with the other statistics reported for S4′, a win rate of 40%
and a high profit/loss ratio, which are independent measures and tell the same story. This is
also a **desirable** property that the Sharpe ratio alone does not show: at
equal Sharpe, a distribution with positive skewness is preferable.

---

## A.10 Limitations

**The DSR corrects for selection within the family, not for the choice of the family.** The
fourteen configurations are minor variants of the same strategy, on the same instrument, over the
same window. The test answers: *given this family, is the best distinguishable from the family's
noise?* It does not answer: *does intraday momentum on SPY have edge?* That selection took place
upstream, at the moment the family was published because it worked, and no correction applied
downstream can recover it.

**The threshold is estimated, not known.** In a Wald test the null value $\theta_0$ is a constant
fixed in advance. Here $SR_0 = \hat\sigma \times 1.7384$ depends on $\hat\sigma$, which in turn
depends, through the plug-in of §A.4.2, on the same $\widehat{SR}_d$ that stands in the numerator.
Numerator and threshold are therefore correlated, and the variance of $\widehat{SR}_d - SR_0$ is not
the $\text{SE}^2$ that the denominator uses: a covariance term is missing. The direction is not
neutral, if $\hat\sigma$ is overstated the test is conservative and if understated
anti-conservative, and the level is to be read as nominal. The PSR against zero does not have this
problem, because there $SR^* = 0$ is a true constant; it is specific to the deflated version.

**Independence of observations.** The factor $\sqrt{n-1}$ assumes independent daily returns.
Residual autocorrelation would reduce the effective sample size and therefore the DSR. It was not
tested. The cost is not quite zero, since the return series itself is not available (§A.5), but it
is close to it: one further accumulator, $S_{11} = \sum_i r_i r_{i-1}$, yields
$\hat\rho_1 = (S_{11}/n - m^2)/m_2$ alongside the five already collected, and two more extend this
to a Ljung-Box on the first three lags. One backtest.

**Normality of the maximum.** The Gumbel approximation for $SR_0$ assumes that the Sharpes under
$H_0$ are Gaussian. With $n = 2011$ observations this is reasonable, but the marked skewness of
the returns weakens it. The effect goes in the unfavorable direction: positive skewness in the
distribution of sample Sharpes thickens the right tail and therefore raises $SR_0$. It is of order
$1/\sqrt{n}$, however, hence negligible with $n = 2011$.

**Single window.** The DSR is not an out-of-sample validation: it says that the result is not an
artifact of the *search*, not that it holds in different sub-windows of time. That is a separate
question, and it remains open; see §8.

---

## A.11 Conclusions

1. The Sharpe of 1.075 of S4′ tight **is not an artifact of the selection among fourteen
   configurations**: DSR = 99.04% under the conservative specification, 99.36% correcting the SE
   for the actual moments. The test is against the selection threshold $SR_0$, under the null
   that all fourteen configurations have a true Sharpe of zero: it says that S4′ is not selection
   noise, not that it is better than S4, from which it differs by +0.033 in log return over eight
   years (§6).

2. The result holds up to **about 65 trials** vs. the actual 14, a margin of a factor of five
   on the parameter a critique could focus on. The standard Bailey and López de Prado specification
   would give 99.99% and insensitivity to any $N$, but that insensitivity is an artifact of the
   correlation between the trials and should not be claimed.

3. The same moments settle how the platform's printed figures should be read (§A.8): LEAN samples
   the equity series on calendar days and annualizes it with 252, and its Probabilistic Sharpe
   Ratio is measured against a benchmark Sharpe of 1 rather than against zero. Both reproduce from
   our moments. This changes no result here; it is what allows §7 to say which platform figures
   can be cited and which cannot.

4. The return profile of S4′ has **marked positive skewness** (+2.01), consistent with the rest of
   the statistics and favorable in a way the Sharpe ratio does not capture.

5. Two distinct things remain uncovered: the upstream selection of the strategy family, and
   temporal stability. The second is outside the scope of this report and was not addressed; the
   first is a structural limit worth noting, not resolvable with these data.

6. The choice to compute the DSR from the raw moments (§A.5) rather than from the PSR in
   QuantConnect's interface turns out to be necessary, not merely prudent: that statistic,
   recomputed today on unchanged code, differs by 39 to 46 percentage points from the value
   preserved in the result files, on all five published strategies (§A.2.1). A figure that moves on
   a fixed input cannot serve as a basis, whichever of the two values is the right one.
