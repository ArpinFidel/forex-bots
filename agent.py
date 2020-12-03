import abc
import codecs
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

from helpers import logger as log
from helpers import timer

matplotlib.rcParams['timezone'] = 'Asia/Jakarta'

# TODO: 10/9 harga beli

class Agent(abc.ABC):
    def __init__(self, ticker, fig, ax, df):
        self.ticker = ticker
        self.fig = fig
        self.ax = ax
        self.first_render = True
        self.df = df
        self.signals = []
        self.signal = 0

    @log.has_log
    def render(self):
        log.log('clearing fig')
        self.ax.cla()
        timer.elapsed()

        self.ax.title.set_text(self.ticker)
        self.ax.tick_params(labelrotation=45)
        self.ax.xaxis.set_major_formatter(pldate.DateFormatter('%H:%M'))
        self.ax.xaxis.set_major_locator(plticker.MultipleLocator(base=0.03))

        log.log('plotting')
        self.buy_sig  = [i for i, state in enumerate(self.signals) if state ==  1 and (i==0 or self.signals[i-1]!= 1)]
        self.sell_sig = [i for i, state in enumerate(self.signals) if state == -1 and (i==0 or self.signals[i-1]!=-1)]
        self.ax.plot(self.df.close, color='k', lw=1.)
        self.ax.plot(self.df.close, '^', markersize=10, color='g', label = 'buying signal',  markevery = self.buy_sig)
        self.ax.plot(self.df.close, 'v', markersize=10, color='r', label = 'selling signal', markevery = self.sell_sig)
        timer.elapsed()

        plt.pause(0.001)

        if self.first_render: 
            plt.legend()
            self.first_render = False

    @abc.abstractmethod
    def get_signals(self): pass

    def update(self, new_data=None):
        if new_data is not None:
            log.log('update data')
            self.df = self.df.append(new_data)
            self.df = self.df[-600:]
            timer.elapsed()

        log.log('generating signals')
        self.get_signals()
        timer.elapsed()

        log.log('rendering')
        self.render()

        return self.signal
