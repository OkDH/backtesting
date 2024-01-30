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
    data["LowerLine"] = data["MA20"] - 2 * data["Close"].rolling(20).std()

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
            if row["Rsi"] > 40: 
            # if row["Close"] > row["LowerLine"]:
                if row["Close"] >= entry_low * 1.065:  # 종가가 저가대비 n% 이상 상승한 경우
                    data.at[index, "Signal"] = True
                    one_block_price = (row["Close"] - entry_low) / 10 # n분할
                    data.at[index, "OneBlockPrice"] = one_block_price
                    data.at[index, "StopLoss"] = (row["Close"] - (one_block_price * 1))
        elif not row["IsUp"]:
            entry_low = None
    return data

# 이동평균 계산 함수
def calculate_moving_average(df, window=20):
    return df.rolling(window=window).mean()

# RSI 계산 함수
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
    df['Rsi'] = 100 - (100 / (1 + df['rs']))

    return df

# 백테스팅 함수
def backtest(data) :
    # 전략
    # 진입 : 양봉전환하면서 저가 대비 10%이상 상승했을 때 종가로 진입
    # 매도 : 평단가 대비 5분할의 1칸 가격 위에 매도
    # 손절 : 평단 -2%로 내려갈 시 매도

    initial_capital = 10000  # 초기 자본
    cash = initial_capital # 보유 현금

    available_buy_cash = 0 # 한번 매수에 사용가능한 금액

    # MDD
    peek_value = 0
    drawdown = 0 
    max_drawdown = 0

    position = None
    
    for index, row in data.iterrows():
        
        if position is not None:  # 이미 포지션을 가지고 있는 경우
            # 목표가
            target_price = position["EntryPrice"] + position["OneBlockPrice"]
            # target_price = position["EntryPrice"] * 1.01
            # 수익 실현
            if row["Open"] >= target_price:
                cash += position["Shares"] * row["Open"]  # 주식 판매로 얻은 금액 추가
                # 매도 기록 추가
                data.at[index, "SellPrice"] = row["Open"]
                data.at[index, "SellShares"] = position["Shares"]
                data.at[index, "Profit"] = (row["Open"] * position["Shares"]) - position["TotalBuyPrice"]
                position = None  # 포지션 해제
            elif row["High"] >= target_price: # 목표 매도가에 매도
                cash += position["Shares"] * target_price  # 주식 판매로 얻은 금액 추가
                # 매도 기록 추가
                data.at[index, "SellPrice"] = target_price
                data.at[index, "SellShares"] = position["Shares"]
                data.at[index, "Profit"] = (target_price * position["Shares"]) - position["TotalBuyPrice"]
                position = None  # 포지션 해제
            elif row["Open"] <= position["StopLoss"]: # 장초반 손절
                cash += position["Shares"] * row["Open"]  # 주식 판매로 얻은 금액 추가
                # 매도 기록 추가
                data.at[index, "SellPrice"] = row["Open"]
                data.at[index, "SellShares"] = position["Shares"]
                data.at[index, "Profit"] = (row["Open"] * position["Shares"]) - position["TotalBuyPrice"]
                position = None  # 포지션 해제
            elif row["Low"] <= position["StopLoss"]: # 손절
                cash += position["Shares"] * position["StopLoss"]  # 주식 판매로 얻은 금액 추가
                # 매도 기록 추가
                data.at[index, "SellPrice"] = position["StopLoss"]
                data.at[index, "SellShares"] = position["Shares"]
                data.at[index, "Profit"] = (position["StopLoss"] * position["Shares"]) - position["TotalBuyPrice"]
                position = None  # 포지션 해제

        if row["Signal"] and position is None and cash > 0:  # 진입 신호가 발생하고 현금이 있는 경우

            # 한번에 매수 가능한 현금
            available_buy_cash = cash if cash < initial_capital else initial_capital # 원금안에서만 매수
            # available_buy_cash = cash # 수익금 재투자

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
            data.at[index, "BuyPrice"] = row["Close"]
            data.at[index, "BuyShares"] = shares
            cash -= shares * row["Close"]  # 주식 구입으로 사용된 금액 차감
            
        data.at[index, "Cash"] = cash
        value = (position["Shares"] * row["Close"]) if position is not None else 0 # 보유하는 주식이 있다면 보유주식수 * 종가
        value += cash
        data.at[index, "Value"] = value

        # MDD
        if value > peek_value:
            peek_value = value
            drawdown = 0
        else:
            drawdown = (peek_value - value) / peek_value * 100
            max_drawdown = max(max_drawdown, drawdown)
        data.at[index, "Drawdown"] = 0 - drawdown
        
    # if position is not None:  # 데이터의 끝에 도달했는데 아직 포지션이 열려 있는 경우
    #     cash += position["Shares"] * data.iloc[-1]["Close"]  # 보유 주식을 현금화
    #     data.at[-1, "Cash"] = cash
    #     data.at[-1, "Value"] = cash
    #     # 매도 기록 추가
    #     data.at[-1, "SellPrice"] = data.iloc[-1]["Close"]
    #     data.at[-1, "SellShares"] = position["Shares"]
    #     data.at[-1, "Profit"] = (data.iloc[-1]["Close"] * position["Shares"]) - position["TotalBuyPrice"]

    # 백테스팅 결과
    result = {}
    result["Start"] = {"label":"시작일", "value":data.index[0]}
    result["End"] = {"label":"종료일", "value":data.index[-1]}
    result["Duration"] = {"label":"총 거래일", "value":len(data)}
    result["InitialCash"] = {"label":"투자원금", "value":initial_capital}
    result["Cash"] = {"label":"남은 현금", "value":cash}
    result["Return"] = {"label":"실현손익금", "value":cash - initial_capital}
    result["ReturnRatio"] = {"label":"누적수익률(%)", "value":(result["Return"]["value"] / initial_capital) * 100}
    result["MaxDrawdown"] = {"label":"MDD(%)", "value":max_drawdown}
    result["TotalProfit"] = {"label":"실현 수익금의 합", "value":data[data["Profit"] > 0]["Profit"].sum()}
    result["TotalLoss"] = {"label":"실현 손실금의 합", "value":data[data["Profit"] < 0]["Profit"].sum()}
    result["ProfitLossRatio"] = {"label":"손익비", "value":result["TotalProfit"]["value"] / abs(result["TotalLoss"]["value"])}
    result["WinCount"] = {"label":"실현 수익 횟수", "value":len(data[data["Profit"] > 0])}
    result["LoseCount"] = {"label":"실현 손익 횟수", "value":len(data[data["Profit"] <= 0])}
    result["WinRate"] = {"label":"매매 성공률(%)", "value":result["WinCount"]["value"] / (result["WinCount"]["value"] + result["LoseCount"]["value"]) * 100}
    result["AvgDailyReturnRatio"] = {"label":"일평균수익률(%)", "value":result["ReturnRatio"]["value"] / result["Duration"]["value"]}
    result["AvgAnnualReturnRatio"] = {"label":"연평균수익률(%)", "value":result["AvgDailyReturnRatio"]["value"] * 247}
    result["AvgMonthlyReturnRatio"] = {"label":"월평균수익률(%)", "value":result["AvgAnnualReturnRatio"]["value"] / 12}

    snp = yf.download("^GSPC", start=data.index[0], end=data.index[-1])
    print(snp)
    result["S&P500"] = {"label":"S&P500 상승률(%)", "value":(snp.iloc[-1]["Close"] - snp.iloc[0]["Close"]) / snp.iloc[0]["Close"] * 100}


    return data, result

