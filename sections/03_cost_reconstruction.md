# §3. Method: one backtest, every cost level

**With this code architecture, a single instrumented backtest at 0 bps contains every cost level
in closed form.**

The question is not invented for the occasion: the paper raises it itself. Among the lines of
future work listed in §6.7 is "re-running with 2× and 5× baseline transaction costs to establish
the break-even cost level". What follows answers that question for every cost level rather than for
two, and without re-running anything.

## 3.1 The two invariances everything depends on

In an arbitrary backtest, introducing costs changes the history: the capital available at each
instant is different, and if decisions depend on capital or on execution prices, then *which*
trades occur changes as well. When that happens there is no closed form: every cost level is a
different experiment and has to be re-run.

The repository's code has two properties that break that circle.

The first: **the signal does not look at execution prices**. Entries and exits in all five
strategies evaluate `data[symbol].close`, that is, the market price of the bar, not the price at
which our order was filled. Slippage moves the second and leaves the first intact, so it does not
touch the condition that decides whether to open or close.

The second: **sizing is relative to equity**. `set_holdings` receives a fraction of net equity,
$\Lambda_t$, not a number of shares. A smaller account buys proportionally fewer shares, but the
position remains the same fraction of capital.

It follows that the set of trade instants $T = \{t_1,\dots,t_N\}$, the direction of each, and the
weight of each as a fraction of equity are **identical at every cost level**. What changes is how
much is subtracted at each fill, not which fills occur. This is a property of the code, not of the
data, and it is falsifiable: a stop-loss anchored to the fill price, or sizing by a fixed number of
shares, would be enough to break it. The constant order count across the five cost levels, in all
ten combinations, is the check that it does not break here.

## 3.2 The equity curve at cost $b$

Let $E_0(t)$ be the equity path in the 0 bps run. For the $i$-th fill, executed at $t_i$, let
$Q_i$ be the number of shares, $P_i$ the market price and $V_i$ the equity immediately before the
order. The **execution weight** is the notional traded as a fraction of equity:

$$w_i = \frac{|Q_i P_i|}{V_i}$$

With an additional slippage of $b$ basis points ($1\ \text{bps} = 10^{-4}$), the fill loses a
fraction $w_i\,b/10^4$ of equity. Since the effect is multiplicative and compounds fill after fill:

$$E_b(t) = E_0(t)\cdot \prod_{i:\,t_i \le t}\left(1 - \frac{w_i\, b}{10^4}\right)$$

Under the two invariances of §3.1 this is not an approximation: it is an identity, because the
product runs over exactly the same fills with exactly the same weights.

## 3.3 First order and break-even

Moving to the cumulative return $1 + R_b = E_b(T)/E(0)$ and taking the logarithm, the product
becomes a sum:

$$\ln(1+R_b) = \ln(1+R_0) + \sum_{i=1}^{N}\ln\!\left(1 - \frac{w_i b}{10^4}\right)$$

The cost per single fill is of order $10^{-4}$, so the expansion $\ln(1-x) = -x + O(x^2)$ is
extremely accurate term by term:

$$\ln(1+R_b) = \ln(1+R_0) - \frac{b}{10^4}\,w_{sum} + O(b^2), \qquad w_{sum} = \sum_{i=1}^{N} w_i$$

The log return is **affine in $b$**, with slope $-w_{sum}/10^4$. A single quantity accumulated
during the run, $w_{sum}$, describes the entire cost map. Setting the return to zero gives the
break-even level:

$$b^* = \frac{10^4\,\ln(1+R_0)}{w_{sum}}$$

The neglected term is $-\tfrac{b^2}{2\cdot 10^8}\sum_i w_i^2$. The sum of squares is not
observable from the data collected; $w_{sum}^2/N$ is a lower bound for it by Cauchy-Schwarz, with
equality if all weights were identical. It is used further on to verify that the residual grows
where it should.

## 3.4 Where the commissions are

The model reconstructs **slippage**. Commissions are not modeled at all: they are already inside
$E_0$, because the 0 bps run is not a run without costs but a run without *additional* slippage,
one that pays the Interactive Brokers fee model in full. The horizontal axis of every chart is
therefore "additional slippage", not "total cost".

For this to work only one thing is needed: that the commission, **as a fraction of equity**, be
the same at every level of $b$ for the same trade. The fee model is per share, with a rate of
$c = 0.005$ per share, and the quantity of an order is $|Q_i| = \Lambda_i V_i / P_i$. Therefore

$$\frac{\text{Fee}_i}{V_i} = c\,\frac{\Lambda_i}{P_i}$$

