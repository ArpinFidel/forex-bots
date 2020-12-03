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

import agent
from helpers import logger as log
from helpers import timer


@agent.Agent.register
class ABCD(agent.Agent):
    def __init__(self, ticker, fig, ax, df):
        super().__init__(ticker, fig, ax, df)
    @log.has_log
    def abcd(self, skip_loop = 13, ma = 27):
        trend = self.df.close
        ma = pd.Series(trend).rolling(ma).mean().values
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

        signal = np.zeros(len(trend))
        buy = list(ac_set - bd_set)
        sell = list(bd_set - ac_set)

        signal[buy] = 1.0
        signal[sell] = -1.0

        self.signals = signal
        self.signal = signal[-1]
    
    def get_signals(self):
        self.abcd()
