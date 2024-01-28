import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf
import matplotlib.dates as mdates


# 보조 지표 세팅 및 진입 시그널 생성
def generate_signals(data):
    # 이동평균
    data["MA20"] = calculate_moving_average(data["Close"], window=20)
    # 양봉 or 음봉
    data["Change"] = data["Close"] - data["Open"]
    data["IsUp"] = np.where(data["Change"] > 0, True, False)
    # 진입 시그널
    data["Signal"] = False
    data["OneBlockPrice"] = None # 5분할 중 한블록의 가격
    data["AdditionalBuy1"] = None # 첫번째 추가 매수 가격
    data["AdditionalBuy2"] = None # 두번째 추가 매수 가격
    data["AdditionalBuy3"] = None # 세번째 추가 매수 가격
    data["AdditionalBuy4"] = None # 네번째 추가 매수 사격
    data["StopLoss"] = None # 손절선
    entry_low = None
    for index, row in data.iterrows():
        if row["IsUp"] and entry_low is None:
            entry_low = row["Low"]
        if row["IsUp"] and entry_low is not None:
            if row["Close"] >= entry_low * 1.10:  # 종가가 10% 이상 상승한 경우
                data.at[index, "Signal"] = True
                one_block_price = (row["Close"] - entry_low) / 5
                data.at[index, "OneBlockPrice"] = one_block_price
                data.at[index, "AdditionalBuy1"] = row["Close"] - (one_block_price * 1)
                data.at[index, "AdditionalBuy2"] = row["Close"] - (one_block_price * 2)
                data.at[index, "AdditionalBuy3"] = row["Close"] - (one_block_price * 3)
                data.at[index, "AdditionalBuy4"] = row["Close"] - (one_block_price * 4)
                data.at[index, "StopLoss"] = data.at[index, "AdditionalBuy4"] * 0.98
        elif not row["IsUp"]:
            entry_low = None
    return data

# 이동평균 계산 함수
def calculate_moving_average(data, window=20):
    return data.rolling(window=window).mean()