and both $\Lambda_i$ (which comes from SPY's 14-day volatility, a market quantity) and $P_i$ are
**invariant in $b$**. The commission takes the same fraction of equity at every cost level: it
multiplies every path by the same sequence of factors, and cancels in the ratio $E_b/E_0$. This
does not require the fraction to be constant *over time*, and it is not: it goes as $1/P_i$, so
over the sample it halves while SPY moves from about 240 to about 570 dollars. What the model
needs is that the fraction be the same in the two runs **at the same instant**, and it is, because
at that instant both see the same price and the same leverage. On the order of magnitude, half a cent
per share is equivalent to a tenth to a fifth of a basis point of slippage, a fraction of what is
being measured on the cost axis.

That commissions do follow equity can be seen in the raw data. Between the S0 `tight` run at 0 bps
and the one at 1 bps, commissions paid go from 15,460 to 11,230 dollars, that is, to 73%, at
exactly the same 3,594 orders; final equity instead falls to 52%. They are neither fixed nor
proportional to the final result: they follow equity along the whole path, higher at the start and
lower at the end. The real check, however, is the out-of-sample validation of §3.6, whose forty
predicted returns are all net of commissions: if commissions did not follow equity, the smaller
account at high $b$ would pay a larger fraction of them, and the model would overstate returns by
an amount increasing in $b$. It does not.

## 3.5 The per-order minimum

The declared fee model also has a minimum of 1 dollar per order, and a fixed minimum is not
proportional to equity. That is not the regime in operation: the average order pays between 3.98
and 4.77 dollars across all fourteen configurations, four to five times the threshold, and not
even the most penalized run gets there, since S1 `tight` at 2 bps closes at $-53\%$ and still pays
1.87 dollars per order. Where the minimum could bite, on the most de-leveraged days, it would make
commissions slightly *more* than proportional: the error is bounded and of known sign. The one run
that sits entirely inside the minimum is `hold24`, at 1.011 dollars per order, because it
rebalances only the delta and its orders are two orders of magnitude smaller: one more reason,
independent of those in §2, why its cost structure is not comparable with that of the strategies.

## 3.6 Out-of-sample validation

Forty rows, the four at $b>0$ for each of the ten strategy/threshold combinations, none of them
used to calibrate the model, which starts only from the 0 bps run of each combination.

[Table T6]

Maximum error 0.185 percentage points (pp), **mean absolute error 0.038pp**. The order count stays
constant across the five levels everywhere, so the invariance of §3.1 is not assumed but verified.

In percentage points, however, the error depends on the scale of the return and is not comparable
across rows: the invariant measure is the residual in bps of terminal log wealth. Up to 1 bps the
mean residual is $+0.41$ bps with a dispersion of 1.79 and no pattern, that is, noise. At 2 bps the
mean rises to $+3.98$ bps over the nine regular rows, compared with the $O(b^2)$ term of about 2.19
bps expected from the lower bound of §3.3: same sign, same order of magnitude. The linear model
begins to understate the cost exactly where it should.

[Figure F1]

The one off-scale row, 39 bps, is S1 `tight` at 2 bps, a run that closes at $-53.1\%$: near the
point where capital goes to zero the logarithm amplifies, and the same 0.185pp in absolute terms
weighs far more. This is not a failure of the model; it is the model's natural measure blowing up
where wealth goes to zero.

## 3.7 The $\bar w = \Lambda$ identity

The average weight per order, $\bar w = w_{sum}/N$, lies between 1.8052 and 1.8282 across all
fourteen configurations, vs. an average leverage `lambda_avg` $= 1.8056$.

[Table T7]

This is not an empirical regularity: it is an identity by construction. The strategies are
exclusively intraday, so every position opens from zero and closes in full within the day; every
order therefore moves a notional equal to 100% of the target position, and the weight of the order
coincides with the leverage of the moment. The mean of the weights can only coincide with the time
average of the leverage.

**Practical consequence**: substituting $w_{sum} \approx 1.81\,N$ into the break-even formula,

$$b^* \approx \frac{10^4\,\ln(1+R_0)}{1.81\,N}$$

the cost tolerance of any strategy in this class can be computed from the README table alone,
return and number of orders, before running any backtest. Verified out of sample on five
configurations: S2 1.90 vs. a measured 1.903; S3 1.96 vs. 1.957; S4 2.09 vs. 2.088;
S0 `tight` 1.669 vs. 1.670; S0 `loose` 2.113 vs. 2.107.

The identity has two deviations, both expected. `hold24` has $\bar w = 0.0434$, because
`set_holdings` in that case rebalances only the delta relative to the position already open: it
neither opens nor closes whole positions, and the identity does not apply for the same reason it
holds elsewhere. The `intraday` benchmark has $\bar w = 1.79416$, a gap of $-0.63\%$: the
shortfall in $w_{sum}$ is 45.73, that is, 25.5 delta-type fills at the observed average weight,
vs. 27 orders missing relative to the expected total of $2\times 2{,}012$. Every night of
carryover removes the evening exit and turns the next morning's entry into a partial rebalance: the
two counts agree to within the uncertainty on the weight of a delta fill, that is, the same
explanation read from two independent sides.

## 3.8 What the method does not reconstruct

From the equity curve alone one cannot recover the number of orders, the win rate, the average
gain and loss per trade, the expectancy, the commissions or the turnover: these are quantities that
require direct instrumentation of the backtest, not its return series. The method gives the cost
map, not the operating statement, which is why the fourteen configurations were run at 0 bps one
by one anyway.
