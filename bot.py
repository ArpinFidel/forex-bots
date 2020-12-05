import abc
import pickle
import time
from datetime import datetime

import arrow
import matplotlib
import matplotlib.animation as anim
import matplotlib.dates as pldate
import matplotlib.pyplot as plt
import matplotlib.ticker as plticker
import pandas as pd
import requests

import abcd
import macd
from agent import Agent
from helpers import logger as log
from helpers import timer


class Bot:
    max_open = 2
    speed = 200

    def __init__(self, name, agent, data, fig, ax, render_n=1, a_fig=None, a_ax=None):
        self.name = name
        self.agent = agent(data, a_fig, a_ax)
        self.data = data

        self.stop_loss   = self.agent.stop_loss
        self.take_profit = self.agent.take_profit
        self.space_order = self.agent.space_order
        self.space_loss  = self.agent.space_loss
        self.space_buy_loss     = self.agent.space_buy_loss
        self.space_sell_loss    = self.agent.space_sell_loss
        self.max_loss_duration  = self.agent.max_loss_duration

        self.fig = fig
        self.ax = ax
        self.render_n = render_n
        self.render_i = 0

        self.gains = [0, 0]
        self.min_gain = 0
        self.max_gain = 0

        self.win_n = [0, 0]
        self.lose_n = [0, 0]

        self.open = []
        self.closed = []

        self.since_order = 0
        self.since_loss  = self.space_loss
        self.since_buy_loss   = self.space_buy_loss
        self.since_sell_loss  = self.space_sell_loss
        self.history=[0 for i in range(len(data))]
        
    class Order:
        type_buy  = 0
        type_sell = 1

        def __init__(self, bot, price, order_type):
            self.type = order_type
            self.age = 0
            
            self.price = price
            self.avg_price = price
            self.new_price = 0
            self.last_price = 0
            
            self.bot = bot
            self.stop_loss = bot.stop_loss
            self.take_profit = bot.take_profit
            self.tp_decrement = .004*self.take_profit
            self.sl_decrement = .0005*self.stop_loss

            self.loss_duration = 0
            self.max_loss_duration = bot.max_loss_duration
        def update(self, new_price):
            self.age += 1
            self.new_price = new_price
            if self.age > 20 \
            and (self.avg_price-new_price)/self.avg_price < 0.005:
                self.take_profit = max(-1*self.stop_loss, self.take_profit-self.tp_decrement)
                self.stop_loss = min(0, self.stop_loss-self.sl_decrement)
            self.avg_price = (.9*self.age*self.avg_price+new_price)/(.9*self.age+1)
            self.last_price = new_price
        def get_gain(self):
            gain = 0
            if self.type == Bot.Order.type_buy:
                gain = (self.new_price-self.price)/self.price
                if gain > 1: gain -= 1
            else:
                gain = self.price/self.new_price
                if gain < 1: gain = gain-1
                else: gain -= 1
            gain = min(gain, self.bot.take_profit)
            gain = max(gain, self.bot.stop_loss)
            return gain
        def is_stop(self):
            if self.get_gain() < self.stop_loss:
                self.loss_duration += 1
                if self.loss_duration > self.max_loss_duration:
                    return True
            else:
                self.loss_duration = 0
            return False
        def is_take(self):
            return self.get_gain() > self.take_profit

    def buy(self, price):
        self.since_order = 0
        self.open.append(self.Order(self, price, self.Order.type_buy))

    def sell(self, price): 
        self.since_order = 0
        self.open.append(self.Order(self, price, self.Order.type_sell))

    def close(self, order):
        self.closed.append(order)
        self.gains[order.type] += order.get_gain()
        self.max_gain = max(self.max_gain, sum(self.gains))
        self.min_gain = min(self.min_gain, sum(self.gains))
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
        self.since_loss  += 1
        self.since_buy_loss  += 1
        self.since_sell_loss += 1

        price = data.close.iloc[-1]

        for i, order in enumerate(self.open):
            order.update(price)

            # print(self.data.index[-1], end='')
            # print(" GAIN: %+.4f TP: %.4f"%(order.get_gain(), order.take_profit))

            if order.is_stop() or order.is_take():
                self.close(order)
                self.open.pop(i)

                if order.is_stop():
                    self.since_loss = 0
                    if order.type == Bot.Order.type_buy:
                        self.since_buy_loss = 0
                    else:
                        self.since_sell_loss = 0
                
                print("CLOSE %s: %s: %.4f %.5f"%("buy" if order.type == 0 else "sell", "LOSE" if order.is_stop() else "WIN", order.get_gain(), (order.price-order.new_price)))
                print("TOTAL %.4f"%sum(self.gains))
                if self.win_n[0]+self.lose_n[0] > 0:
                    print("BUY : {:4d} {:4d} = {:.3f} {:.3f}".format(self.win_n[0], self.lose_n[0], self.win_n[0]/(self.win_n[0]+self.lose_n[0]), self.lose_n[0]/(self.win_n[0]+self.lose_n[0])))
                if self.win_n[1]+self.lose_n[1] > 0:
                    print("SELL: {:4d} {:4d} = {:.3f} {:.3f}".format(self.win_n[1], self.lose_n[1], self.win_n[1]/(self.win_n[1]+self.lose_n[1]), self.lose_n[1]/(self.win_n[1]+self.lose_n[1])))
                print("MIN %.4f"%self.min_gain)
                print("MAX %.4f"%self.max_gain)
                time.sleep(0.5)

        if len(self.open) < Bot.max_open \
        and (len(self.open) == 0 or self.since_order > self.space_order) \
        and self.since_loss > self.space_loss:
            if signal == Agent.buy_signal \
            and self.since_buy_loss > self.space_buy_loss:
                self.history.append(signal)
                self.buy(price)
                print("BUY")
            elif signal == Agent.sell_signal \
            and self.since_sell_loss > self.space_sell_loss:
                self.history.append(signal)
                self.sell(price)
                print("SELL")
            else:
                self.history.append(0)
        else:
            self.history.append(0)

        self.render()

    @log.has_log
    def render(self):
        self.render_i = (self.render_i+1) % self.render_n
        if self.render_i != 0:
            return

        timer.start()
        
        self.ax.cla()

        self.ax.tick_params(labelrotation=45)
        self.ax.xaxis.set_major_formatter(pldate.DateFormatter('%H:%M'))
        # self.ax.xaxis.set_major_locator(plticker.MultipleLocator(base=0.03))

        self.buy_sig  = [i for i, state in enumerate(self.history) if state == Agent.buy_signal ]
        self.sell_sig = [i for i, state in enumerate(self.history) if state == Agent.sell_signal]
        self.ax.plot(self.data.close, color='k', lw=1.)
        self.ax.plot(self.data.close, '^', markersize=10, color='g', label = 'buying signal',  markevery = self.buy_sig)
        self.ax.plot(self.data.close, 'v', markersize=10, color='r', label = 'selling signal', markevery = self.sell_sig)

        plt.pause(0.0001)

        elapsed = timer.get_elapsed()
        x = self.render_n/elapsed
        if x < Bot.speed:
            self.render_n += int((Bot.speed/x-1)*self.render_n-1)
        else:
            self.render_n = int(max(1, self.render_n/x))
        # if self.first_render: 
        # if self.first_render: 
        #     plt.legend()
        #     self.first_render = False

