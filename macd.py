import abc
import codecs
import datetime
import threading
import time

import arrow
import matplotlib
import matplotlib.animation as anim
import matplotlib.dates as pldate
import matplotlib.pyplot as plt
import matplotlib.ticker as plticker
import numpy as np
import pandas as pd
import pytz
import requests

from agent import Agent
from helpers import logger as log
from helpers import timer


@Agent.register
class MACD(Agent):
    skip_data = 4
    def __init__(self, df, fig=None, ax=None):
        super().__init__(df, fig, ax)
        
        self.stop_loss   = -.0005
        self.take_profit =  .0020
        self.space_order = 25
        self.space_loss  = 6

        self.skip_data = 0
        self.max_loss_duration = 7
        
        self.space_buy_loss   = 16
        self.space_sell_loss  = 16

    # TODO: opti mize
    @log.has_log
    def macd(self, fast=12, slow=26, signal=9):
        mean = self.df.close.mean()
        if abs(self.df.close.iloc[-1]-mean) < .00025*mean:
            return

        # fast
        short_ema = self.df.close.ewm(span=fast, adjust=False).mean()
        # slow
        long_ema = self.df.close.ewm(span=slow, adjust=False).mean()

        macd = short_ema - long_ema
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        signal = macd - signal_line

        if abs(signal[-20:].max()) < abs(signal.max())*0.25:
            return
        
        self.asdf = signal*100000

        sign = signal.iloc[-1]/abs(signal.iloc[-1])
        for i in range(2, 4):
            if signal.iloc[-i]/abs(signal.iloc[-i]) != sign:
                if sign == 1:
                    self.signal = Agent.buy_signal
                    return
                else:
                    self.signal = Agent.sell_signal
                    return

        # avg = abs(signal.mean())
        # print(signal.iloc[-1]/avg)
        # if abs(signal.iloc[-1]) < avg*0.9:
        #     x = abs(sum(signal[-6:]))
        #     if x > avg*1.1:
        #         if signal.iloc[-1] > signal.iloc[-2]:
        #             self.signal = Agent.buy_signal
        #         else:
        #             self.signal = Agent.sell_signal
        #     else: print(x/avg)
        # else: print(abs(signal.iloc[-1]), avg*0.85)
        
        mx = abs(signal.max())
        if abs(signal.iloc[-1]) > mx*0.6:
            # print("REVERSESRESERSGKLDFJLK", self.asdf.iloc[-1])
            # print(mx*0.6*1e5)
            diff = [signal.iloc[-i]-signal.iloc[-i-1] for i in range(20)]
            # self.asdf = diff*1000000
            # print(['%.2f'%(x*100000) for x in diff])
            # print(['%.2f'%(x*100000) for x in [signal.iloc[-i] for i in range(20)]])
            # time.sleep(10)
            for i in range(19):
                if diff[i]*diff[i+1] < 0:
                    for j in range(i, 19):
                        if diff[j]*diff[j+1] < 1:
                            break
                    else:
                        if signal.iloc[-1] < 0:
                            self.signal = Agent.buy_signal
                        else:
                            self.signal = Agent.sell_signal

        # flag = -1
        # for i in range(0,len(signal)):
        #     #if MACD > signal line  then buy else sell
        #     if macd[i] > signal_line[i]:
        #         if flag != 1:
        #             self.signal = Agent.buy_signal
        #             flag = 1
        #     elif macd[i] < signal_line[i]: 
        #         if flag != 0:
        #             self.signal = Agent.sell_signal
        #             flag = 0
                
            
    def _update(self, new_data=None):
        if new_data is not None:
            # self.skip_data = (self.skip_data+len(new_data)) % MACD.skip_data
            # if self.skip_data != 0: return
            self.df = self.df.append(new_data)
            self.df = self.df[-200:]

        self.macd()
        while len(self.signals) < len(self.df)-1:
            self.signals.append(0)
        self.signals.append(self.signal)
        self.signals = self.signals[-200:]


