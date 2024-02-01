import yfinance as yf

class BacktestResult:

    def __init__(self, start=None, end=None, duration=None, initial_capital=None, cash=None,
                    max_drawdown=None, total_profit=None, total_loss=None, 
                    win_count=None, lose_count=None):
        self.start = start
        self.end = end
        self.duration = duration
        self.initial_capital = initial_capital
        self.cash = cash
        self.max_drawdown = max_drawdown
        self.total_profit = total_profit
        self.total_loss = total_loss
        self.win_count = win_count
        self.lose_count = lose_count
        self.profit = self.cash - self.initial_capital,
        self.profit_ratio = (self.profit / self.initial_capital) * 100
        self.profit_loss_ratio = self.total_profit / self.total_loss
        self.win_rate = self.win_count / (self.win_count + self.lose_count) * 100
        self.avg_daily_profit_ratio = self.profit / self.duration
        self.avg_annual_profit_ratio = self.avg_daily_profit_ratio * 247
        self.avg_monthly_profit_ratio = self.avg_annual_profit_ratio / 12

        snp_df = yf.download("^GSPC", start=stock.index[0], end=stock.index[-1])

        self.snp = (snp_df.iloc[-1]["Close"] - snp_df.iloc[0]["Close"]) / snp_df.iloc[0]["Close"] * 100

    def print(self):
        print("============ 백테스팅 결과 ============")
        print(f"시작일: {self.start}")
        print(f"종료일: {self.end}")
        print(f"총 거래일: {self.duration}")
        print(f"투자 원금: {self.initial_capital:.2f}")
        print(f"보유 현금: {self.cash:.2f}")
        print(f"실현손익금: {self.profit:.2f}")
        # self.result["ReturnRatio"] = {"label":"누적수익률(%)", "value":(self.result["Return"]["value"] / self.initial_capital) * 100}
        # self.result["MaxDrawdown"] = {"label":"MDD(%)", "value":max_drawdown}
        # self.result["TotalProfit"] = {"label":"실현 수익금의 합", "value":stock[stock["Profit"] > 0]["Profit"].sum()}
        # self.result["TotalLoss"] = {"label":"실현 손실금의 합", "value":stock[stock["Profit"] < 0]["Profit"].sum()}
        # self.result["ProfitLossRatio"] = {"label":"손익비", "value":self.result["TotalProfit"]["value"] / abs(self.result["TotalLoss"]["value"])}
        # self.result["WinCount"] = {"label":"실현 수익 횟수", "value":len(stock[stock["Profit"] > 0])}
        # self.result["LoseCount"] = {"label":"실현 손익 횟수", "value":len(stock[stock["Profit"] <= 0])}
        # self.result["WinRate"] = {"label":"매매 성공률(%)", "value":self.result["WinCount"]["value"] / (self.result["WinCount"]["value"] + self.result["LoseCount"]["value"]) * 100}
        # self.result["AvgDailyReturnRatio"] = {"label":"일평균수익률(%)", "value":self.result["ReturnRatio"]["value"] / self.result["Duration"]["value"]}
        # self.result["AvgAnnualReturnRatio"] = {"label":"연평균수익률(%)", "value":self.result["AvgDailyReturnRatio"]["value"] * 247}
        # self.result["AvgMonthlyReturnRatio"] = {"label":"월평균수익률(%)", "value":self.result["AvgAnnualReturnRatio"]["value"] / 12}
        # snp = yf.download("^GSPC", start=stock.index[0], end=stock.index[-1])
        # self.result["S&P500"] = {"label":"S&P500 상승률(%)", "value":(snp.iloc[-1]["Close"] - snp.iloc[0]["Close"]) / snp.iloc[0]["Close"] * 100}