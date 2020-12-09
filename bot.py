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
import MetaTrader5 as mt5
import pandas as pd
import requests

import abcd
import macd
import repo
from agent import Agent
from helpers import logger as log
from helpers import timer
from order import Order


class Bot:
    max_open = 2
    speed = 200

    def __init__(self, pair, name, agent, data, fig, ax, 
        render_n=1, 
        a_fig=None, 
        a_ax=None, 
        do_render=True,
        do_real=True,
    ):
        self.pair = pair
        self.name = name
        self.data = data

        self.pair_id = repo.get_pair_id(pair)
        self.agent = agent(data, a_fig, a_ax, do_render=do_render)

        self.stop_loss   = self.agent.stop_loss
        self.take_profit = self.agent.take_profit
        self.space_order = self.agent.space_order
        self.space_loss  = self.agent.space_loss
        self.space_buy_loss     = self.agent.space_buy_loss
        self.space_sell_loss    = self.agent.space_sell_loss
        self.max_loss_duration  = self.agent.max_loss_duration
        self.lot = 0.01

        self.fig = fig
        self.ax  = ax
        self.render_i  = -1
        self.render_n  = render_n
        self.do_render = do_render

        self.do_real = do_real

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

    def order(self, order_type):
        # tick = mt5.symbol_info_tick(self.pair)
        # if order_type == Order.type_buy:
        #     price = tick.ask
        # else:
        #     price = tick.bid
        price = self.data.close.iloc[-1]
        self.since_order = 0
        order = Order(self, price, order_type)
        if self.do_real:
            send = self.send_open_order(order)
            if not send: return False
            order.ticket = send
        self.open.append(order)
        order.db_id = repo.insert_order(self, order)
        return order

    def close(self, order):
        self.closed.append(order)
        self.gains[order.type] += order.get_gain()
        self.max_gain = max(self.max_gain, sum(self.gains))
        self.min_gain = min(self.min_gain, sum(self.gains))
        if order.get_gain() < 0:
            self.lose_n[order.type] += 1
        else:
            self.win_n[order.type] += 1
        if self.do_real:
            ok = self.send_close_order(order)
            if not ok: return False
        repo.close_order(order)
        return True
    
    def check_stops(self, price, update_avg=True):
        if len(self.open) > 0:
            print("OPEN:", len(self.open))
        for i, order in enumerate(self.open):
            order.update(price, update_avg)

            print(order)

            if order.is_stop() or order.is_take():
                self.close(order)
                self.open.pop(i)

                if order.is_stop():
                    self.since_loss = 0
                    if order.type == Order.type_buy:
                        self.since_buy_loss = 0
                    else:
                        self.since_sell_loss = 0
                
                # print(self.data.time.iloc[-1])
                print("CLOSE %s: %s"%("buy " if order.type == 0 else "sell", "LOSE" if order.is_stop() else "WIN"))
                print("TOTAL %.4f"%sum(self.gains))
                if self.win_n[0]+self.lose_n[0] > 0:
                    print("BUY : {:4d} {:4d} = {:.3f} {:.3f}".format(self.win_n[0], self.lose_n[0], self.win_n[0]/(self.win_n[0]+self.lose_n[0]), self.lose_n[0]/(self.win_n[0]+self.lose_n[0])))
                if self.win_n[1]+self.lose_n[1] > 0:
                    print("SELL: {:4d} {:4d} = {:.3f} {:.3f}".format(self.win_n[1], self.lose_n[1], self.win_n[1]/(self.win_n[1]+self.lose_n[1]), self.lose_n[1]/(self.win_n[1]+self.lose_n[1])))
                print("MIN %+.4f"%self.min_gain)
                print("MAX %+.4f"%self.max_gain)
                print()
                # time.sleep(0.5)
        if len(self.open) > 0: print()

    def update(self, data, shutdown=False):
        signal = self.agent.update(data)

        if(len(self.data)>1200):
            self.data = self.data[-800:]
            self.history = self.history[-800:]
        
        self.data = self.data.append(data, ignore_index=True)
        
        # print(self.data.time.iloc[-1], self.data.close.iloc[-1])
        # print("OPEN:",len(self.open))

        self.since_order += 1
        self.since_loss  += 1
        self.since_buy_loss  += 1
        self.since_sell_loss += 1

        price = data.close.iloc[-1]

        self.check_stops(price)
            
        if not shutdown \
        and len(self.open) < Bot.max_open \
        and (len(self.open) == 0 or self.since_order > self.space_order) \
        and self.since_loss > self.space_loss:
            if signal == Agent.buy_signal \
            and self.since_buy_loss > self.space_buy_loss:
                self.history.append(signal)
                self.order(Order.type_buy)
                print("BUY")
            elif signal == Agent.sell_signal \
            and self.since_sell_loss > self.space_sell_loss:
                self.history.append(signal)
                self.order(Order.type_sell)
                print("SELL")
            else:
                self.history.append(0)
        else:
            self.history.append(0)

        if self.do_render: self.render()

    def send_open_order(self, order):
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "type": mt5.ORDER_TYPE_BUY if order.type==Order.type_buy else mt5.ORDER_TYPE_SELL,

            "symbol": self.pair,
            "volume": self.lot,
            "price": order.price,

            "sl": order.get_mt5_sl(),
            "tp": order.get_mt5_tp(),
            "deviation": 30,

            "magic": 234012,
            "comment": "python script open",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print('order_send failed: retcode={}'.format(result.retcode))
            for k, v in result._asdict().items():
                print('   {}={}'.format(k, v))
                if k=='request':
                    for k, v in v._asdict().items():
                        print('       traderequest: {}={}'.format(k, v))
            return False

        print("ORDER SUCCESS")
        order.ticket = result.order
        return result.order

    def send_close_order(self, order):
        deviation=50
        
        tick = mt5.symbol_info_tick(self.pair)
        if order.type == Order.type_buy:
            price = tick.bid
        else:
            price = tick.ask

        request={
            "action": mt5.TRADE_ACTION_DEAL,
            "type": mt5.ORDER_TYPE_SELL if order.type == Order.type_buy else mt5.ORDER_TYPE_BUY,
            "position": order.ticket,
            "symbol": self.pair,

            "price": price,
            "volume": self.lot,
            "deviation": deviation,

            "magic": 234000,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
            "comment": "close",
        }
        result = mt5.order_send(request)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print("order_send failed: retcode={}".format(result.retcode))
            print("   result", result)
            return False

        for k, v in result._asdict().items():
            print("   {}={}".format(k, v))
            if k == "request":
                for k, v in v._asdict().items():
                    print("       traderequest: {}={}".format(k, v))
        print("CLOSE SUCCESS")
        return True
        

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

