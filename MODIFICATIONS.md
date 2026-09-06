# What was run, and what was changed

The 58 backtests come from two places. The five published strategies are the original authors'
code, which this repository does not duplicate: it is read from a local clone, and the three
changes made to it are recorded below. The two constructed cells, S2′ and S4′, are not their
code, and their files are in `strategies/`.

The strategy sources of the original repository have not changed since commit `b960d36` of
23 March 2026, so any clone made after that date matches what was run here.

---

## The five published strategies: three changes to the authors' files

**1. The exit threshold.** The five files implement the exit the paper specifies, which this
report calls `tight`: a long closes when the price falls back below `max(upper_bound, vwap)`, a
short when it rises above `min(lower_bound, vwap)`. The `loose` variant is the exit the original
README describes instead, with the opposite band; the two are compared in §4.5 and §5, and half
of every table in the report is `loose`. It is one line per direction:

```python
# long                                # short
max(upper_bound, vwap_val)   tight    min(lower_bound, vwap_val)
max(lower_bound, vwap_val)   loose    min(upper_bound, vwap_val)
```

In `strategy0.py` lines 112 and 115, `strategy1.py` 101 and 105, `strategy2.py` 127 and 131,
`strategy3.py` 124 and 138, `strategy4.py` 124 and 137.

**2. Slippage.** No slippage model is set in any of the five files, so a run as committed pays
the Interactive Brokers per-share commission and nothing else: that is the 0 bps column of every
table. The other four columns add a constant model, in `Initialize` after the `AddEquity` call:

```python
self.spy.SetSlippageModel(ConstantSlippageModel(bps / 10000))     # bps in {0.25, 0.5, 1, 2}
```

**3. The `w_sum` accumulator.** The cost reconstruction of §3 needs one quantity that no LEAN
statistic reports: the sum, over every fill, of the notional traded as a fraction of the equity
at that moment. Two methods added to the algorithm class collect it and emit it as a runtime
statistic, the only channel the QuantConnect Free plan offers that does not consume the log
quota:

```python
    def OnOrderEvent(self, order_event):
        if order_event.Status not in (OrderStatus.Filled, OrderStatus.PartiallyFilled):
            return
        v = self.Portfolio.TotalPortfolioValue
        if v > 0:
            self.w_sum += abs(order_event.FillQuantity * order_event.FillPrice) / v

    def OnEndOfAlgorithm(self):
        self.SetRuntimeStatistic("w_sum", f"{self.w_sum:.4f}")
```

with `self.w_sum = 0.0` initialised alongside the other state. It records and reports; it changes
no decision the algorithm takes. The value is meaningful only at 0 bps, which is the run every
other cost level is reconstructed from.

---

## The two constructed cells: `strategies/`

S2′ and S4′ are not in the repository under analysis and were never run there. They complete the
factorial of §4: the entry-filter axis crossed with the exit-structure axis.

| file | what it is |
|:---|:---|
| [`strategies/strategy2_prime.py`](strategies/strategy2_prime.py) | Strategy 2 **without** the VWAP entry filter: band + EMA, 30-minute simple exit |
| [`strategies/strategy4_prime.py`](strategies/strategy4_prime.py) | Strategy 4 **with** the VWAP entry filter: band + EMA + VWAP, 5-minute exit with the persistence gate |

Each is one condition away from the repository cell it is built from, and the line is marked in
the source. Both carry the two switches at the top of `initialize` — `exit_variant` for the
threshold and `slippage_bps` for the cost level — so the four rows of T13 come from these two
files and four settings, and both carry the same `w_sum` accumulator as the runs above.

They are written against the snake_case API; the repository's files use the PascalCase aliases.
The two are the same calls under different names.

---

## The instrumented run of Appendix A

One further run is an addition rather than a variant: the single S4′ `tight` run at 0 bps that
the Deflated Sharpe Ratio rests on also carries the five accumulators of
`instrumentation/equity_moments.py`, added with the three calls documented at the top of that
file. Like `w_sum`, it only records: it changes nothing the algorithm does.
