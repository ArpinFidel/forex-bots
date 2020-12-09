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
    def __init__(self, df, fig=None, ax=None, do_render=True):
        super().__init__(df, fig, ax, do_render)
        
        self.stop_loss   = -.0004
        self.take_profit =  .0013
        self.space_order = 10
        self.space_loss  = 6

        self.skip_data = 0
        self.max_loss_duration = 360
        
        self.space_buy_loss   = 15
        self.space_sell_loss  = 15

    # TODO: opti mize
    @log.has_log
    def gensig(self):
        dl7 = min(self.df.low[-7:])
        dh7 = max(self.df.high[-7:])
        ema = self.df.close[-200:].mean()

        if self.df.close.iloc[-1] > ema and self.df.close.iloc[-2] < dl7:
            self.signal = Agent.buy_signal
        else if self.df.close.iloc[-2]
            
    def _update(self, new_data=None):
        if new_data is not None:
            # self.skip_data = (self.skip_data+len(new_data)) % MACD.skip_data
            # if self.skip_data != 0: return
            self.df = self.df.append(new_data, ignore_index=True)
            self.df = self.df[-200:]

        while len(self.signals) < len(self.df)-1:
            self.signals.append(0)
        self.gensig()
        self.signals.append(self.signal)
        self.signals = self.signals[-200:]


