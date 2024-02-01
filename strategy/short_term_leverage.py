import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf
import strategy.secondary_indicator as si
import dao.backtest_result as br

'''
미국 3배 레버리지 ETF 단타 전략
# 진입 : 양봉전환하면서 저가 대비 n%이상 상승했을 때 종가로 진입
# 매도 : 평단가 대비 n분할의 1칸 가격 위에 매도
# 손절 : 평단가 대비 n분할의 1간 가격 아래에서 매도
'''
class ShortTermLeverage:

    def __init__(self, stock, initial_capital = 10000, standard_rsi = 0, target_division = 5, standard_rate = 1.1, is_reinvest = True):
        self.stock = stock
        self.initial_capital = initial_capital # 초기자본
        self.standard_rsi = standard_rsi # 진입 기준 rsi (standard_rsi 높을 때 진입)
        self.target_division = target_division # 목표가 될 분할 수(분할 수가 높을 수록 목표 가격이 낮음)
        self.standard_rate = standard_rate # 진입 기준 저가대비 상승률 ex) 1.1 = 양본전환 후 저가 대비 10%이상 종가 마무리되면 진입
        self.is_reinvest = is_reinvest # 수익금 재투자 여부(False이면 매수최대금이 원금을 넘지 않음) 
        self.result = None

        self.generate_signals()

    # 보조 지표 세팅 및 진입 시그널 생성
    def generate_signals(self):
        stock = self.stock

        # 볼린저밴드
        stock["UpperLine"], stock["LowerLine"] = si.bollinger_band(stock["Close"])

        # RSI
        stock["Rsi"] = si.rsi(stock["Close"])

        # 양봉 or 음봉
        stock["Change"] = stock["Close"] - stock["Open"]
        stock["IsUp"] = np.where(stock["Change"] > 0, True, False)

        # 진입 시그널
        stock["Signal"] = False
        entry_low = None
        for index, row in stock.iterrows():
            if row["IsUp"] and entry_low is None:
                entry_low = row["Low"]
            if row["IsUp"] and entry_low is not None: # 양봉이면서
                if row["Rsi"] > self.standard_rsi: 
                    if row["Close"] >= entry_low * self.standard_rate:  # 종가가 저가대비 n% 이상 상승한 경우
                        stock.at[index, "Signal"] = True
                        one_block_price = (row["Close"] - entry_low) / self.target_division # n분할
                        stock.at[index, "OneBlockPrice"] = one_block_price
                        stock.at[index, "StopLoss"] = (row["Close"] - (one_block_price * 1))
            elif not row["IsUp"]:
                entry_low = None
        return stock
    
    # 백테스팅 시작
    def backtest(self):

        stock = self.stock

        cash = self.initial_capital # 보유 현금

        available_buy_cash = 0 # 한번 매수에 사용가능한 금액

        # MDD
        peek_value = 0
        drawdown = 0 
        max_drawdown = 0

        position = None
        
        for index, row in stock.iterrows():
            
            if position is not None:  # 이미 포지션을 가지고 있는 경우
                # 목표가
                target_price = position["EntryPrice"] + position["OneBlockPrice"]
                # target_price = position["EntryPrice"] * 1.01
                # 수익 실현
                if row["Open"] >= target_price:
                    cash += position["Shares"] * row["Open"]  # 주식 판매로 얻은 금액 추가
                    # 매도 기록 추가
                    stock.at[index, "SellPrice"] = row["Open"]
                    stock.at[index, "SellShares"] = position["Shares"]
                    stock.at[index, "Profit"] = (row["Open"] * position["Shares"]) - position["TotalBuyPrice"]
                    position = None  # 포지션 해제
                elif row["High"] >= target_price: # 목표 매도가에 매도
                    cash += position["Shares"] * target_price  # 주식 판매로 얻은 금액 추가
                    # 매도 기록 추가
                    stock.at[index, "SellPrice"] = target_price
                    stock.at[index, "SellShares"] = position["Shares"]
                    stock.at[index, "Profit"] = (target_price * position["Shares"]) - position["TotalBuyPrice"]
                    position = None  # 포지션 해제
                elif row["Open"] <= position["StopLoss"]: # 장초반 손절
                    cash += position["Shares"] * row["Open"]  # 주식 판매로 얻은 금액 추가
                    # 매도 기록 추가
                    stock.at[index, "SellPrice"] = row["Open"]
                    stock.at[index, "SellShares"] = position["Shares"]
                    stock.at[index, "Profit"] = (row["Open"] * position["Shares"]) - position["TotalBuyPrice"]
                    position = None  # 포지션 해제
                elif row["Low"] <= position["StopLoss"]: # 손절
                    cash += position["Shares"] * position["StopLoss"]  # 주식 판매로 얻은 금액 추가
                    # 매도 기록 추가
                    stock.at[index, "SellPrice"] = position["StopLoss"]
                    stock.at[index, "SellShares"] = position["Shares"]
                    stock.at[index, "Profit"] = (position["StopLoss"] * position["Shares"]) - position["TotalBuyPrice"]
                    position = None  # 포지션 해제

            if row["Signal"] and position is None and cash > 0:  # 진입 신호가 발생하고 현금이 있는 경우

                # 한번에 매수 가능한 현금
                if self.is_reinvest :
                    available_buy_cash = cash # 수익금 재투자
                else :
                    available_buy_cash = cash if cash < self.initial_capital else self.initial_capital # 원금안에서만 매수

                # 매수 가능한 주식 수 계산
                shares = available_buy_cash // row["Close"]  
                position = {
                    "EntryDate": index, 
                    "EntryPrice": row["Close"], 
                    "Shares": shares,
                    "TotalBuyPrice": row["Close"] * shares,
                    "AvailableBuyCash" : available_buy_cash,
                    "OneBlockPrice": row["OneBlockPrice"],
                    "StopLoss": row["StopLoss"]
                }
                # 매수 기록 추가
                stock.at[index, "BuyPrice"] = row["Close"]
                stock.at[index, "BuyShares"] = shares
                cash -= shares * row["Close"]  # 주식 구입으로 사용된 금액 차감
                
            stock.at[index, "Cash"] = cash
            value = (position["Shares"] * row["Close"]) if position is not None else 0 # 보유하는 주식이 있다면 보유주식수 * 종가
            value += cash
            stock.at[index, "Value"] = value

            # MDD
            if value > peek_value:
                peek_value = value
                drawdown = 0
            else:
                drawdown = (peek_value - value) / peek_value * 100
                max_drawdown = max(max_drawdown, drawdown)
            stock.at[index, "Drawdown"] = 0 - drawdown
            
        # 백테스팅 결과
        self.result = br.BacktestResult(
            start = stock.index[0],
            end = stock.index[-1],
            duration = len(stock),
            initial_capital = self.initial_capital,
            cash = cash,
            max_drawdown = max_drawdown,
            total_profit = stock[stock["Profit"] > 0]["Profit"].sum(),
            total_loss = stock[stock["Profit"] < 0]["Profit"].sum(),
            win_count = len(stock[stock["Profit"] > 0]),
            lose_count = len(stock[stock["Profit"] <= 0]),
        )

        return stock

    # 차트 그리기 함수
    def plot_trades_candlestick(self):
        
        apds = [ 
            # 매수, 매도 포인트
            mpf.make_addplot(self.stock["BuyPrice"], type='scatter'),
            mpf.make_addplot(self.stock["SellPrice"], type='scatter'),
            # win / lose 그리기
            mpf.make_addplot(self.stock["Profit"].apply(lambda x: x if pd.notnull(x) and x >= 0 else np.nan), type='scatter', color="red", panel=1),
            mpf.make_addplot(self.stock["Profit"].apply(lambda x: x if pd.notnull(x) and x < 0 else np.nan), type='scatter', color="blue", panel=1),
            # RSI
            mpf.make_addplot(self.stock["Rsi"], type="line", ylabel='RSI', panel=2),
            # 자산가치
            mpf.make_addplot(self.stock["Value"], type='line', ylabel='Value', color="red", panel=3),
            mpf.make_addplot(self.stock["Drawdown"], type='line', ylabel='MDD', panel=3),
            # 볼린저밴드
            # mpf.make_addplot(self.stock["UpperLine"]), 
            # mpf.make_addplot(self.stock["LowerLine"]),
            
        ]

        # Plot the candlestick chart
        mpf.plot(self.stock, title="Back Testing", type='candle', style="yahoo", addplot=apds, mav=(20, 60, 120), volume=False, panel_ratios=(5,1,1,2), figscale=1.3)

    # 백테스팅 결과 가져오기
    def get_result(self):
        return self.result

    