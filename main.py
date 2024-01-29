import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf


# 보조 지표 세팅 및 진입 시그널 생성
def generate_signals(data):
    # 이동평균
    data["MA20"] = calculate_moving_average(data["Close"], window=20)
    # 볼린저밴드
    data["UpperLine"] = data["MA20"] + 2 * data["Close"].rolling(20).std()
    data["LowerLine"] = data["MA20"] + 2 * data["Close"].rolling(20).std()
    # RSI
    data = calculate_rsi(data)
    # 양봉 or 음봉
    data["Change"] = data["Close"] - data["Open"]
    data["IsUp"] = np.where(data["Change"] > 0, True, False)
    # 진입 시그널
    data["Signal"] = False
    entry_low = None
    for index, row in data.iterrows():
        if row["IsUp"] and entry_low is None:
            entry_low = row["Low"]
        if row["IsUp"] and entry_low is not None: # 양봉이면서
            #if row["rsi"] > 60 : # 
                if row["Close"] >= entry_low * 1.10:  # 종가가 저가대비 10% 이상 상승한 경우
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
def calculate_moving_average(df, window=20):
    return df.rolling(window=window).mean()

def calculate_rsi(df, period=14):

    # 전일 대비 변동 평균
    df['change'] = df['Close'].diff()

    # 상승한 가격과 하락한 가격
    df['up'] = df['change'].apply(lambda x: x if x > 0 else 0)
    df['down'] = df['change'].apply(lambda x: -x if x < 0 else 0)

    # 상승 평균과 하락 평균
    df['avg_up'] = df['up'].ewm(alpha=1/period).mean()
    df['avg_down'] = df['down'].ewm(alpha=1/period).mean()

    # 상대강도지수(RSI) 계산
    df['rs'] = df['avg_up'] / df['avg_down']
    df['rsi'] = 100 - (100 / (1 + df['rs']))

    return df

# 백테스팅 함수
def backtest(data) :
    # 전략
    # 진입 : 양봉전환하면서 저가 대비 10%이상 상승했을 때 종가로 진입
    # 추가 매수 : 저가부터 진입한 종가까지 5분할 하여 매수
    # 매도 : 평단가 대비 5분할의 1칸 가격 위에 매도
    # 손절 : 마지막 5분할선에서 -2%로 내려갈 시 매도

    initial_capital = 10000  # 초기 자본
    cash = initial_capital # 보유 현금

    available_buy_cash = 0 # 한번 매수에 사용가능한 금액

    position = None
    
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
            # 매수 기록 추가
            data.at[index, "BuyPrice"] = row["Close"]
            data.at[index, "BuyShares"] = shares
            cash -= shares * row["Close"]  # 주식 구입으로 사용된 금액 차감
        elif position is not None:  # 이미 포지션을 가지고 있는 경우
            target_price = position["EntryPrice"] + position["OneBlockPrice"]
            if row["High"] >= target_price: # 목표 매도가에 매도
                cash += position["Shares"] * target_price  # 주식 판매로 얻은 금액 추가
                data.at[index, "Cash"] = cash
                # 매도 기록 추가
                data.at[index, "SellPrice"] = target_price
                data.at[index, "SellShares"] = position["Shares"]
                data.at[index, "Profit"] = (target_price * position["Shares"]) - position["TotalBuyPrice"]
                position = None  # 포지션 해제
                continue
            if position["IsAdditionalBuy1"] is False and row["Low"] <= position["AdditionalBuy1"]: # 1차 매수
                position, buy_price = addBuy(position, position["AdditionalBuy1"])
                position["IsAdditionalBuy1"] = True
                # 매수 기록 추가
                data.at[index, "BuyPrice"] = position["AdditionalBuy1"]
                data.at[index, "BuyShares"] = position["AvailableBuyCash"] // position["AdditionalBuy1"]
                cash -= buy_price # 주식 구입으로 사용된 금액 차감
            if position["IsAdditionalBuy2"] is False and row["Low"] <= position["AdditionalBuy2"]: # 2차 매수
                position, buy_price = addBuy(position, position["AdditionalBuy2"])
                position["IsAdditionalBuy2"] = True
                # 매수 기록 추가
                data.at[index, "BuyPrice"] = position["AdditionalBuy2"]
                data.at[index, "BuyShares"] = position["AvailableBuyCash"] // position["AdditionalBuy2"]
                cash -= buy_price # 주식 구입으로 사용된 금액 차감
            if position["IsAdditionalBuy3"] is False and row["Low"] <= position["AdditionalBuy3"]: # 3차 매수
                position, buy_price = addBuy(position, position["AdditionalBuy3"])
                position["IsAdditionalBuy3"] = True
                # 매수 기록 추가
                data.at[index, "BuyPrice"] = position["AdditionalBuy3"]
                data.at[index, "BuyShares"] = position["AvailableBuyCash"] // position["AdditionalBuy3"]
                cash -= buy_price # 주식 구입으로 사용된 금액 차감
            if position["IsAdditionalBuy4"] is False and row["Low"] <= position["AdditionalBuy4"]: # 4차 매수
                position, buy_price = addBuy(position, position["AdditionalBuy4"])
                position["IsAdditionalBuy4"] = True
                # 매수 기록 추가
                data.at[index, "BuyPrice"] = position["AdditionalBuy4"]
                data.at[index, "BuyShares"] = position["AvailableBuyCash"] // position["AdditionalBuy4"]
                cash -= buy_price # 주식 구입으로 사용된 금액 차감
            if row["Low"] <= position["StopLoss"]: # 손절
                cash += position["Shares"] * position["StopLoss"]  # 주식 판매로 얻은 금액 추가
                # 매도 기록 추가
                data.at[index, "SellPrice"] = position["StopLoss"]
                data.at[index, "SellShares"] = position["Shares"]
                data.at[index, "Profit"] = (position["StopLoss"] * position["Shares"]) - position["TotalBuyPrice"]
                position = None  # 포지션 해제
            
        data.at[index, "Cash"] = cash

    if position is not None:  # 데이터의 끝에 도달했는데 아직 포지션이 열려 있는 경우
        cash += position["Shares"] * data.iloc[-1]["Close"]  # 보유 주식을 현금화
        data.at[index, "Cash"] = cash
        # 매도 기록 추가
        data.at[index, "SellPrice"] = data.iloc[-1]["Close"]
        data.at[index, "SellShares"] = position["Shares"]
        data.at[index, "Profit"] = (data.iloc[-1]["Close"] * position["Shares"]) - position["TotalBuyPrice"]

    # 백테스팅 결과
    result = {}
    result["Start"] = {"label":"시작일", "value":data.index[0]}
    result["End"] = {"label":"종료일", "value":data.index[-1]}
    result["Duration"] = {"label":"총 거래일", "value":len(data)}
    result["InitialCash"] = {"label":"투자원금", "value":initial_capital}
    result["Cash"] = {"label":"남은 현금", "value":cash}
    result["Return"] = {"label":"실현손익금", "value":cash - initial_capital}
    result["ReturnRatio"] = {"label":"누적수익률(%)", "value":(result["Return"]["value"] / initial_capital) * 100}
    result["TotalProfit"] = {"label":"실현 수익금의 합", "value":data[data["Profit"] > 0]["Profit"].sum()}
    result["TotalLoss"] = {"label":"실현 손익금의 합", "value":data[data["Profit"] < 0]["Profit"].sum()}
    result["ProfitLossRatio"] = {"label":"손익비", "value":result["TotalProfit"]["value"] / result["TotalLoss"]["value"]}
    result["WinCount"] = {"label":"실현 수익 횟수", "value":len(data[data["Profit"] > 0])}
    result["LoseCount"] = {"label":"실현 손익 횟수", "value":len(data[data["Profit"] <= 0])}
    result["WinRate"] = {"label":"매매 성공률(%)", "value":result["WinCount"]["value"] / (result["WinCount"]["value"] + result["LoseCount"]["value"]) * 100}
    result["AvgDailyReturnRatio"] = {"label":"일평균수익률(%)", "value":result["ReturnRatio"]["value"] / result["Duration"]["value"]}
    result["AvgAnnualReturnRatio"] = {"label":"연평균수익률(%)", "value":result["AvgDailyReturnRatio"]["value"] * 247}
    result["AvgMonthlyReturnRatio"] = {"label":"월평균수익률(%)", "value":result["AvgAnnualReturnRatio"]["value"] / 12}

    return data, result

