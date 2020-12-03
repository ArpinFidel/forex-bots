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
    buy_signal = 1
    sell_signal = -1

    def __init__(self, df, fig=None, ax=None):
        self.df = df

        self.fig = fig
        self.ax = ax
        self.render_n = 10
        self.render_i = 0
        
        self.do_render = True
        if fig is None or ax is None:
            self.do_render = False
        self.first_render = True
        self.signals = []
        self.signal = 0

    @log.has_log
    def render(self):
        self.render_i = (self.render_i+1) % self.render_n
        if self.render_i != 0:
            return

        self.ax.cla()

        self.ax.tick_params(labelrotation=45)
        self.ax.xaxis.set_major_formatter(pldate.DateFormatter('%H:%M'))
        self.ax.xaxis.set_major_locator(plticker.MultipleLocator(base=0.03))

        self.buy_sig  = [i for i, state in enumerate(self.signals) if state == Agent.buy_signal ]# and (i==0 or self.signals[i-1]!=self.signals[i])]
        self.sell_sig = [i for i, state in enumerate(self.signals) if state == Agent.sell_signal]# and (i==0 or self.signals[i-1]!=self.signals[i])]
        self.ax.plot(self.df.close, color='k', lw=1.)
        self.ax.plot(self.df.close, '^', markersize=10, color='g', label = 'buying signal',  markevery = self.buy_sig)
        self.ax.plot(self.df.close, 'v', markersize=10, color='r', label = 'selling signal', markevery = self.sell_sig)

        plt.pause(0.001)

        if self.first_render: 
            plt.legend()
            self.first_render = False

    @abc.abstractmethod
    def _update(self, new_data=None): pass

    def update(self, new_data=None):
        self.signal = 0
        self._update(new_data)

        if self.do_render:
            self.render()

        return self.signal
