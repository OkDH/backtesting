import yfinance as yf
import backtrader as bt
import datetime

class TestStrategy(bt.Strategy):

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # 시가
        self.dataopen = self.datas[0].open
        # 종가
        self.dataclose = self.datas[0].close
        # 저가
        self.datalow = self.datas[0].low

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():

                self.log(f'BUY  : 주가 {order.executed.price:,.2f}, '
                    f'수량 {order.executed.size:,.0f}, '
                    f'수수료 {order.executed.comm:,.2f}, '
                    f'자산 {cerebro.broker.getvalue():,.2f}')
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log(f'SELL : 주가 {order.executed.price:,.2f}, '
                    f'수량 {order.executed.size:,.0f}, '
                    f'수수료 {order.executed.comm:,.2f}, '
                    f'자산 {cerebro.broker.getvalue():,.0f}')
            self.bar_executed = len(self)
        elif order.status in [order.Canceled]:
            self.log('ORDER CANCELD')
        elif order.status in [order.Margin]:
            self.log('ORDER MARGIN')
        elif order.status in [order.Rejected]:
            self.log('ORDER REJECTED')
        # self.order = None

    def next(self):
        
        # 양봉 or 음봉
        change = self.dataclose[0] - self.dataopen[0]
        isUp = True if change > 0 else False

        # 과거 음봉 다음 양봉인날 저가
        past_low = self.datalow[0]

        num = 0 # 과거 index용
        # 음봉이면 패스, 양봉이면 음봉 만나기 전까지 루프
        if isUp :
            while True :
                num -= 1

                past_change = self.dataclose[num] - self.dataopen[num]

                if past_change > 0 :
                    # 전날 저가가 지금 저가보다 낮을 수 있어서 낮은 저가로 계산
                    past_low = self.datalow[num] if past_low > self.datalow[num] else past_low
                else :
                    break

        past_per = ((self.dataclose[0] - past_low) / past_low) * 100

        if not self.position:
            if isUp and past_per >= 10: # 매수
                self.log('BUY CREATE 저가: {:.2f} 종가: {:.2f} 상승률: {:0.2f}%'.format(
                    past_low,
                    self.dataclose[0],
                    past_per
                ))

                print(self.position)

                # 목표가에 매도 주문
                target_price = self.dataclose[0] + ((self.dataclose[0] - past_low) / 4)
                self.sell(exectype=bt.Order.Limit, price=target_price)
        # else :
            # for order in self.broker.get_orders_open():
            #     print(order)
            
        


if __name__ == '__main__':

    stock = yf.download("TQQQ", start="2023-12-01", end="2023-12-25")

    cerebro = bt.Cerebro()

    data = bt.feeds.PandasData(dataname=stock)

    cerebro.adddata(data)
    cerebro.addstrategy(TestStrategy)

    cerebro.broker = bt.brokers.BackBroker(coc=True) #cheat-on-close : 종가거래
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(0.0007)

    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    cerebro.run()

    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # cerebro.plot(style='candle', barup='red', bardown='blue')
