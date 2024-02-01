import yfinance as yf
import strategy.short_term_leverage as strategy_stl

# 미국 레버리지 ETF 단타
def short_term_leverage():
    # 주가 데이터 조회
    stock = yf.download("SOXL", start="2010-01-01")

    stl = strategy_stl.ShortTermLeverage(stock, initial_capital=1000, standard_rsi=40, target_division=10, standard_rate=1.065, is_reinvest=True)

    # 백테스팅
    stl.backtest()

    # 결과 출력
    result = stl.get_result()
    result.print()

    # 차트 출력
    # stl.plot_trades_candlestick()

if __name__ == '__main__':
    # 미국 레버리지 ETF 단타
    short_term_leverage()

