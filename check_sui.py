import pandas as pd

df = pd.read_feather('d:/myProject/LH/freqtrade/user_data/data/binance/SUI_USDT-1d.feather')
print(f'SUI 数据条数：{len(df)}')
print(f'SUI 数据范围：{pd.to_datetime(df["date"]).min()} - {pd.to_datetime(df["date"]).max()}')
