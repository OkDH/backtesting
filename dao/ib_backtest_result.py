import dao.backtest_result as br

class IbBacktestResult(br.BacktestResult):

    # 쿼터손절 횟수
    def set_quarter_count(self, quarter_count):
        self.quarter_count = quarter_count
    
    # 원금소진 횟수
    def set_exhaust_count(self, exhaust_count):
        self.exhaust_count = exhaust_count

    # 이동평균 이탈 손절 횟수
    def set_ma_cut_count(self, ma_cut_count):
        self.ma_cut_count = ma_cut_count

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
        print(f"원금소진 횟수: {self.exhaust_count}")
        print(f"쿼터손절 횟수: {self.quarter_count}")
        print(f"이평선 이탈손절 횟수: {self.ma_cut_count}")
        print("--------------------")
        print(f"일평균수익률: {self.avg_daily_profit_ratio:.2f}%")
        print(f"월평균수익률: {self.avg_monthly_profit_ratio:.2f}%")
        print(f"연평균수익률: {self.avg_annual_profit_ratio:.2f}%")
