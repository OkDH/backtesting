import pandas as pd
import numpy as np
import math
import dao.ib_backtest_result as ibr
import strategy.infinite_buy as ib

'''
 무한매수 custom switching 버전
 기본 코드 틀은 strategy.infinite_buy.InfiniteBuy를 상속받아서
 becktest() 코드만 구현
 200일선 위에서는 v1, 아래에서는 v2버전대
'''

class InfiniteBuy(ib.InfiniteBuy): 
    

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

        # 신규진입 횟수
        new_count = 0

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
                if (self.is_ma_cut and row["MA30"] < row["MA200"]):
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
                    shares = position["Shares"]

                    # 남은 현금이 1회분 매수금액보다 작으면 쿼터 손절
                    if self.is_quarter_mode and (position["AvailableBuyCash"] - position["TotalBuyPrice"]) < position["OneBuyCash"] :
                        quarter_count += 1

                        target_shares = math.floor(shares / 4)

                        # 1/4를 MOC(종가에 무조건 매도) 매도
                        amount = row["Close"] * target_shares
                        sell_commission = math.floor(amount * self.commission * 100) / 100
                        cash += amount - sell_commission  # 주식 판매로 얻은 금액 추가
                        position["Shares"] = shares - target_shares
                        position["TotalBuyPrice"] -= amount

                        # 손익금
                        profit = amount - (position["EntryPrice"] * target_shares) - sell_commission
                        position["Profit"] += profit

                        # 매도 기록 추가
                        trade_history.append({
                            "Type":"SELL",
                            "Price": row["Close"],
                            "Shares": target_shares,
                            "Commission": sell_commission,
                            "EntryPrice": position["EntryPrice"],
                            "Profit": profit
                        })

                        stock.at[index, "Quarter"] = position["EntryPrice"]

                    else:

                        if  row["Close"] > row["MA200"] : # 200일선 위라면 v1 방식
                            # 매도 체크 
                            # 전체 수량을 평단가 +10%에 지정가 매도
                            target_price = position["EntryPrice"] * 1.1
                            target_shares = shares
                            if shares > 0 and row["High"] > target_price:
                                amount = target_price * target_shares
                                sell_commission = math.floor(amount * self.commission * 100) / 100
                                cash += amount - sell_commission  # 주식 판매로 얻은 금액 추가
                                position["Shares"] = shares - target_shares
                                position["TotalBuyPrice"] = 0

                                # 손익금
                                profit = amount - (position["EntryPrice"] * target_shares) - sell_commission
                                position["Profit"] += profit

                                # 매도 기록 추가
                                trade_history.append({
                                    "Type":"SELL",
                                    "Price": target_price,
                                    "Shares": target_shares,
                                    "Commission": sell_commission,
                                    "EntryPrice": position["EntryPrice"],
                                    "Profit": profit
                                })

                                stock.at[index, "End"] = target_price

                                if self.is_reinvest :
                                    position["AvailableBuyCash"] = cash # 수익금 재투자
                            
                        else: # 200일선 아래라면 v2 버전
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

                            if target_shares1 > 0 and row["Close"] > target_price1:
                                amount = row["Close"] * target_shares1
                                sell_commission = math.floor(amount * self.commission * 100) / 100
                                cash += amount - sell_commission  # 주식 판매로 얻은 금액 추가
                                position["Shares"] -= target_shares1
                                position["TotalBuyPrice"] = position["EntryPrice"] * position["Shares"]

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

                            if target_shares2 > 0 and row["High"] > target_price2:
                                amount = target_price2 * target_shares2
                                sell_commission = math.floor(amount * self.commission * 100) / 100
                                cash += amount - sell_commission  # 주식 판매로 얻은 금액 추가
                                position["Shares"] -= target_shares2
                                position["TotalBuyPrice"] = position["EntryPrice"] * position["Shares"]

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
                        if (position["AvailableBuyCash"] - position["TotalBuyPrice"]) > 0:
                            one_buy_shares = math.floor(position["OneBuyCash"] / row["Close"])
                            buy_shares1 = round(one_buy_shares / 2)

                            # LOC 평단매수
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

                            # 시중가 +10~15%인데, 전날 정가의 +10%로 LOC매수하는 것으로 구현
                            buy_shares2 = one_buy_shares - buy_shares1
                            buy_price = stock.at[stock.index[stock.index.get_loc(index)-1], "Close"] * 1.1
                            
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

                    if position["Shares"] == 0:
                        stock.at[index, "End"] = row["Close"]
                        position = None # 포지션 해제

            elif row["Rsi"] < self.standard_rsi and position is None and cash > 0: # 신규진입

                # if (self.is_ma_cut and row["Close"] > row["MA200"]) or not self.is_ma_cut: 
                if (self.is_ma_cut and row["MA30"] > row["MA200"]) or not self.is_ma_cut: 

                    new_count += 1

                    # 한 사이클에 매수 가능한 현금
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

        self.result.set_new_count(new_count)
        self.result.set_quarter_count(quarter_count)
        self.result.set_exhaust_count(exhaust_count)
        self.result.set_ma_cut_count(ma_cut_count)

        return stock, trade_df