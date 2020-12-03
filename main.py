import abc
import datetime
import time

import arrow
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import requests

import abcd
from helpers import logger as log
from helpers import timer


class Order(abc.ABC):
    def __init__(self, price):
        self.price = price
        self.new_price = 0
    def update(self, new_price):
        self.new_price = new_price
    @abc.abstractmethod
    def get_gain(self): pass
    def is_stop(self):
        return self.get_gain < Bot.stop_loss
    def is_take(self):
        return self.get_gain > Bot.take_profit

class Bot:
    max_ongoing = 1
    stop_loss = .1
    take_profit = .25

    def __init__(self, name):
        self.name = name

        self.buy_gains = 0
        self.sell_gains = 0

        self.buy_win_n = 0
        self.buy_lose_n = 0
        self.sell_win_n = 0
        self.sell_lose_n = 0

        self.ongoing = []

    @Order.register
    class BuyOrder(Order):
        def __init__(self, price):
            super().__init__(price)
        def get_gain(self):
            gain = (self.new_price-self.price)/self.price
            if gain < 1: gain = 1 - gain
            return gain
    
    @Order.register
    class SellOrder(Order):
        def __init__(self, price):
            super().__init__(price)
        def get_gain(self):
            gain = self.price/self.new_price
            if gain < 1: gain = 1 - gain
            return gain

    def buy(self, price):
        self.ongoing.append(Bot.BuyOrder(price))

    def sell(self, price): 
        self.ongoing.append(Bot.SellOrder(price))


@log.has_log
def get_quote(ticker, interval='1m', range='1d'):
    url = 'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}=X?range={range}&interval={interval}'.format(**locals())
    res = requests.get(url)
    data = res.json()
    body = data['chart']['result'][0]

    dt = datetime.datetime
    dt = pd.Series(map(lambda x: arrow.get(x).to('Asia/Jakarta').datetime, body['timestamp']), name='Datetime')
    df = pd.DataFrame(body['indicators']['quote'][0], index=dt)
    log.log(res)

    df = df.loc[:, ('open', 'high', 'low', 'close', 'volume')]
    return df


def main():
    log.log('getting data')
    df1 = get_quote('USDJPY')
    df1, df2 = df1[:600], df1[600:]

    fig, ax = plt.subplots(2)

    timer.start()
    p = abcd.ABCD('USDJPY', fig, ax[0], df1)
    p.update()
    # a = Agent('EURGBP', fig, ax[1], None)

    for i in range(len(df2)):
        time.sleep(0.1)
        p.update(df2[i:i+1])
    # a.update()
    

    # p.render()
    # a.render()

    plt.show()
    input()


if __name__ == '__main__': main()
