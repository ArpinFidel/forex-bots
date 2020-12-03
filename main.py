import abc
import datetime
import time

import arrow
import matplotlib
import matplotlib.animation as anim
import matplotlib.dates as pldate
import matplotlib.pyplot as plt
import matplotlib.ticker as plticker
import pandas as pd
import requests

import abcd
from agent import Agent
from helpers import logger as log
from helpers import timer


class Order(abc.ABC):
    type_buy  = 0
    type_sell = 1

    def __init__(self, price, order_type):
        self.price = price
        self.new_price = 0
        self.type = order_type
    def update(self, new_price):
        self.new_price = new_price
    @abc.abstractmethod
    def get_gain(self): pass
    def is_stop(self):
        return self.get_gain() < Bot.stop_loss
    def is_take(self):
        return self.get_gain() > Bot.take_profit

class Bot:
    max_open = 2
    stop_loss   = -.0004
    take_profit =  .0010
    space_order = 12
    space_loss  = 9

    def __init__(self, name, agent, data, fig, ax, render_n=0, a_fig=None, a_ax=None):
        self.name = name
        self.agent = agent(data, a_fig, a_ax)
        self.data = data

        self.fig = fig
        self.ax = ax
        self.render_n = render_n
        self.render_i = 0

        self.gains = [0, 0]

        self.win_n = [0, 0]
        self.lose_n = [0, 0]

        self.open = []
        self.closed = []

        self.since_order = 0
        self.since_loss  = 15
        self.history=[0 for i in range(len(data))]

    @Order.register
    class BuyOrder(Order):
        def __init__(self, price):
            super().__init__(price, Order.type_buy)
        def get_gain(self):
            gain = (self.new_price-self.price)/self.price
            if gain > 1: gain -= 1
            return gain
    
    @Order.register
    class SellOrder(Order):
        def __init__(self, price):
            super().__init__(price, Order.type_sell)
        def get_gain(self):
            gain = self.price/self.new_price
            if gain < 1: gain = gain-1
            else: gain -= 1
            return gain

    def buy(self, price):
        self.since_order = 0
        self.open.append(Bot.BuyOrder(price))

    def sell(self, price): 
        self.since_order = 0
        self.open.append(Bot.SellOrder(price))

    def close(self, order):
        self.closed.append(order)
        self.gains[order.type] += order.get_gain()
        if order.get_gain() < 0:
            self.lose_n[order.type] += 1
        else:
            self.win_n[order.type] += 1

    def update(self, data):
        signal = self.agent.update(data)
        
        if(len(self.data)>1200):
            self.data = self.data[-800:]
            self.history = self.history[-800:]
        
        self.data = self.data.append(data)
        self.since_order += 1
        self.since_loss += 1

        price = data.close[-1]

        for i, order in enumerate(self.open):
            order.update(price)

            print(self.data.index[-1], end='')
            print(" GAIN: %+.4f"%order.get_gain())

            if order.is_stop() or order.is_take():
                self.close(order)
                self.open.pop(i)
                if order.is_stop():
                    self.since_loss = 0
                
                print("CLOSE %s: %s: %.4f %.5f"%("buy" if order.type == 0 else "sell", "LOSE" if order.is_stop() else "WIN", order.get_gain(), (order.price-order.new_price)))
                print("TOTAL %.4f"%sum(self.gains))
                if self.win_n[0]+self.lose_n[0] > 0:
                    print("BUY : {:4d} {:4d} = {:.3f} {:.3f}".format(self.win_n[0], self.lose_n[0], self.win_n[0]/(self.win_n[0]+self.lose_n[0]), self.lose_n[0]/(self.win_n[0]+self.lose_n[0])))
                if self.win_n[1]+self.lose_n[1] > 0:
                    print("SELL: {:4d} {:4d} = {:.3f} {:.3f}".format(self.win_n[1], self.lose_n[1], self.win_n[1]/(self.win_n[1]+self.lose_n[1]), self.lose_n[1]/(self.win_n[1]+self.lose_n[1])))

        if len(self.open) < Bot.max_open \
        and (len(self.open) == 0 or self.since_order > Bot.space_order) \
        and self.since_loss > Bot.space_loss:
            self.history.append(signal)
            if signal == Agent.buy_signal:
                self.buy(price)
                print("BUY")
            elif signal == Agent.sell_signal:
                self.sell(price)
                print("SELL")
        else:
            self.history.append(0)

        self.render()

    @log.has_log
    def render(self):
        self.render_i = (self.render_i+1) % self.render_n
        if self.render_i != 0:
            return

        self.ax.cla()

        self.ax.tick_params(labelrotation=45)
        self.ax.xaxis.set_major_formatter(pldate.DateFormatter('%H:%M'))
        self.ax.xaxis.set_major_locator(plticker.MultipleLocator(base=0.03))

        self.buy_sig  = [i for i, state in enumerate(self.history) if state == Agent.buy_signal ]
        self.sell_sig = [i for i, state in enumerate(self.history) if state == Agent.sell_signal]
        self.ax.plot(self.data.close, color='k', lw=1.)
        self.ax.plot(self.data.close, '^', markersize=10, color='g', label = 'buying signal',  markevery = self.buy_sig)
        self.ax.plot(self.data.close, 'v', markersize=10, color='r', label = 'selling signal', markevery = self.sell_sig)

        plt.pause(0.0001)

        # if self.first_render: 
        #     plt.legend()
        #     self.first_render = False



@log.has_log
def get_quote(ticker, interval='1m', range='1d'):
    url = 'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}=X?range={range}&interval={interval}'.format(**locals())
    res = requests.get(url)
    data = res.json()
    body = data['chart']['result'][0]

    dt = datetime.datetime
    dt = pd.Series(map(lambda x: arrow.get(x).to('Asia/Jakarta').datetime, body['timestamp']), name='Datetime')
    df = pd.DataFrame(body['indicators']['quote'][0], index=dt)

    df = df.loc[:, ('open', 'high', 'low', 'close', 'volume')]
    return df


def main():
    df1 = get_quote('EURGBP', range='7d').dropna()
    df1, df2 = df1[:600], df1[600:]

    fig, ax = plt.subplots(2)

    timer.start()
    b = Bot('USDJPY', abcd.ABCD, df1, fig, ax[0], a_fig=fig, a_ax=ax[1], render_n=10)
    # a = Agent('EURGBP', fig, ax[1], None)

    for i in range(len(df2)):
        b.update(df2[i:i+1])
    # a.update()
    

    # p.render()
    # a.render()

    while True:
        plt.show()
        input()


if __name__ == '__main__': main()
