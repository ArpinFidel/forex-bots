import matplotlib.pyplot as plt
import pandas as pd
from pandas.plotting import register_matplotlib_converters

import abcd
import bot
import macd
from helpers import logger as log
from helpers import timer

register_matplotlib_converters()
from datetime import datetime

import MetaTrader5 as mt5


@log.has_log
def get_quote(ticker, p1, p2):
    pass
    # url = 'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}=X?period1={p1}&period2={p2}&interval=1m&range=7d'.format(**locals())
    # print(url)
    # res = requests.get(url)
    # data = res.json()
    # body = data['chart']['result'][0]
    # log.log(res)

    # dt = datetime
    # dt = pd.Series(map(lambda x: arrow.get(x).to('Asia/Jakarta').datetime, body['timestamp']), name='Datetime')
    # df = pd.DataFrame(body['indicators']['quote'][0], index=dt)

    # df = df.loc[:, ('open', 'high', 'low', 'close', 'volume')]

    # return df


def main():
    if not mt5.initialize():
        print("initialize() failed")
        mt5.shutdown()
        quit()

    print(mt5.account_info())
    validate_acc = input('correct account? [Y/n]:')
    if validate_acc == 'n' or validate_acc == 'N':
        quit()
    
    df = mt5.copy_rates_from_pos("USDJPY", mt5.TIMEFRAME_M5, 0, 10000) 
    df = pd.DataFrame(df)
    df.time = pd.to_datetime(df.time, unit='s')
    df = df.loc[:'close']
    mt5.shutdown()
    
    df1, df2 = df[:600], df[600:]

    fig, ax = plt.subplots(2)

    timer.start()
    # b = Bot('GBPJPY', abcd.ABCD, df1, fig, ax[0], a_fig=fig, a_ax=ax[1], render_n=10)
    b = bot.Bot('GBPJPY', macd.MACD, df1, fig, ax[0], a_fig=fig, a_ax=ax[1], render_n=10)
    
    for i in range(len(df2)):
        b.update(df2[i:i+1])

    plt.show()


if __name__ == '__main__': main()