# 추가매수 처리 함수
def addBuy(position, additional_buy_price):
    additional_shares = position["AvailableBuyCash"] // additional_buy_price  # 추가 구매할 주식 수 계산
    position["Shares"] += additional_shares  # 보유 주식 수 업데이트
    position["TotalBuyPrice"] += additional_buy_price * additional_shares # 총 매입가격
    position["EntryPrice"] = position["TotalBuyPrice"] / position["Shares"]
    return position, (additional_buy_price * additional_shares) # return position, 매입가격

# 차트 그리기 함수
def plot_trades_candlestick(data):
    # 색상 지정
    marketcolors = mpf.make_marketcolors(up='red', down='blue')

    # 스타일 만들기
    style = mpf.make_mpf_style(marketcolors=marketcolors)
    
    apds = [ 
         mpf.make_addplot(data["BuyPrice"], type='scatter', marker='^', markersize=80),
         mpf.make_addplot(data["SellPrice"], type='scatter', marker='v', markersize=80),
         mpf.make_addplot(data["UpperLine"]),
       ]

    # Plot the candlestick chart
    mpf.plot(data, type='candle', style=style, addplot=apds, mav=(200))

    # plt.plot(data['Cash'], color='blue', label='Cash')
    # plt.legend()
    # plt.show()

def print_result(result):
    print("백테스팅 결과:")
    for key, value in result.items():
        if isinstance(value['value'], float):
            print(f"{value['label']}: {value['value']:.2f}")
        else:
            print(f"{value['label']}: {value['value']}")

if __name__ == '__main__':
    # 주가 데이터 조회
    stock = yf.download("TQQQ", start="2020-01-01", end="2023-12-31")

    # 보조 지표 세팅
    data = generate_signals(stock)

    # 백테스팅
    data, result = backtest(data)

    # 결과 출력
    print_result(result)
    
    # print(data[data["Profit"].notna()])

    # 차트 출력
    plot_trades_candlestick(data)
