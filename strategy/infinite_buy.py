import yfinance as yf
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf
import strategy.secondary_indicator as si
import dao.ib_backtest_result as ibr

class InfiniteBuy:
    
    def __init__(self, stock, initial_capital = 10000, commission=0.007, divisions=40, standard_rsi=0, is_quarter_mode=True, is_ma_cut=False, is_reinvest=True):
        self.stock = stock
        self.initial_capital = initial_capital # 초기자본
        self.commission = commission # 수수료
        self.standard_rsi = standard_rsi # 진입 기준 rsi (standard_rsi 높을 때 진입)
        self.is_reinvest = is_reinvest # 수익금 재투자 여부(False이면 매수최대금이 원금을 넘지 않음) 
        self.divisions = divisions
        self.is_quarter_mode = is_quarter_mode # 쿼터 손절 여부
        self.is_ma_cut = is_ma_cut # 200일선 커트 여부
        self.result = None

        self.generate_signals()

    def generate_signals(self):
        stock = self.stock

        # RSI
        stock["Rsi"] = si.rsi(stock["Close"])

        # MA
        stock["MA20"] = si.moving_average(stock["Close"], window=20)
        stock["MA200"] = si.moving_average(stock["Close"], window=200)

        # MACD
        # stock["Macd"], stock["MacdSignal"] = si.macd(stock["Close"])

    def backtest(self):

        stock = self.stock

        cash = self.initial_capital # 보유 현금

        available_buy_cash = 0 # 한번 매수에 사용가능한 금액

        # MDD
        peek_value = 0
        drawdown = 0 
        max_drawdown = 0

        # 현재 포지션
        position = None

        # 매매 내역
        trade_history = []

        # 쿼터손절 횟수
        quarter_count = 0 

        # 원금소진 횟수
        exhaust_count = 0

        # 이동평균 이탈 손절 횟수
        ma_cut_count = 0

        
        for index, row in stock.iterrows():

            if index <= stock.index[13]: # 이전 13일간의 데이터는 스킵
                continue

            if position is not None:  # 이미 포지션을 가지고 있는 경우

                # if (self.is_ma_cut and row["Close"] < row["MA200"]): # 종가가 200일선 아래라면 전체 손절
                if (self.is_ma_cut and row["MA20"] < row["MA200"]):
                    ma_cut_count += 1

                # if (self.is_ma_cut and row["Macd"] < row["MacdSignal"]):
                    amount = row["Close"] * position["Shares"]
                    sell_commission = math.floor(amount * self.commission * 100) / 100
                    cash += amount - sell_commission  # 주식 판매로 얻은 금액 추가

                    # 손익금
                    profit = amount - (position["EntryPrice"] * position["Shares"]) - sell_commission

                    # 매도 기록 추가
                    trade_history.append({
                        "Type": "SELL",
                        "Price": row["Close"],
                        "Shares": position["Shares"],
                        "Commission": sell_commission,
                        "EntryPrice": position["EntryPrice"],
                        "Profit": profit
                    })

                    stock.at[index, "End"] = row["Close"]
                    position = None # 포지션 해제

                else:
                    # T : 매수 누적액 / 1회 매수 금액 (소수점 둘째자리 올림)
                    t = position["TotalBuyPrice"] / position["OneBuyCash"]
                    t = math.ceil(t * 100) / 100

                    # 진행률 상관없이 
                    # 수량의 1/4는 LOC (10 - T/2 * (40/분할수))%
                    # 수량의 3/4는 +10% 매도
                    shares = position["Shares"]

                    # 1/4 LOC 매도
                    target_per1 = 10 - t/2 * (40/self.divisions)
                    target_per1 = round(target_per1, 1)
                    target_price1 = position["EntryPrice"] * (1 + (target_per1/100)) # + 수수료 고려하여 위에서 팔 경우 코딩 수정 필요
                    target_shares1 = math.floor(shares / 4)

                    # 39 < T <= 40이라면 쿼터 손절
                    if self.is_quarter_mode and 39 < t and t <= 40:
                        quarter_count += 1

                        # 1/4를 MOC(종가에 무조건 매도) 매도
                        amount = row["Close"] * target_shares1
                        sell_commission = math.floor(amount * self.commission * 100) / 100
                        cash += amount - sell_commission  # 주식 판매로 얻은 금액 추가
                        position["Shares"] = shares - target_shares1
                        position["TotalBuyPrice"] -= amount

                        # 손익금
                        profit = amount - (position["EntryPrice"] * target_shares1) - sell_commission
                        position["Profit"] += profit

                        # 매도 기록 추가
                        trade_history.append({
                            "Type":"SELL",
                            "Price": row["Close"],
                            "Shares": target_shares1,
                            "Commission": sell_commission,
                            "EntryPrice": position["EntryPrice"],
                            "Profit": profit
                        })

                        stock.at[index, "Quarter"] = position["EntryPrice"]

                    else:
                        if target_shares1 > 0 and row["Close"] > target_price1:
                            amount = row["Close"] * target_shares1
                            sell_commission = math.floor(amount * self.commission * 100) / 100
                            cash += amount - sell_commission  # 주식 판매로 얻은 금액 추가
                            position["Shares"] = shares - target_shares1
                            position["TotalBuyPrice"] -= amount

                            # 손익금
                            profit = amount - (position["EntryPrice"] * target_shares1) - sell_commission
                            position["Profit"] += profit

                            # 매도 기록 추가
                            trade_history.append({
                                "Type":"SELL",
                                "Price": row["Close"],
                                "Shares": target_shares1,
                                "Commission": sell_commission,
                                "EntryPrice": position["EntryPrice"],
                                "Profit": profit
                            })
                        
                        # 3/4 지정가 매도
                        target_price2 = position["EntryPrice"] * 1.1 # + 수수료 고려하여 위에서 팔 경우 코딩 수정 필요
                        target_shares2 = shares - target_shares1

                        if target_shares2 > 0 and row["Close"] > target_price2:
                            amount = target_price2 * target_shares2
                            sell_commission = math.floor(amount * self.commission * 100) / 100
                            cash += amount - sell_commission  # 주식 판매로 얻은 금액 추가
                            position["Shares"] = position["Shares"] - target_shares2
                            position["TotalBuyPrice"] -= amount

                            # 손익금
                            profit = amount - (position["EntryPrice"] * target_shares2) - sell_commission
                            position["Profit"] +=profit

                            # 매도 기록 추가
                            trade_history.append({
                                "Type":"SELL",
                                "Price": target_price2,
                                "Shares": target_shares2,
                                "Commission": sell_commission,
                                "EntryPrice": position["EntryPrice"],
                                "Profit": profit
                            })
                        
                        # 매수 체크
                        progress_per = position["TotalBuyPrice"] / position["AvailableBuyCash"] * 100
                        one_buy_shares = math.floor(position["OneBuyCash"] / row["Close"])

                        if progress_per < 100: 
                            if 50 > progress_per: # 전반전
                                # LOC 평단매수
                                buy_shares1 = round(one_buy_shares / 2)

                                if row["Close"] < position["EntryPrice"]:
                                    amount = row["Close"] * buy_shares1
                                    buy_commission = math.floor(amount * self.commission * 100) / 100
                                    cash -= amount + buy_commission # 주식 구입으로 사용된 금액 차감
                                    position["EntryPrice"] = self.get_entry_price(position["EntryPrice"], position["Shares"], row["Close"], buy_shares1)
                                    position["Shares"] += buy_shares1
                                    position["TotalBuyPrice"] += amount
                                    
                                    # 매수 기록 추가
                                    trade_history.append({
                                        "Type":"BUY",
                                        "Price": row["Close"],
                                        "Shares": buy_shares1,
                                        "Commission": buy_commission,
                                        "EntryPrice": position["EntryPrice"]
                                    })

                                # LOC (10 - T/2 * (40/분할수))%  매수
                                buy_shares2 = one_buy_shares - buy_shares1
                                buy_per = 10 - t/2 * (40/self.divisions)
                                buy_per = round(target_per1, 1)
                                buy_price = position["EntryPrice"] * (1 + (buy_per/100)) # + 수수료 고려하여 위에서 팔 경우 코딩 수정 필요
                                
                                if row["Close"] < buy_price:
                                    amount = row["Close"] * buy_shares2
                                    buy_commission = math.floor(amount * self.commission * 100) / 100
                                    cash -= amount + buy_commission # 주식 구입으로 사용된 금액 차감
                                    position["EntryPrice"] = self.get_entry_price(position["EntryPrice"], position["Shares"], row["Close"], buy_shares2)
                                    position["Shares"] += buy_shares2
                                    position["TotalBuyPrice"] += amount

                                    # 매수 기록 추가
                                    trade_history.append({
                                        "Type":"BUY",
                                        "Price": row["Close"],
                                        "Shares": buy_shares2,
                                        "Commission": buy_commission,
                                        "EntryPrice": position["EntryPrice"]
                                    })
                            else: # 후반전
                                buy_per = 10 - t/2 * (40/self.divisions)
                                buy_per = round(target_per1, 1)
                                buy_price = position["EntryPrice"] * (1 + (buy_per/100)) # + 수수료 고려하여 위에서 팔 경우 코딩 수정 필요

                                if row["Close"] < buy_price:
                                    amount = row["Close"] * one_buy_shares
                                    buy_commission = math.floor(amount * self.commission * 100) / 100
                                    cash -= amount + buy_commission # 주식 구입으로 사용된 금액 차감
                                    position["EntryPrice"] = self.get_entry_price(position["EntryPrice"], position["Shares"], row["Close"], one_buy_shares)
                                    position["Shares"] += one_buy_shares
                                    position["TotalBuyPrice"] += amount
                                    
                                    # 매수 기록 추가
                                    trade_history.append({
                                        "Type":"BUY",
                                        "Price": row["Close"],
                                        "Shares": one_buy_shares,
                                        "Commission": buy_commission,
                                        "EntryPrice": position["EntryPrice"]
                                    })

                    if position["Shares"] == 0:
                        stock.at[index, "End"] = target_price2
                        position = None # 포지션 해제

            elif row["Rsi"] < self.standard_rsi and position is None and cash > 0: # 신규진입

                # if (self.is_ma_cut and row["Close"] > row["MA200"]) or not self.is_ma_cut: 
                if (self.is_ma_cut and row["MA20"] > row["MA200"]) or not self.is_ma_cut: 
                # if (self.is_ma_cut and row["Macd"] > row["MacdSignal"]) or not self.is_ma_cut: 

                    # 한번에 매수 가능한 현금
                    if self.is_reinvest :
                        available_buy_cash = cash # 수익금 재투자
                    else :
                        available_buy_cash = cash if cash < self.initial_capital else self.initial_capital # 원금안에서만 매수

                    # 1회 매수금액 
                    one_buy_cash = math.floor(available_buy_cash / self.divisions * 100) / 100

                    shares = one_buy_cash // row["Close"]  
                    amount = row["Close"] * shares
                    buy_commission = math.floor(amount * self.commission * 100) / 100
                    cash -= amount + buy_commission # 주식 구입으로 사용된 금액 차감
                    position = {
                        "StartDate": index,
                        "EntryDate": index, 
                        "EntryPrice": row["Close"],
                        "Shares": shares,
                        "OneBuyCash": one_buy_cash,
                        "TotalBuyPrice": amount,
                        "AvailableBuyCash": available_buy_cash,
                        "Profit": 0
                    }

                    stock.at[index, "Start"] = row["Close"]

                    # 매수 기록 추가
                    trade_history.append({
                        "Type":"BUY",
                        "Price": row["Close"],
                        "Shares": shares,
                        "Commission": buy_commission,
                        "EntryPrice": position["EntryPrice"]
                    })
            
            stock.at[index, "Cash"] = cash
            value = (position["Shares"] * row["Close"]) if position is not None else 0 # 보유하는 주식이 있다면 보유주식수 * 종가
            value += cash
            stock.at[index, "Value"] = value
            stock.at[index, "EntryPrice"] = position["EntryPrice"] if position is not None else np.nan
            stock.at[index, "EntryShares"] = position["Shares"] if position is not None else np.nan
            stock.at[index, "ProgressPer"] = (position["TotalBuyPrice"] / position["AvailableBuyCash"] * 100) if position is not None else 0

            
            # 전날 100%가 아니고 당일 100%가 되면 원금소진 +1
            if stock.at[index, "ProgressPer"] >= 100 and stock.at[stock.index[stock.index.get_loc(index)-1], "ProgressPer"] < 100:
                exhaust_count += 1
                stock.at[index, "Exhaust"] = position["EntryPrice"]

            # MDD
            if value > peek_value:
                peek_value = value
                drawdown = 0
            else:
                drawdown = (peek_value - value) / peek_value * 100
                max_drawdown = max(max_drawdown, drawdown)
            stock.at[index, "Drawdown"] = 0 - drawdown


        # trade_history를 DataFrame으로 변환
        trade_df = pd.DataFrame(trade_history)

        #백테스팅 결과
        self.result = ibr.IbBacktestResult(
            start = stock.index[0],
            end = stock.index[-1],
            duration = len(stock),
            initial_capital = self.initial_capital,
            cash = cash,
            balance_status = stock.iloc[-1]["Value"],
            max_drawdown = max_drawdown,
            total_profit = trade_df[trade_df["Profit"] > 0]["Profit"].sum(),
            total_loss = trade_df[trade_df["Profit"] < 0]["Profit"].sum(),
            win_count = len(trade_df[trade_df["Profit"] > 0]),
            lose_count = len(trade_df[trade_df["Profit"] <= 0]),
        )

        self.result.set_quarter_count(quarter_count)
        self.result.set_exhaust_count(exhaust_count)
        self.result.set_ma_cut_count(ma_cut_count)

        return stock, trade_df
    
    """ 
    평단가 계산
        ((보유 평단가 * 보유수량) + (신규매수단가 * 신규매수수량)) / (보유수량 + 신규매수수량)
    """
    def get_entry_price(self, entry_price, entry_shares, buy_price, buy_shares):
        new_entry_price = ((entry_price * entry_shares) + (buy_price * buy_shares)) / (entry_shares + buy_shares)
        return round(new_entry_price, 8)
    
    # 차트 그리기 함수
    def plot_trades_candlestick(self):

        standard_rsi_line = pd.Series(self.standard_rsi, index=self.stock.index)

        apds = [ 
            # 평단가 라인
            mpf.make_addplot(self.stock["EntryPrice"], type='line'),
            mpf.make_addplot(self.stock["EntryPrice"], type='line'),
            mpf.make_addplot(self.stock["Start"], type='scatter'),
            mpf.make_addplot(self.stock["End"], type='scatter'),
            # 진행률
            mpf.make_addplot(self.stock["ProgressPer"], ylabel='Persent', type='line', panel=1),
            # RSI
            mpf.make_addplot(self.stock["Rsi"], type="line", ylabel='RSI', panel=2),
            mpf.make_addplot(standard_rsi_line, type="line", ylabel='RSI Line', panel=2),
            # MACD
            # mpf.make_addplot(self.stock["Macd"], type="line", color='darkorange', ylabel='MACD', panel=4),
            # mpf.make_addplot(self.stock["MacdSignal"], type="line", color='purple', ylabel='Signal', panel=4),
            # 자산가치
            mpf.make_addplot(self.stock["Value"], type='line', ylabel='Value', color='red', panel=3),
            mpf.make_addplot(self.stock["Drawdown"], type='line', ylabel='MDD', panel=3),
        ]

        if "Quarter" in self.stock:
            apds.append(mpf.make_addplot(self.stock["Quarter"], type='scatter', marker='v'))
        if "Exhaust" in self.stock:
            apds.append(mpf.make_addplot(self.stock["Exhaust"], type='scatter', marker='v'))

        # Plot the candlestick chart
        mpf.plot(self.stock, title="Back Testing", type='candle', style="yahoo", addplot=apds, mav=(20, 200), volume=False, figscale=1.3, ) # panel_ratios=(5,1,1,2)
    
    # 백테스팅 결과 가져오기
    def get_result(self):
        return self.result