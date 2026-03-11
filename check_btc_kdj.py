import pandas as pd
import numpy as np
from pathlib import Path

# 读取 BTC 数据 (feather 格式)
data_file = Path("d:/myProject/LH/freqtrade/user_data/data/binance/BTC_USDT-1d.feather")
if not data_file.exists():
    print("未找到 BTC 数据文件")
    exit()

df = pd.read_feather(data_file)
print(f"数据条数：{len(df)}")
print(f"时间范围：{df['date'].min()} - {df['date'].max()}")

# 计算 KDJ
period = 9
lowest_low = df['low'].rolling(window=period).min()
highest_high = df['high'].rolling(window=period).max()
df['rsv'] = (df['close'] - lowest_low) / (highest_high - lowest_low) * 100
df['k'] = df['rsv'].ewm(com=2, adjust=False).mean()
df['d'] = df['k'].ewm(com=2, adjust=False).mean()
df['j'] = 3*df['k'] - 2*df['d']

print("\n=== J 值统计 ===")
print(f"Min J: {df['j'].min():.2f}")
print(f"Max J: {df['j'].max():.2f}")
print(f"Mean J: {df['j'].mean():.2f}")
print(f"\nJ<=-5 的天数：{(df['j']<=-5).sum()}")
print(f"J>=100 的天数：{(df['j']>=100).sum()}")
print(f"J<0 的天数：{(df['j']<0).sum()}")
print(f"0<=J<=100 的天数：{((df['j']>=0) & (df['j']<=100)).sum()}")

# 显示 J 值最小的几天
print("\n=== J 值最小的 10 天 ===")
top_10_j_low = df.nsmallest(10, 'j')
for idx, row in top_10_j_low.iterrows():
    date_str = pd.to_datetime(row['date']).strftime('%Y-%m-%d')
    print(f"{date_str}: J={row['j']:.2f}")
