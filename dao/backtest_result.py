import yfinance as yf

class BacktestResult:

    def __init__(self, start=None, end=None, duration=None, initial_capital=None, cash=None, balance_status=None,
                    max_drawdown=None, total_profit=None, total_loss=None, 
                    win_count=None, lose_count=None):
        self.start = start
        self.end = end
        self.duration = duration
        self.initial_capital = initial_capital
        self.cash = cash
        self.balance_status = balance_status
        self.max_drawdown = max_drawdown
        self.total_profit = total_profit
        self.total_loss = total_loss
        self.win_count = win_count
        self.lose_count = lose_count
        self.profit = self.balance_status - self.initial_capital
        self.profit_ratio = (self.profit / self.initial_capital) * 100
        self.profit_loss_ratio = self.total_profit / abs(self.total_loss)
        self.win_rate = self.win_count / (self.win_count + self.lose_count) * 100
        self.avg_daily_profit_ratio = self.profit / self.duration
        self.avg_annual_profit_ratio = self.avg_daily_profit_ratio * 247
        self.avg_monthly_profit_ratio = self.avg_annual_profit_ratio / 12

        snp_df = yf.download("^GSPC", start=self.start, end=self.end)

        self.snp = (snp_df.iloc[-1]["Close"] - snp_df.iloc[0]["Close"]) / snp_df.iloc[0]["Close"] * 100

    def print(self):
        print("============ 백테스팅 결과 ============")
        print(f"시작일: {self.start}")
        print(f"종료일: {self.end}")
        print(f"총 거래일: {self.duration}")
        print("--------------------")
        print(f"투자 원금: {self.initial_capital:,.2f}")
        print(f"보유 현금: {self.cash:,.2f}")
        print(f"잔고 현황: {self.balance_status:,.2f}")
        print(f"손익금: {self.profit:,.2f}")
        print(f"수익률: {self.profit_ratio:.1f}%")
        print(f"S&P500 상승률: {self.snp:.1f}%")
        print(f"MDD: {self.max_drawdown:.1f}%")
        print("--------------------")
        print(f"실현 수익금의 합: {self.total_profit:,.2f}")
        print(f"실현 손실금의 합: {self.total_loss:,.2f}")
        print(f"손익비: {self.profit_loss_ratio:,.2f}")
        print("--------------------")
        print(f"실현 수익 횟수: {self.win_count:,}")
        print(f"실현 손실 횟수: {self.lose_count:,}")
        print(f"매매 성공률: {self.win_rate:.1f}%")
        print("--------------------")
        print(f"일평균수익률: {self.avg_daily_profit_ratio:.1f}%")
        print(f"월평균수익률: {self.avg_monthly_profit_ratio:.1f}%")
        print(f"연평균수익률: {self.avg_annual_profit_ratio:.1f}%")

    def get_start(self):
        return self.start

    def get_end(self):
        return self.end

    def get_duration(self):
        return self.duration

    def get_initial_capital(self):
        return self.initial_capital

    def get_cash(self):
        return self.cash

    def get_max_drawdown(self):
        return self.max_drawdown

    def get_total_profit(self):
        return self.total_profit

    def get_total_loss(self):
        return self.total_loss

    def get_win_count(self):
        return self.win_count

    def get_lose_count(self):
        return self.lose_count

    def get_profit(self):
        return self.profit

    def get_profit_ratio(self):
        return self.profit_ratio

    def get_profit_loss_ratio(self):
        return self.profit_loss_ratio

    def get_win_rate(self):
        return self.win_rate

    def get_avg_daily_profit_ratio(self):
        return self.avg_daily_profit_ratio

    def get_avg_annual_profit_ratio(self):
        return self.avg_annual_profit_ratio

    def get_avg_monthly_profit_ratio(self):
        return self.avg_monthly_profit_ratio