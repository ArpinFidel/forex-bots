import random
import sqlite3 as sl
import threading
import time

import matplotlib.pyplot as plt
import pandas as pd
from pandas.plotting import register_matplotlib_converters

import abcd
import bot
import macd
import repo
from helpers import logger as log
from helpers import timer
from order import Order

register_matplotlib_converters()
from datetime import datetime, timedelta

import MetaTrader5 as mt5

# TODO:
# save history
# refactor setter getter
# refactor structure (decouple everything)
# flask api
# shutdown command
# front end interface
# >
trade_symbol = 'USDJPY'

ENV = 'TEST'

def init_db():
    repo.create_symbols_table()
    repo.create_orders_table()
    repo.get_pair_id(trade_symbol)

def init_mt5():
    if not mt5.initialize():
        print("initialize() failed")
        mt5.shutdown()
        quit()

    print(mt5.account_info())
    validate_acc = input('correct account? [Y/n]:')
    if validate_acc == 'n' or validate_acc == 'N':
        quit()
    
    symbol_info = mt5.symbol_info(trade_symbol)
    if symbol_info is None:
        print(trade_symbol, "not found, can not call order_check()")
        mt5.shutdown()
        quit()
    
    # if the trade_symbol is unavailable in MarketWatch, add it
    if not symbol_info.visible:
        print(trade_symbol, "is not visible, trying to switch on")
        if not mt5.symbol_select(trade_symbol,True):
            print("symbol_select({}}) failed, exit",trade_symbol)
            mt5.shutdown()
            quit()
    
def get_initial_data(n, timeframe=mt5.TIMEFRAME_M5):
    df = mt5.copy_rates_from_pos(trade_symbol, timeframe , 0, n) 
    df = pd.DataFrame(df)
    df.time = pd.to_datetime(df.time, unit='s')
    # df = df[['time', 'close']]
    df.time += pd.Timedelta(hours=5)
    df = df.loc[:'close']
    print(df)
    return df

def gen_test_data(df, minutes=1):
    for i in range(len(df)):
        t = df.time.iloc[i]+timedelta(seconds=20*minutes)
        avg = (df.high.iloc[i]+df.low.iloc[i])/2
        lo = df.low.iloc[i]
        hi = df.high.iloc[i]
        op = df.open.iloc[i]
        cl = df.close.iloc[i]
        for i in range(20):
            yield ((20-i)*op + i*avg)/20, t+timedelta(seconds=i*minutes)
        for i in range(10):
            yield (i*random.uniform(lo, hi) + (10-i)*op)/10, t+timedelta(seconds=i+20*minutes)
        for i in range(10):
            yield ((10-i)*random.uniform(lo, hi) + i*cl)/10, t+timedelta(seconds=i+30*minutes)
        for i in range(20):
            yield (i*cl + (20-i)*avg)/20, t+timedelta(seconds=i+40*minutes)

def run_test():
    init_mt5()
    init_db()

    fig, ax = plt.subplots(2)
    df = get_initial_data(50000, mt5.TIMEFRAME_M10)
    initial, df = df[:600], df[600:]
    initial = initial[['time', 'close']]
    initial = initial[::5]

    b = bot.Bot(
        trade_symbol,
        trade_symbol,
        macd.MACD,
        initial, fig, ax[0], a_fig=fig, a_ax=ax[1], 
        render_n=10, 
        # do_render=False,
        do_real=False,
    )
    
    def event_loop():
        test = gen_test_data(df, 10)
        while True:
            for i in range(60):
                mt5.symbol_info(trade_symbol)

                d = df.iloc[-1:].copy()
                p, t = next(test)

                d.time  = t
                d.close = p

                if i==0:
                    b.update(d)
                    continue
                
                if len(b.open)!=0:
                    b.check_stops(d.close.iloc[-1], update_avg=False)
    event_loop()
    # threading.Thread(target=event_loop).start()

    # while True:
    #     b.render()
    #     b.agent.render()
    #     plt.pause(0.0001)

def main():
    init_mt5()
    init_db()
    
    symbol_info = mt5.symbol_info(trade_symbol)
    if symbol_info is None:
        print(trade_symbol, "not found, can not call order_check()")
        mt5.shutdown()
        quit()
    
    fig, ax = plt.subplots(2)
    df = get_initial_data(800)

    b = bot.Bot(
        trade_symbol,
        trade_symbol,
        macd.MACD,
        df, fig, ax[0], a_fig=fig, a_ax=ax[1], 
        render_n=10, 
        do_render=False
    )

    shutdown = False

    def event_loop():
        while True:
            for i in range(15):
                symbol_info = mt5.symbol_info(trade_symbol)
                
                tick = mt5.symbol_info_tick(trade_symbol)
                price = (tick.bid+tick.bid)/2

                d = df.iloc[-1:].copy()
                d.close = price
                d.time = pd.Timestamp.now().floor(freq='s')

                if i==0:
                    b.update(d, shutdown=shutdown)
                    time.sleep(20)
                    continue
                
                if len(b.open)!=0:
                    b.check_stops(d.close.iloc[-1], update_avg=False)
                time.sleep(20)
    # event_loop()
    threading.Thread(target=event_loop).start()

    while True:
        b.render()
        b.agent.render()
        plt.pause(0.5)

    # input('')
    # shutdown = True
    # while len(b.open) > 0:
    #     pass
    # time.sleep(0.5)
    # mt5.shutdown()
    # print('exit successfully')


if __name__ == '__main__': 
    if ENV == 'TEST': run_test()
    else: main()
