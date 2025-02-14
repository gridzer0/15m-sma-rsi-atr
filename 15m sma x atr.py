#libraries
import MetaTrader5 as mt5
from MetaTrader5 import initialize, login, shutdown, AccountInfo, TerminalInfo, order_send, TradeRequest
import pandas as pd
import numpy as np
import time
import schedule
from datetime import datetime

#mt5 initialization
if not mt5.initialize():
    print("initialize() failed. mt5 might not be running")
    mt5.shutdown()
    quit()
else:
    print("\ninitialize() success")

account_info=mt5.account_info()
if account_info is not None:
    print(f'logged in as {account_info.name}')
else:
    print("failed to get account info")

#order details
symbol = 'EURUSD'
target_balance = account_info.balance * 1.1 #10% profit target
stop_balance = account_info.balance * 0.9 #10% account stop loss

#rsi indicator calculator function
def rsi_calculator_function(data, period=14): #change to 7 if opening frequency is low
    delta = data['close'].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    avg_gain = pd.Series(gain).rolling(window=period, min_periods=1).mean()
    avg_loss = pd.Series(loss).rolling(window=period, min_periods=1).mean()

    rs = avg_gain / (avg_loss + 1e-10)  # Avoid division by zero
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

    

while True:
    #15m timeframe data parsing
    def fifteen_minute_data():
        fifteen_minute_data = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 100)
        fifteen_minute_dataframe = pd.DataFrame(fifteen_minute_data)

        #calculate sma
        fifteen_minute_dataframe['sma'] = fifteen_minute_dataframe['close'].rolling(window=10).mean()

        #calcualte rsi
        fifteen_minute_dataframe['rsi'] = rsi_calculator_function(fifteen_minute_dataframe)

        #calcualte atr
        fifteen_minute_dataframe['high-low'] = fifteen_minute_dataframe['high'] - fifteen_minute_dataframe['low']
        fifteen_minute_dataframe['high-prev_close'] = np.abs(fifteen_minute_dataframe['high'] - fifteen_minute_dataframe['close'].shift(1))
        fifteen_minute_dataframe['low-prev_close'] = np.abs(fifteen_minute_dataframe['low'] - fifteen_minute_dataframe['close'].shift(1))
        fifteen_minute_dataframe['true_range'] = fifteen_minute_dataframe[['high-low', 'high-prev_close', 'low-prev_close']].max(axis=1)
        fifteen_minute_dataframe['atr'] = fifteen_minute_dataframe['true_range'].rolling(window=14).mean()
        fifteen_minute_dataframe['median_atr'] = fifteen_minute_dataframe['atr'].median()

        fifteen_minute_dataframe.dropna(inplace=True)

        #determine market signal. if close > sma and curremt atr > median atr, signal is bullish
        fifteen_minute_dataframe.loc[(fifteen_minute_dataframe['close'] > fifteen_minute_dataframe['sma']) & (fifteen_minute_dataframe['atr'] > fifteen_minute_dataframe['median_atr']), ['signal']] = 'bullish'
        fifteen_minute_dataframe.loc[(fifteen_minute_dataframe['close'] < fifteen_minute_dataframe['sma']) & (fifteen_minute_dataframe['atr'] > fifteen_minute_dataframe['median_atr']), ['signal']] = 'bearish'

        fifteen_minute_dataframe.loc[(fifteen_minute_dataframe['close'] == fifteen_minute_dataframe['sma']) | (fifteen_minute_dataframe['atr'] <= fifteen_minute_dataframe['median_atr']) , ['signal']] = 'hold'
        return fifteen_minute_dataframe

    def market_conditions(): #checks to see if market is bullish or bearish

        fifteen_minute_dat = fifteen_minute_data()

        first_signal = fifteen_minute_dat['signal'].iloc[-1]
        second_signal = fifteen_minute_dat['signal'].iloc[-2]
        third_signal = fifteen_minute_dat['signal'].iloc[-3]

        previous_close = fifteen_minute_dat['close'].iloc[-2]
        current_close = fifteen_minute_dat['close'].iloc[-1]

        if first_signal == 'bullish' and second_signal == 'bullish' and third_signal == 'bullish' and current_close > previous_close: #averages out last 3 signals from 15.dat for confirmation bias :/
            print('\nbullish signal')

        elif first_signal == 'bearish' and second_signal == 'bearish' and third_signal == 'bearish' and current_close < previous_close:
            print('\nbearish signal')
            
        else:
            print('\nno signal')
        time.sleep(300)

    market_conditions()