# 차트 그리기 함수
def plot_trades_candlestick(data):
    
    apds = [ 
        # 매수, 매도 포인트
        mpf.make_addplot(data["BuyPrice"], type='scatter'),
        mpf.make_addplot(data["SellPrice"], type='scatter'),
        # win / lose 그리기
        mpf.make_addplot(data["Profit"].apply(lambda x: x if pd.notnull(x) and x >= 0 else np.nan), type='scatter', color="red", panel=1),
        mpf.make_addplot(data["Profit"].apply(lambda x: x if pd.notnull(x) and x < 0 else np.nan), type='scatter', color="blue", panel=1),
        # 자산가치
        mpf.make_addplot(data["Value"], type='line', ylabel='Value', color="red", panel=2),
        mpf.make_addplot(data["Drawdown"], type='line', ylabel='MDD', panel=2),
        # 볼린저밴드
        # mpf.make_addplot(data["UpperLine"]), 
        # mpf.make_addplot(data["LowerLine"]),
        # RSI
        # mpf.make_addplot(data["Rsi"], type="line", ylabel='RSI', panel=3)
       ]

    # Plot the candlestick chart
    mpf.plot(data, title="Back Testing", type='candle', style="yahoo", addplot=apds, mav=(20, 60, 120), volume=False, panel_ratios=(5,1,2), figscale=1.3)


def print_result(result):
    print("백테스팅 결과:")
    for key, value in result.items():
        if isinstance(value['value'], float):
            print(f"{value['label']}: {value['value']:.2f}")
        else:
            print(f"{value['label']}: {value['value']}")

if __name__ == '__main__':
    # 주가 데이터 조회
    stock = yf.download("SOXL", start="2010-01-01")

    # 보조 지표 세팅
    data = generate_signals(stock)

    # 백테스팅
    data, result = backtest(data)

    # 결과 출력
    print_result(result)
    
    # print(data[data["Profit"].notna()])
    # print(data)

    # 차트 출력
    plot_trades_candlestick(data)
