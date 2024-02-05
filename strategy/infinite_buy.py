import yfinance as yf
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf
import strategy.secondary_indicator as si
import dao.backtest_result as br

class InfiniteBuy:
    
    def __init__(self, stock, initial_capital = 10000, commission=0.007, divisions=40, standard_rsi = 0, is_reinvest = True):
        self.stock = stock
        self.initial_capital = initial_capital # 초기자본
        self.commission = commission # 수수료
        self.standard_rsi = standard_rsi # 진입 기준 rsi (standard_rsi 높을 때 진입)
        self.is_reinvest = is_reinvest # 수익금 재투자 여부(False이면 매수최대금이 원금을 넘지 않음) 
        self.divisions = divisions
        self.result = None

        self.generate_signals()

    def generate_signals(self):
        stock = self.stock

        # RSI
        stock["Rsi"] = si.rsi(stock["Close"])

        # MA 200
        stock["MA200"] = si.moving_average(stock["Close"], window=200)

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

                print(target_shares1)

                if row["Close"] > target_price1:
                    amount = row["Close"] * target_shares1
                    sell_commission = amount * self.commission
                    cash += amount - sell_commission  # 주식 판매로 얻은 금액 추가
                    # 매도 기록 추가
                    stock.at[index, "SellPrice"] = row["Close"]
                    stock.at[index, "SellShares"] = target_shares1
                    stock.at[index, "SellCommission"] = amount * self.commission
                    # stock.at[index, "Profit"] = 
                    position["Shares"] = shares - target_shares1
                
                # 3/4 지정가 매도
                target_price2 = position["EntryPrice"] * 1.1 # + 수수료 고려하여 위에서 팔 경우 코딩 수정 필요
                target_shares2 = shares - target_shares1

                if row["Close"] > target_price2:
                    amount = target_price2 * target_shares2
                    sell_commission = amount * self.commission
                    cash += amount - sell_commission  # 주식 판매로 얻은 금액 추가
                    # 매도 기록 추가
                    stock.at[index, "SellPrice"] = target_price2
                    stock.at[index, "SellShares"] = target_shares2
                    stock.at[index, "SellCommission"] = amount * self.commission
                    position["Shares"] = position["Shares"] - target_shares2
                
                
                # 매수 체크
                progress_per = position["TotalBuyPrice"] / position["AvailableBuyCash"] * 100
                one_buy_shares = math.floor(position["OneBuyCash"] / row["Close"])

                if 50 > progress_per: # 전반전
                    # LOC 평단매수
                    buy_shares1 = round(one_buy_shares / 2)

                    if row["Close"] < position["EntryPrice"]:
                        amount = row["Close"] * buy_shares1
                        buy_commission = amount * self.commission
                        position["Shares"] += buy_shares1
                        position["TotalBuyPrice"] += amount
                        position["BuyCommission"] += buy_commission
                        # TODO 평단가 계산
                        
                        # 매수 기록 추가
                        stock.at[index, "BuyPrice"] = row["Close"]
                        stock.at[index, "BuyShares"] = buy_shares1
                        stock.at[index, "BuyCommission"] = buy_commission
                        stock.at[index, "ProgressPer"] = position["TotalBuyPrice"] / position["AvailableBuyCash"] * 100
                        cash -= amount + buy_commission # 주식 구입으로 사용된 금액 차감

                    # LOC (10 - T/2 * (40/분할수))%  매수
                    buy_shares2 = one_buy_shares - buy_shares1
                    buy_per = 10 - t/2 * (40/self.divisions)
                    buy_per = round(target_per1, 1)
                    buy_price = position["EntryPrice"] * (1 + (buy_per/100)) # + 수수료 고려하여 위에서 팔 경우 코딩 수정 필요
                    
                    if row["Close"] < buy_price:
                        amount = row["Close"] * buy_shares2
                        buy_commission = amount * self.commission
                        position["Shares"] += buy_shares2
                        position["TotalBuyPrice"] += amount
                        position["BuyCommission"] += buy_commission
                        # TODO 평단가 계산
                        
                        # 매수 기록 추가
                        stock.at[index, "BuyPrice"] = row["Close"]
                        stock.at[index, "BuyShares"] = buy_shares2
                        stock.at[index, "BuyCommission"] = buy_commission
                        stock.at[index, "ProgressPer"] = position["TotalBuyPrice"] / position["AvailableBuyCash"] * 100
                        cash -= amount + buy_commission # 주식 구입으로 사용된 금액 차감
                else: # 후반전
                    buy_per = 10 - t/2 * (40/self.divisions)
                    buy_per = round(target_per1, 1)
                    buy_price = position["EntryPrice"] * (1 + (buy_per/100)) # + 수수료 고려하여 위에서 팔 경우 코딩 수정 필요

                    if row["Close"] < buy_price:
                        amount = row["Close"] * one_buy_shares
                        buy_commission = amount * self.commission
                        position["Shares"] += one_buy_shares
                        position["TotalBuyPrice"] += amount
                        position["BuyCommission"] += buy_commission
                        # TODO 평단가 계산
                        
                        # 매수 기록 추가
                        stock.at[index, "BuyPrice"] = row["Close"]
                        stock.at[index, "BuyShares"] = one_buy_shares
                        stock.at[index, "BuyCommission"] = buy_commission
                        stock.at[index, "ProgressPer"] = position["TotalBuyPrice"] / position["AvailableBuyCash"] * 100
                        cash -= amount + buy_commission # 주식 구입으로 사용된 금액 차감

                if position["Shares"] == 0:
                    position = None # 포지션 해제

            elif row["Rsi"] < self.standard_rsi and position is None and cash > 0: # 신규진입

                # 한번에 매수 가능한 현금
                if self.is_reinvest :
                    available_buy_cash = cash # 수익금 재투자
                else :
                    available_buy_cash = cash if cash < self.initial_capital else self.initial_capital # 원금안에서만 매수

                # 1회 매수금액 
                one_buy_cash = math.floor(available_buy_cash / self.divisions * 100) / 100

                shares = one_buy_cash // row["Close"]  
                amount = row["Close"] * shares
                buy_commission = amount * self.commission
                position = {
                    "StartDate": index,
                    "EntryDate": index, 
                    "EntryPrice": row["Close"],
                    "Shares": shares,
                    "OneBuyCash": one_buy_cash,
                    "TotalBuyPrice": amount,
                    "BuyCommission": buy_commission,
                    "AvailableBuyCash" : available_buy_cash
                }

                # 매수 기록 추가
                stock.at[index, "BuyPrice"] = row["Close"]
                stock.at[index, "BuyShares"] = shares
                stock.at[index, "BuyCommission"] = buy_commission
                stock.at[index, "ProgressPer"] = amount / available_buy_cash * 100
                cash -= amount + buy_commission # 주식 구입으로 사용된 금액 차감
            
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

        return stock
            