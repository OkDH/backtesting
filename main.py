import yfinance as yf
import strategy.short_term_leverage as strategy_stl
import strategy.infinite_buy_v1 as ib_v1
import strategy.infinite_buy as ib_v2_2
import strategy.infinite_buy_slowly as ib_slowly
import pandas as pd

# 무한매수 백테스팅
def infinite_buy():
    stock = yf.download("TQQQ", start="2015-06-01")

    # v1
    ib = ib_v1.InfiniteBuy(stock, initial_capital=10000, commission=0.007, standard_rsi=100, is_quarter_mode=False, is_ma_cut=True, is_reinvest=False)

    # v2.2
    # ib = ib_v2_2.InfiniteBuy(stock, initial_capital=100000, commission=0.007, standard_rsi=55, is_quarter_mode=True, is_ma_cut=True, is_reinvest=True)

    # slowly
    # ib = ib_slowly.InfiniteBuy(stock, initial_capital=100000, commission=0.007, standard_rsi=100, is_quarter_mode=True, is_ma_cut=True, is_reinvest=True)


    # 백테스팅
    data, trade_df = ib.backtest()

    d = data[["Close", "Rsi", "EntryPrice", "EntryShares", "ProgressPer", "Value", "Cash"]]

    pd.set_option("display.max_rows", 1500)
    # print(d)

    # print(trade_df)

    # 결과 출력
    result = ib.get_result()
    result.print()

    # 차트 출력
    # ib.plot_trades_candlestick()

# 미국 레버리지 ETF 단타
def short_term_leverage():
    # 주가 데이터 조회
    stock = yf.download("SOXL", start="2010-01-01")

    stl = strategy_stl.ShortTermLeverage(stock, initial_capital=1000, commission=0.007, standard_rsi=0, target_division=1, standard_rate=1.07, is_reinvest=False)

    # 백테스팅
    data = stl.backtest()
    d = data[["BuyPrice","BuyShares","BuyCommission","TargetPrice", "SellPrice","SellShares","SellCommission","Profit", "Value"]]

    pd.set_option("display.max_rows", 500)
    print(d)

    # 결과 출력
    result = stl.get_result()
    result.print()

    # 차트 출력
    stl.plot_trades_candlestick()

if __name__ == '__main__':
    # 미국 레버리지 ETF 단타
    # short_term_leverage()

    # 무한매수
    infinite_buy()