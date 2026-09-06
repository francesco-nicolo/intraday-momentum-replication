# region imports
from AlgorithmImports import *
from collections import deque
import numpy as np
# endregion

# =============================================================================
# S2'. NOT repository code: a construction of this report.
#
# The only difference from Strategy 2 is the entry condition, which drops the VWAP term and
# keeps band + EMA, the dual confirmation the paper describes and the repository implements in
# Strategy 4. It is the mirror cell of S4' in the entry-filter x exit-structure factorial
# (report, §4.1 and §6).
#
# The API is the snake_case one; the repository's files use the PascalCase aliases. The two are
# the same calls under different names.
#
# CONFIG below: exit_variant selects the exit threshold ("tight" is the one the paper specifies
# and the repository implements, "loose" the one the repository's README describes), slippage_bps
# the additional slippage. The w_sum accumulator is the sum of the notional traded as a fraction
# of equity, the single quantity the cost reconstruction of §3 needs; it is meaningful only at
# slippage_bps = 0, since that is the run every other cost level is reconstructed from.
# =============================================================================


class IntradayMomentum_2prime(QCAlgorithm):

    def initialize(self):
        # 1. Setup Basics
        self.set_start_date(2017, 5, 10)
        self.set_end_date(2025, 5, 10)
        self.set_cash(100000)

        # ---- CONFIG ----
        self.exit_variant = "tight"     # "tight" = repository code | "loose" = the README's exit
        self.slippage_bps = 0           # 0 | 0.25 | 0.5 | 1 | 2
        # ----------------

        # 2. Subscribe to Data
        self.spy = self.add_equity("SPY", Resolution.MINUTE)
        self.spy_symbol = self.spy.symbol

        if self.slippage_bps > 0:
            self.spy.set_slippage_model(
                ConstantSlippageModel(self.slippage_bps / 10000)
            )

        # 3. Strategy Parameters
        self.lookback = 14
        self.vol_target = 0.02
        self.minute_stats = {}
        self.daily_returns = deque(maxlen=self.lookback)

        # 4. Indicators & State
        self.vwap_ind = self.vwap(self.spy_symbol)
        self.ema_period = 100
        self.ema_ind = self.ema(self.spy_symbol, self.ema_period, Resolution.MINUTE)

        self.todays_open = None
        self.yesterdays_close = None

        # ---- Instrumentation: meaningful ONLY at slippage_bps = 0 ----
        self.w_sum = 0.0
        # --------------------------------------------------------------

        # 5. Warm up
        self.set_warm_up(self.lookback, Resolution.DAILY)

        # 6. Scheduled Events
        self.schedule.on(
            self.date_rules.every_day(self.spy_symbol),
            self.time_rules.before_market_close(self.spy_symbol, 0),
            self.record_end_of_day
        )

    def record_end_of_day(self):
        if not self.spy.has_data:
            return

        current_close = self.spy.close

        if self.yesterdays_close is not None:
            daily_ret = (current_close / self.yesterdays_close) - 1
            self.daily_returns.append(daily_ret)

        self.yesterdays_close = current_close
        self.todays_open = None

    def on_data(self, data: Slice):
        if self.spy_symbol not in data or data[self.spy_symbol] is None:
            return

        current_time = self.time
        current_price = data[self.spy_symbol].close
        time_key = current_time.strftime("%H:%M")

        if current_time.hour == 9 and current_time.minute == 31:
            self.todays_open = data[self.spy_symbol].open

        if (
            self.todays_open is None
            or self.yesterdays_close is None
            or len(self.daily_returns) < self.lookback
            or not self.ema_ind.is_ready
        ):
            return

        historical_moves = self.minute_stats.get(time_key, deque(maxlen=self.lookback))
        sigma = np.mean(historical_moves) if len(historical_moves) > 0 else 0

        if sigma == 0 and not self.is_warming_up:
            current_move = abs(current_price / self.todays_open - 1)
            historical_moves.append(current_move)
            self.minute_stats[time_key] = historical_moves
            return

        upper_bound = max(self.todays_open, self.yesterdays_close) * (1 + sigma)
        lower_bound = min(self.todays_open, self.yesterdays_close) * (1 - sigma)

        current_move = abs(current_price / self.todays_open - 1)
        historical_moves.append(current_move)
        self.minute_stats[time_key] = historical_moves

        # Forced liquidation at the end of the session
        if current_time.hour == 15 and current_time.minute >= 58:
            if self.portfolio.invested:
                self.liquidate(self.spy_symbol)
            return

        # Execution every 30 minutes, symmetric cadence (identical to S2)
        if current_time.minute % 30 == 0:
            vwap_val = self.vwap_ind.current.value
            ema_val = self.ema_ind.current.value

            if not self.portfolio.invested:
                target_leverage = self.calculate_dynamic_size()
                if target_leverage == 0:
                    return

                # ENTRY: band + EMA  <-- THE ONLY DIFFERENCE FROM S2 (no VWAP)
                if current_price > upper_bound and current_price > ema_val:
                    self.set_holdings(self.spy_symbol, target_leverage)

                elif current_price < lower_bound and current_price < ema_val:
                    self.set_holdings(self.spy_symbol, -target_leverage)

            else:
                if self.portfolio[self.spy_symbol].is_long:
                    threshold = (max(upper_bound, vwap_val) if self.exit_variant == "tight"
                                 else max(lower_bound, vwap_val))
                    if current_price < threshold:
                        self.liquidate(self.spy_symbol)

                elif self.portfolio[self.spy_symbol].is_short:
                    threshold = (min(lower_bound, vwap_val) if self.exit_variant == "tight"
                                 else min(upper_bound, vwap_val))
                    if current_price > threshold:
                        self.liquidate(self.spy_symbol)

    def calculate_dynamic_size(self):
        if len(self.daily_returns) < self.lookback:
            return 0

        current_vol = np.std(list(self.daily_returns))
        if current_vol == 0:
            return 0

        return min(2, self.vol_target / current_vol)

    def on_order_event(self, order_event):
        if order_event.status not in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED):
            return
        v = self.portfolio.total_portfolio_value
        if v > 0:
            self.w_sum += abs(order_event.fill_quantity * order_event.fill_price) / v

    def on_end_of_algorithm(self):
        self.set_runtime_statistic("w_sum", f"{self.w_sum:.4f}")
