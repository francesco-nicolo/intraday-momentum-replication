# region imports
from AlgorithmImports import *
from collections import deque
import numpy as np
# endregion

# =============================================================================
# BENCHMARK. This is NOT code from the original repository: it is our own construction.
#
# Long SPY with no signal at all, sized with the same leverage rule as the strategies:
# Lambda = min(2, vol_target / sigma_14d).
#
#   mode = "hold24"    position held overnight as well, rebalanced every morning at 9:31.
#                      Measures the opportunity cost of the whole intraday approach.
#   mode = "intraday"  entry at 9:31, liquidation at 15:58. Same session exposure as the
#                      strategies, no signal. It is the matched comparison: if a strategy
#                      does not beat this, the signal adds nothing.
#
# The two matched runs of §2 (entry at 10:00, long and short) were produced from this same
# file by changing the entry condition to `hour == 10 and minute == 0` and, for the short
# run, the sign of the target in set_holdings.
#
# NOTES:
#  - LEAN does not charge margin interest. With Lambda > 1 the return is overstated by about
#    (Lambda - 1) * r per year. It has to be subtracted by hand (§2, T3).
#  - The security leverage is raised to 4 only to prevent forced margin calls (which would
#    liquidate the position and corrupt the series). The margin_calls counter checks that
#    none fire anyway.
#  - The benchmark is long-only; the strategies also go short.
# =============================================================================


class VolTargetedBenchmark(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2017, 5, 10)
        self.set_end_date(2025, 5, 10)
        self.set_cash(100000)

        # ---- CONFIG ----
        self.mode = "intraday"          # "hold24" | "intraday"
        self.slippage_bps = 0           # 0 | 0.25 | 0.5 | 1 | 2
        # ----------------

        self.spy = self.add_equity("SPY", Resolution.MINUTE)
        self.spy_symbol = self.spy.symbol
        self.spy.set_leverage(4)        # only to prevent forced margin calls

        if self.slippage_bps > 0:
            self.spy.set_slippage_model(
                ConstantSlippageModel(self.slippage_bps / 10000)
            )

        self.lookback = 14
        self.vol_target = 0.02
        self.daily_returns = deque(maxlen=self.lookback)
        self.yesterdays_close = None

        # ---- Instrumentation: valid ONLY at slippage_bps = 0 ----
        self.w_sum = 0.0
        self.margin_calls = 0
        self.lambda_sum = 0.0
        self.lambda_days = 0
        self.lambda_capped_days = 0     # days on which the cap at 2 binds

        # Equity and leverage drag.
        #   eq_sum / eq_n  = average equity  ->  integral = years * average, which converts
        #                    the commissions in dollars into an annual rate (the fee model is
        #                    per share, so commissions are a constant fraction of equity: the
        #                    right denominator is the integral, not the initial capital).
        #   drag_sum       = sum of Lambda(Lambda-1) r^2 rewritten with the portfolio return
        #                    alone: since r_port = Lambda*r, Lambda(Lambda-1) r^2 equals
        #                    (Lambda-1)/Lambda * r_port^2. Annual drag = 0.5 * drag_sum / years.
        #                    It never passes through ann_std, so it is immune to LEAN's
        #                    annualization convention.
        # In intraday mode the portfolio is flat overnight, so the return between two closes
        # is exactly the return of the session.
        self.eq_sum = 0.0
        self.eq_n = 0
        self.prev_equity = None
        self.drag_sum = 0.0
        self.lam_today = 0.0
        # --------------------------------------------------------

        self.set_warm_up(self.lookback, Resolution.DAILY)

        self.schedule.on(
            self.date_rules.every_day(self.spy_symbol),
            self.time_rules.before_market_close(self.spy_symbol, 0),
            self.record_end_of_day
        )

    def record_end_of_day(self):
        # ---- Equity / drag instrumentation (valid ONLY at 0 bps) ----
        if not self.is_warming_up:
            v = self.portfolio.total_portfolio_value
            if v > 0:
                self.eq_sum += v
                self.eq_n += 1
                if self.prev_equity is not None and self.prev_equity > 0:
                    r = v / self.prev_equity - 1.0
                    if self.lam_today > 1.0:
                        self.drag_sum += (self.lam_today - 1.0) / self.lam_today * r * r
                self.prev_equity = v
            self.lam_today = 0.0
        # ----------------------------------------------------------------

        if not self.spy.has_data:
            return

        current_close = self.spy.close

        if self.yesterdays_close is not None:
            daily_ret = (current_close / self.yesterdays_close) - 1
            self.daily_returns.append(daily_ret)

        self.yesterdays_close = current_close

    def on_data(self, data: Slice):
        if self.spy_symbol not in data or data[self.spy_symbol] is None:
            return
        if self.is_warming_up:
            return

        current_time = self.time

        # Liquidation at 15:58, same time as the strategies (intraday mode only)
        if self.mode == "intraday" and current_time.hour == 15 and current_time.minute >= 58:
            if self.portfolio.invested:
                self.liquidate(self.spy_symbol)
            return

        # Entry / rebalance at 9:31
        if current_time.hour == 9 and current_time.minute == 31:
            target_leverage = self.calculate_dynamic_size()
            if target_leverage == 0:
                return

            self.lambda_sum += target_leverage
            self.lambda_days += 1
            if target_leverage >= 2:
                self.lambda_capped_days += 1

            self.lam_today = target_leverage

            self.set_holdings(self.spy_symbol, target_leverage)

    def calculate_dynamic_size(self):
        if len(self.daily_returns) < self.lookback:
            return 0

        current_vol = np.std(list(self.daily_returns))
        if current_vol == 0:
            return 0

        return min(2, self.vol_target / current_vol)

    def on_margin_call_warning(self):
        self.margin_calls += 1

    def on_order_event(self, order_event):
        if order_event.status not in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED):
            return
        v = self.portfolio.total_portfolio_value
        if v > 0:
            self.w_sum += abs(order_event.fill_quantity * order_event.fill_price) / v

    def on_end_of_algorithm(self):
        self.set_runtime_statistic("00 mode", f"{self.mode} {self.slippage_bps}bps")
        self.set_runtime_statistic("01 w_sum", f"{self.w_sum:.4f}")
        avg = self.lambda_sum / self.lambda_days if self.lambda_days else 0
        self.set_runtime_statistic("02 lambda_avg", f"{avg:.4f}")
        pct = 100 * self.lambda_capped_days / self.lambda_days if self.lambda_days else 0
        self.set_runtime_statistic("03 pct_capped", f"{pct:.1f}%")
        self.set_runtime_statistic("04 margin_calls", f"{self.margin_calls}")

        # ---- Raw values, for build_tables.py ----
        avg_eq = self.eq_sum / self.eq_n if self.eq_n else 0.0
        self.set_runtime_statistic("05 eq_n", f"{self.eq_n}")
        self.set_runtime_statistic("06 avg_equity", f"{avg_eq:.4f}")
        self.set_runtime_statistic("07 drag_sum", f"{self.drag_sum:.12e}")
        self.set_runtime_statistic("08 total_fees", f"{self.portfolio.total_fees:.2f}")

        # ---- Derived values, for immediate reading (%/year) ----
        years = (self.end_date - self.start_date).days / 365.25
        fee_pct = 100 * self.portfolio.total_fees / (years * avg_eq) if avg_eq else 0.0
        lev_pct = 100 * 0.5 * self.drag_sum / years
        self.set_runtime_statistic("09 fee_drag_pct", f"{fee_pct:.4f}")
        self.set_runtime_statistic("10 lev_drag_pct", f"{lev_pct:.4f}")
