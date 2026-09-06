"""
equity_moments.py: the instrumentation behind Appendix A of the report.

Five scalar accumulators of the daily equity returns (count and the first four power sums), from
which mean, standard deviation, skewness and kurtosis are recovered without exporting the return
series. The QuantConnect Free plan offers neither API access nor the Object Store, so the series
cannot be downloaded; the five numbers are emitted as runtime statistics, a channel that does not
consume the log quota. The Deflated Sharpe Ratio of Appendix A is computed from them by
build_tables.py (function dsr_appendix), which has the S4' tight values hard-coded in DSR_RAW.

How it was used. The strategy files themselves are the original repository's, unchanged except
for the slippage setting and, for the constructed cells S2' and S4', the one-line change to the
VWAP entry condition described in §4.1 of the report. For the single run at 0 bps that Appendix A
rests on, the method shown in §A.5 was added to the S4' tight algorithm class; this file packages
the same code as three static helpers, so that it can be dropped into any QCAlgorithm subclass
with three calls and no edit to the class body:

    1. in initialize():            EquityMoments.setup(self)
    2. scheduled one minute before the close, every trading day (after the 15:58 liquidation, so
       the portfolio is already flat when the sample is taken):
                                   self.schedule.on(self.date_rules.every_day(self.spy_symbol),
                                                    self.time_rules.before_market_close(self.spy_symbol, 1),
                                                    lambda: EquityMoments.record(self))
    3. in on_end_of_algorithm():   EquityMoments.report(self)

The sample moments are then (S_k = ret_sk, n = ret_n):

    m1 = S1/n,   m2 = S2/n - m1^2
    g3 = (S3/n - 3 m1 S2/n + 2 m1^3) / m2^(3/2)
    g4 = (S4/n - 4 m1 S3/n + 6 m1^2 S2/n - 3 m1^4) / m2^2        (kurtosis, non-excess)

Exponential formatting with 12 digits is deliberate: the sum of fourth powers is of order 1e-5
and fixed-point formatting would zero it out. The consistency check of Appendix A, §A.6.3
(sum of ln(1+r) expanded in the power sums vs. the logarithm of the reported net profit) uses the
same five numbers and nothing else.
"""


class EquityMoments:
    """Static helpers; `algo` is the QCAlgorithm instance."""

    @staticmethod
    def setup(algo):
        algo.prev_equity = None
        algo.ret_n = 0
        algo.ret_s1 = 0.0
        algo.ret_s2 = 0.0
        algo.ret_s3 = 0.0
        algo.ret_s4 = 0.0

    @staticmethod
    def record(algo):
        if algo.is_warming_up:
            return
        v = algo.portfolio.total_portfolio_value
        if v <= 0:
            return
        if algo.prev_equity is not None and algo.prev_equity > 0:
            r = v / algo.prev_equity - 1.0
            algo.ret_n += 1
            algo.ret_s1 += r
            algo.ret_s2 += r * r
            algo.ret_s3 += r * r * r
            algo.ret_s4 += r * r * r * r
        algo.prev_equity = v

    @staticmethod
    def report(algo):
        algo.set_runtime_statistic("11 ret_n", f"{algo.ret_n}")
        algo.set_runtime_statistic("12 ret_s1", f"{algo.ret_s1:.12e}")
        algo.set_runtime_statistic("13 ret_s2", f"{algo.ret_s2:.12e}")
        algo.set_runtime_statistic("14 ret_s3", f"{algo.ret_s3:.12e}")
        algo.set_runtime_statistic("15 ret_s4", f"{algo.ret_s4:.12e}")
