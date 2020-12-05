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

class Agent(abc.ABC):
    buy_signal = 1
    sell_signal = -1
    speed = 200

    def __init__(self, df, fig=None, ax=None):
        self.df = df
        
        self.stop_loss   = -.0004
        self.take_profit =  .0020
        self.space_order = 12
        self.space_loss  = 9
        self.space_buy_loss   = 0
        self.space_sell_loss  = 0

        self.fig = fig
        self.ax = ax
        self.render_n = 10
        self.render_i = 0
        
        self.max_loss_duration = 1

        self.do_render = True
        if fig is None or ax is None:
            self.do_render = False
        self.first_render = True
        self.signals = []
        self.signal = 0
        self.asdf=[]

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

        buy_sig  = [i for i, state in enumerate(self.signals) if state == Agent.buy_signal ]# and (i==0 or self.signals[i-1]!=self.signals[i])]
        sell_sig = [i for i, state in enumerate(self.signals) if state == Agent.sell_signal]# and (i==0 or self.signals[i-1]!=self.signals[i])]
        self.ax.plot(self.df.close, color='k', lw=1.)
        self.ax.plot(self.asdf, color='r', lw=1.)
        self.ax.plot(self.df.close, '^', markersize=10, color='g', label = 'buying signal',  markevery = buy_sig)
        self.ax.plot(self.df.close, 'v', markersize=10, color='r', label = 'selling signal', markevery = sell_sig)

        plt.pause(0.001)

        if self.first_render: 
            plt.legend()
            self.first_render = False
        
        elapsed = timer.get_elapsed()
        x = self.render_n/elapsed
        if x < Agent.speed:
            self.render_n += int((Agent.speed/x-1)*self.render_n-1)
        else:
            self.render_n = int(max(1, self.render_n/x))

    @abc.abstractmethod
    def _update(self, new_data=None): pass

    def update(self, new_data=None):
        self.signal = 0
        self._update(new_data)

        if self.do_render:
            self.render()

        return self.signal