# 백테스팅 함수
def backtest(data) :
    # 전략
    # 진입 : 양봉전환하면서 저가 대비 10%이상 상승했을 때 종가로 진입
    # 추가 매수 : 저가부터 진입한 종가까지 5분할 하여 매수
    # 매도 : 평단가 대비 5분할의 1칸 가격 위에 매도
    # 손절 : 마지막 5분할선에서 -2%로 내려갈 시 매도

    initial_capital = 10000  # 초기 자본
    cash = initial_capital

    available_buy_cash = 0 # 한번 매수에 사용가능한 금액

    position = None
    trades = []
    
    for index, row in data.iterrows():
        if row["Signal"] and position is None and cash > 0:  # 진입 신호가 발생하고 현금이 있는 경우
            available_buy_cash = cash / 5 # 한번에 매수 가능한 현금
            shares = available_buy_cash // row["Close"]  # 매수 가능한 주식 수 계산
            position = {
                "EntryDate": index, 
                "EntryPrice": row["Close"], 
                "Shares": shares,
                "TotalBuyPrice": row["Close"] * shares,
                "AvailableBuyCash" : available_buy_cash,
                "OneBlockPrice": row["OneBlockPrice"],
                "AdditionalBuy1": row["AdditionalBuy1"],
                "AdditionalBuy2": row["AdditionalBuy2"],
                "AdditionalBuy3": row["AdditionalBuy3"],
                "AdditionalBuy4": row["AdditionalBuy4"],
                "IsAdditionalBuy1": False,
                "IsAdditionalBuy2": False,
                "IsAdditionalBuy3": False,
                "IsAdditionalBuy4": False,
                "StopLoss": row["StopLoss"]
            }
            trades.append({
                "Type": "Buy",
                "Date": index,
                "Price": row["Close"],
                "Shares": shares
            })
            cash -= shares * row["Close"]  # 주식 구입으로 사용된 금액 차감
        elif position is not None:  # 이미 포지션을 가지고 있는 경우
            target_price = position["EntryPrice"] + position["OneBlockPrice"]
            if row["High"] >= target_price: # 목표 매도가에 매도
                cash += position["Shares"] * target_price  # 주식 판매로 얻은 금액 추가
                trades.append({
                    "Type": "Sell",
                    "Date": index,
                    "Price": target_price,
                    "Shares": position["Shares"]
                })
                position = None  # 포지션 해제
                continue
            if position["IsAdditionalBuy1"] is False and row["Low"] <= position["AdditionalBuy1"]: # 1차 매수
                position, buy_price = addBuy(position, position["AdditionalBuy1"])
                position["IsAdditionalBuy1"] = True
                trades.append({
                    "Type": "Buy",
                    "Date": index,
                    "Price": position["AdditionalBuy1"],
                    "Shares": position["AvailableBuyCash"] // position["AdditionalBuy1"]
                })
                cash -= buy_price # 주식 구입으로 사용된 금액 차감
            if position["IsAdditionalBuy2"] is False and row["Low"] <= position["AdditionalBuy2"]: # 2차 매수
                position, buy_price = addBuy(position, position["AdditionalBuy2"])
                trades.append({
                    "Type": "Buy",
                    "Date": index,
                    "Price": position["AdditionalBuy2"],
                    "Shares": position["AvailableBuyCash"] // position["AdditionalBuy2"]
                })
                position["IsAdditionalBuy2"] = True
                cash -= buy_price # 주식 구입으로 사용된 금액 차감
            if position["IsAdditionalBuy3"] is False and row["Low"] <= position["AdditionalBuy3"]: # 3차 매수
                trades.append({
                    "Type": "Buy",
                    "Date": index,
                    "Price": position["AdditionalBuy3"],
                    "Shares": position["AvailableBuyCash"] // position["AdditionalBuy3"]
                })
                position, buy_price = addBuy(position, position["AdditionalBuy3"])
                position["IsAdditionalBuy3"] = True
                cash -= buy_price # 주식 구입으로 사용된 금액 차감
            if position["IsAdditionalBuy4"] is False and row["Low"] <= position["AdditionalBuy4"]: # 4차 매수
                position, buy_price = addBuy(position, position["AdditionalBuy4"])
                trades.append({
                    "Type": "Buy",
                    "Date": index,
                    "Price": position["AdditionalBuy4"],
                    "Shares": position["AvailableBuyCash"] // position["AdditionalBuy4"]
                })
                position["IsAdditionalBuy4"] = True
                cash -= buy_price # 주식 구입으로 사용된 금액 차감
            if row["Low"] <= position["StopLoss"]: # 손절
                cash += position["Shares"] * position["StopLoss"]  # 주식 판매로 얻은 금액 추가
                trades.append({
                    "Type": "Sell",
                    "Date": index,
                    "Price": position["StopLoss"],
                    "Shares": position["Shares"]
                })
                position = None  # 포지션 해제

    if position is not None:  # 데이터의 끝에 도달했는데 아직 포지션이 열려 있는 경우
        cash += position["Shares"] * data.iloc[-1]["Close"]  # 보유 주식을 현금화
        trades.append({
            "Type": "Sell",
            "Date": data.index[-1],
            "Price": data.iloc[-1]["Close"],
            "Shares": position["Shares"]
        })
 
    return cash, pd.DataFrame(trades)

# 추가매수 처리 함수
def addBuy(position, additional_buy_price):
    additional_shares = position["AvailableBuyCash"] // additional_buy_price  # 추가 구매할 주식 수 계산
    position["Shares"] += additional_shares  # 보유 주식 수 업데이트
    position["TotalBuyPrice"] += additional_buy_price * additional_shares # 총 매입가격
    position["EntryPrice"] = position["TotalBuyPrice"] / position["Shares"]
    return position, (additional_buy_price * additional_shares) # return position, 매입가격

# 차트 그리기 함수
def plot_trades_candlestick(stock_data, trades):
    df = stock_data[['Open', 'High', 'Low', 'Close', 'Volume']]
    df.index.name = 'Date'

    # 캔들 차트의 크기와 제목
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_title('Candlestick Chart with Trades')

    # 색상 지정
    marketcolors = mpf.make_marketcolors(up='red', down='blue')

    # 스타일 만들기
    style = mpf.make_mpf_style(marketcolors=marketcolors)
    
    # Plot the candlestick chart
    mpf.plot(df, type='candle', style=style)

    # Plot the buy and sell points
    for trade in trades.itertuples():
        if trade.Type == 'Buy':
            plt.scatter(trade.Date, trade.Price, marker='^', color='green', label='Buy')
        elif trade.Type == 'Sell':
            plt.scatter(trade.Date, trade.Price, marker='v', color='red', label='Sell')

    plt.legend()
    plt.show()

if __name__ == '__main__':
    # 주가 데이터 조회
    stock = yf.download("TQQQ", start="2023-10-27", end="2023-12-25")

    # 보조 지표 세팅
    data = generate_signals(stock)

    # 백테스팅
    portfolio_value, trades = backtest(data)

    # 결과 출력
    print("최종 포트폴리오 가치:", portfolio_value)
    print("거래 내역:")
    print(trades)

    plot_trades_candlestick(data, trades)
