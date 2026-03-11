#!/usr/bin/env python3
"""
简单的KDJ策略测试脚本，不依赖API连接
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

# 添加项目路径
sys.path.append('.')


def calculate_kdj(dataframe, period=9):
    """
    计算KDJ指标
    """
    lowest_low = dataframe['low'].rolling(window=period).min()
    highest_high = dataframe['high'].rolling(window=period).max()
    
    # RSV (Raw Stochastic Value)
    dataframe['rsv'] = (dataframe['close'] - lowest_low) / (highest_high - lowest_low) * 100
    
    # KDJ calculation
    dataframe['k'] = dataframe['rsv'].ewm(com=2, adjust=False).mean()
    dataframe['d'] = dataframe['k'].ewm(com=2, adjust=False).mean()
    dataframe['j'] = 3 * dataframe['k'] - 2 * dataframe['d']
    
    return dataframe


def simple_kdj_strategy(dataframe):
    """
    简单的KDJ策略：
    - 当J值从下向上穿过20时买入
    - 当J值从上向下穿过80时卖出
    """
    buy_signals = []
    sell_signals = []
    
    for i in range(1, len(dataframe)):
        prev_j = dataframe['j'].iloc[i-1]
        curr_j = dataframe['j'].iloc[i]
        
        # 买入信号：J线从下往上穿越20
        if prev_j <= 20 <= curr_j:
            buy_signals.append(i)
        # 卖出信号：J线从上往下穿越80
        elif prev_j >= 80 >= curr_j:
            sell_signals.append(i)
    
    return buy_signals, sell_signals


def backtest_strategy(dataframe, initial_capital=10000):
    """
    对KDJ策略进行简单的回测
    """
    cash = initial_capital
    position = 0  # 持有的资产数量
    trades = []
    
    buy_signals, sell_signals = simple_kdj_strategy(dataframe)
    
    for i in range(len(dataframe)):
        date = dataframe.index[i] if hasattr(dataframe.index, 'date') else dataframe['date'].iloc[i]
        price = dataframe['close'].iloc[i]
        
        # 检查是否是买入信号
        if i in buy_signals and cash > 0:
            # 全仓买入
            position = cash / price
            cash = 0
            trades.append({
                'date': date,
                'type': 'BUY',
                'price': price,
                'amount': position,
                'capital': cash + position * price
            })
        
        # 检查是否是卖出信号
        elif i in sell_signals and position > 0:
            # 全仓卖出
            cash = position * price
            position = 0
            trades.append({
                'date': date,
                'type': 'SELL',
                'price': price,
                'amount': position,
                'capital': cash + position * price
            })
    
    # 计算最终资本
    final_capital = cash + position * dataframe['close'].iloc[-1]
    
    return {
        'initial_capital': initial_capital,
        'final_capital': final_capital,
        'trades': trades,
        'total_return': (final_capital - initial_capital) / initial_capital * 100
    }


def load_data(pair, datadir="user_data/data/binance"):
    """
    从feather文件加载数据
    """
    from pandas import read_feather
    filepath = Path(datadir) / f"{pair}-1d.feather"
    
    if not filepath.exists():
        print(f"数据文件不存在: {filepath}")
        return None
    
    df = read_feather(filepath)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    return df


def get_available_pairs(datadir="user_data/data/binance"):
    """
    获取数据目录中的所有可用交易对
    """
    data_path = Path(datadir)
    pairs = []
    
    if data_path.exists():
        for file in data_path.iterdir():
            if file.suffix == '.feather' and '-1d.' in file.name:
                # 将文件名转换为交易对格式
                pair = file.name.replace('-', '_').replace('.feather', '')
                # 只保留实际的交易对名称（不包含时间框架）
                pair = pair.split('_')[0] + '_' + pair.split('_')[1]
                if pair not in pairs:
                    pairs.append(pair)
                    
    return pairs


def main():
    print("开始测试KDJ策略在所有可用交易对上的表现...")
    
    # 获取所有可用的交易对
    available_pairs = get_available_pairs()
    print(f"检测到 {len(available_pairs)} 个可用交易对: {', '.join(available_pairs)}")
    
    if not available_pairs:
        print("错误: 没有找到任何可用的交易对数据")
        return
    
    results = {}
    
    for pair in available_pairs:
        print(f"\n正在处理 {pair}...")
        
        # 加载数据
        df = load_data(pair)
        if df is None:
            print(f"无法加载 {pair} 的数据")
            continue
        
        # 计算KDJ
        df = calculate_kdj(df)
        
        # 移除NaN值
        df = df.dropna()
        
        if len(df) == 0:
            print(f"计算KDJ后没有有效数据: {pair}")
            continue
        
        # 运行回测
        result = backtest_strategy(df)
        
        # 保存结果
        results[pair] = result
        
        print(f"  初始资金: {result['initial_capital']:.2f}")
        print(f"  最终资金: {result['final_capital']:.2f}")
        print(f"  总回报率: {result['total_return']:.2f}%")
        print(f"  交易次数: {len(result['trades'])}")
        
        if len(result['trades']) > 0:
            buy_trades = [t for t in result['trades'] if t['type'] == 'BUY']
            sell_trades = [t for t in result['trades'] if t['type'] == 'SELL']
            print(f"    买入次数: {len(buy_trades)}")
            print(f"    卖出次数: {len(sell_trades)}")
    
    # 总结
    print("\n" + "="*60)
    print("KDJ策略测试总结:")
    print("="*60)
    
    for pair, result in results.items():
        print(f"\n{pair}:")
        print(f"  总回报率: {result['total_return']:.2f}%")
        print(f"  最终资金: {result['final_capital']:.2f}")
        print(f"  交易次数: {len(result['trades'])}")
    
    # 比较基准（买入持有）
    print("\n" + "-"*60)
    print("与买入持有策略比较:")
    print("-"*60)
    
    for pair in available_pairs:
        df = load_data(pair)
        if df is not None and pair in results:
            initial_price = df['close'].iloc[0]
            final_price = df['close'].iloc[-1]
            buy_hold_return = (final_price - initial_price) / initial_price * 100
            
            kdj_return = results[pair]['total_return']
            
            print(f"\n{pair}:")
            print(f"  KDJ策略回报: {kdj_return:.2f}%")
            print(f"  买入持有回报: {buy_hold_return:.2f}%")
            print(f"  差异: {kdj_return - buy_hold_return:+.2f}%")
    
    print("\n注意：此简单回测不考虑手续费、滑点等实际因素")


if __name__ == "__main__":
    main()