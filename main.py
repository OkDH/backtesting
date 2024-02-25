import yfinance as yf
import strategy.short_term_leverage as strategy_stl
import strategy.infinite_buy_v1 as ib_v1
import strategy.infinite_buy as ib_v2_2
import strategy.infinite_buy_slowly as ib_slowly
import pandas as pd

# 무한매수 백테스팅
def infinite_buy():
    stock = yf.download("LABU", start="2015-06-01")


    # v1
    # ib = ib_v1.InfiniteBuy(stock, initial_capital=10000, commission=0.007, standard_rsi=100, is_quarter_mode=False, is_ma_cut=True, is_reinvest=False)

    # v2.2
    # ib = ib_v2_2.InfiniteBuy(stock, initial_capital=100000, commission=0.007, standard_rsi=55, is_quarter_mode=True, is_ma_cut=True, is_reinvest=True)

    # slowly
    ib = ib_slowly.InfiniteBuy(stock, initial_capital=100000, commission=0.007, standard_rsi=100, is_quarter_mode=True, is_ma_cut=False, is_reinvest=True)


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

def infinite_all():
    stock = yf.download("SOXL", start="2000-01-01")

    initial_capital = 100000
    commission=0.007
    is_quarter_mode = False
    is_ma_cut = False
    is_reinvest = False

    result_all_list = []

    for i in range(100, 25, -5):

        print(f"RSI : {i}")

        # v1
        ib = ib_v1.InfiniteBuy(stock, initial_capital=initial_capital, commission=commission, standard_rsi=i, is_quarter_mode=is_quarter_mode, is_ma_cut=is_ma_cut, is_reinvest=is_reinvest)
        ib.backtest()
        result_all_list.append(export_result(ib.get_result(), "v1", i))

        # v2.2
        ib = ib_v2_2.InfiniteBuy(stock, initial_capital=initial_capital, commission=commission, standard_rsi=i, is_quarter_mode=is_quarter_mode, is_ma_cut=is_ma_cut, is_reinvest=is_reinvest)
        ib.backtest()
        result_all_list.append(export_result(ib.get_result(), "v2.2", i))

        # slowly
        ib = ib_slowly.InfiniteBuy(stock, initial_capital=initial_capital, commission=commission, standard_rsi=i, is_quarter_mode=is_quarter_mode, is_ma_cut=is_ma_cut, is_reinvest=is_reinvest)
        ib.backtest()
        result_all_list.append(export_result(ib.get_result(), "slowly", i))
    
    # 리스트를 데이터프레임으로 변환
    result_df = pd.DataFrame(result_all_list)

    # print(result_df)

    # CSV 저장
    result_df.to_csv('result_data.csv')


# Result 결과 넣기
def export_result(result, version, rsi):

    return {
        'version' : version,
        'rsi' : rsi,
        'start' : result.get_start(),
        'end' : result.get_end(),
        'duration' : result.get_duration(),
        'initial_capital' : result.get_initial_capital(),
        'cash' : result.get_cash(),
        'balance_status' : result.get_balance_status(),
        'profit' : result.get_profit(),
        'profit_ratio' : result.get_profit_ratio(),
        'max_drawdown' : result.get_max_drawdown(),
        'total_profit' : result.get_total_profit(),
        'total_loss' : result.get_total_loss(),
        'profit_loss_ratio' : result.get_profit_loss_ratio(),
        'win_count' : result.get_win_count(),
        'lose_count' : result.get_lose_count(),
        'win_rate' : result.get_win_rate(),
        'exhaust_count' : result.get_exhaust_count(),
        'quarter_count' : result.get_quarter_count(),
        'ma_cut_count' : result.get_ma_cut_count(),
        'avg_daily_profit_ratio' : result.get_avg_daily_profit_ratio(),
        'avg_monthly_profit_ratio' : result.get_avg_monthly_profit_ratio(),
        'avg_annual_profit_ratio' : result.get_avg_annual_profit_ratio(),
    }


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
    # infinite_buy()

    # 무한매수 여러 옵션들 비교 
    infinite_all()