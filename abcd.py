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
class ABCD(Agent):
    def __init__(self, df, fig=None, ax=None):
        super().__init__(df, fig, ax)

        self.stop_loss   = -.0004
        self.take_profit =  .0020
        self.space_order = 25
        self.space_loss  = 6

        self.skip_data = 0
        self.max_loss_duration = 7
        
        self.space_buy_loss   = 16
        self.space_sell_loss  = 16

    # TODO: optimize
    @log.has_log
    def abcd(self, skip_loop = 15, ma = 29):
        ma = pd.Series(self.df.close).rolling(ma).mean().values
        n = ma.shape[0]

        gt = []
        lt = []
        for i in range(n):
            gt.append([])
            lt.append([])
            for j in range(i, n, skip_loop):
                if ma[i]<ma[j]: gt[i].append(j)
                if ma[i]>ma[j]: lt[i].append(j)

        ac_set = set()
        bd_set = set()

        for a in range(n):
            for b in gt[a]:
                for c in lt[b]:
                    if (ma[c] > ma[a]):
                        for d in gt[b]:
                            if d >= c:
                                ac_set.add(a)
                                ac_set.add(c)
                                bd_set.add(b)
                                bd_set.add(d)

        signal = np.zeros(len(self.df.close))
        buy = list(ac_set - bd_set)
        sell = list(bd_set - ac_set)

        signal[buy] = 1.0
        signal[sell] = -1.0

        self.signals = signal
        for i in range(1, 20):
            if signal[-i] != 0:
                curr = self.df.close.iloc[-1]
                past = self.df.close.iloc[-i]
                if abs(curr-past)/curr < 0.01 and abs(curr-ma[-1])/ma[-1] > 0.0003:
                    self.signal = signal[-i]
                    if signal[-i] == Agent.buy_signal:
                        return
    
    def _update(self, new_data=None):
        if new_data is not None:
            self.df = self.df.append(new_data)
            self.df = self.df.iloc[-300:]

        self.abcd()
