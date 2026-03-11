import pandas as pd
from pathlib import Path

# 加载SUI数据
df = pd.read_feather('user_data/data/binance/SUI_USDT-1d.feather')
df['date'] = pd.to_datetime(df['date'])
df.set_index('date', inplace=True)

print('SUI/USDT 数据摘要:')
print(f'起始日期: {df.index[0]}')
print(f'结束日期: {df.index[-1]}')
print(f'起始价格: {df.iloc[0]["close"]}')
print(f'结束价格: {df.iloc[-1]["close"]}')

initial_price = df.iloc[0]["close"]
final_price = df.iloc[-1]["close"]
buy_hold_return = (final_price - initial_price) / initial_price * 100
print(f'总回报率: {buy_hold_return:.2f}%')

print('\n前几行数据:')
print(df[['open', 'high', 'low', 'close']].head())

print('\n后几行数据:')
print(df[['open', 'high', 'low', 'close']].tail())

# 查找最低价和最高价
print(f'\n期间最低价: {df["low"].min()}')
print(f'期间最高价: {df["high"].max()}')
print(f'最低价日期: {df[df["low"] == df["low"].min()].index[0].date()}')
print(f'最高价日期: {df[df["high"] == df["high"].max()].index[0].date()}')