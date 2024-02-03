import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf
import strategy.secondary_indicator as si
import dao.backtest_result as br

class InfiniteBuy:
    
    def __init__(self, stock, initial_capital = 10000, commission=0.007, standard_rsi = 0, is_reinvest = True):
        self.stock = stock
        self.initial_capital = initial_capital # 초기자본
        self.commission = commission # 수수료
        self.standard_rsi = standard_rsi # 진입 기준 rsi (standard_rsi 높을 때 진입)
        self.is_reinvest = is_reinvest # 수익금 재투자 여부(False이면 매수최대금이 원금을 넘지 않음) 
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
                print("매수가즈아")