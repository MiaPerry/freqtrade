#!/usr/bin/env python3
"""
分析SUI黄白线策略的交易细节
"""

import pandas as pd
import numpy as np
from pathlib import Path


def calculate_moving_averages(dataframe, short_period=10, long_period=50):
    """
    计算移动平均线
    """
    dataframe['ma_short'] = dataframe['close'].rolling(window=short_period).mean()
    dataframe['ma_long'] = dataframe['close'].rolling(window=long_period).mean()
    
    return dataframe


def analyze_huangbaixian_strategy(dataframe):
    """
    分析黄白线策略的交易信号
    """
    buy_signals = []
    sell_signals = []
    
    for i in range(1, len(dataframe)):
        prev_short = dataframe['ma_short'].iloc[i-1]
        curr_short = dataframe['ma_short'].iloc[i]
        prev_long = dataframe['ma_long'].iloc[i-1]
        curr_long = dataframe['ma_long'].iloc[i]
        
        # 买入信号：短期均线上穿长期均线（金叉）
        if prev_short <= prev_long and curr_short > curr_long:
            buy_signals.append(i)
        # 卖出信号：短期均线下穿长期均线（死叉）
        elif prev_short >= prev_long and curr_short < curr_long:
            sell_signals.append(i)
    
    return buy_signals, sell_signals


def detailed_backtest(dataframe, initial_capital=10000):
    """
    详细的回测，返回所有交易记录
    """
    cash = initial_capital
    position = 0  # 持有的资产数量
    trades = []
    
    buy_signals, sell_signals = analyze_huangbaixian_strategy(dataframe)
    
    for i in range(len(dataframe)):
        date = dataframe.index[i] if hasattr(dataframe.index, 'date') else dataframe['date'].iloc[i]
        price = dataframe['close'].iloc[i]
        
        # 检查是否是买入信号
        if i in buy_signals and cash > 0:
            # 全仓买入
            position = cash / price
            cash = 0
            trade_record = {
                'date': date,
                'type': 'BUY',
                'price': price,
                'amount': position,
                'capital': cash + position * price,
                'cash': cash,
                'holdings_value': position * price
            }
            trades.append(trade_record)
        
        # 检查是否是卖出信号
        elif i in sell_signals and position > 0:
            # 全仓卖出
            cash = position * price
            position = 0
            trade_record = {
                'date': date,
                'type': 'SELL',
                'price': price,
                'amount': position,  # 这里position已经是0了，所以改为卖出的数量
                'capital': cash + position * price,
                'cash': cash,
                'holdings_value': position * price
            }
            # 需要修正卖出量
            if trades:  # 如果已经有交易记录
                last_buy = trades[-1]  # 上一次是买入
                trade_record['amount'] = last_buy['amount']  # 卖出的数量等于上次买入的数量
            trades.append(trade_record)
    
    # 计算最终资本
    final_capital = cash + position * dataframe['close'].iloc[-1]
    
    return {
        'initial_capital': initial_capital,
        'final_capital': final_capital,
        'trades': trades,
        'total_return': (final_capital - initial_capital) / initial_capital * 100,
        'buy_signals': buy_signals,
        'sell_signals': sell_signals
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


def main():
    print("分析SUI/USDT黄白线策略的交易细节...")
    
    # 加载数据
    df = load_data("SUI_USDT")
    if df is None:
        print("无法加载SUI_USDT的数据")
        return
    
    # 计算移动平均线
    df = calculate_moving_averages(df)
    
    # 移除NaN值
    df = df.dropna()
    
    if len(df) == 0:
        print("计算移动平均线后没有有效数据")
        return
    
    # 运行详细回测
    result = detailed_backtest(df)
    
    print(f"\n总体结果:")
    print(f"  初始资金: {result['initial_capital']:.2f}")
    print(f"  最终资金: {result['final_capital']:.2f}")
    print(f"  总回报率: {result['total_return']:.2f}%")
    print(f"  交易次数: {len(result['trades'])}")
    
    # 显示交易历史
    print(f"\n交易历史:")
    print(f"{'类型':<5} {'日期':<12} {'价格':<10} {'数量':<15} {'现金':<15} {'持仓价值':<15}")
    print("-" * 80)
    
    for trade in result['trades']:
        print(f"{trade['type']:<5} {str(trade['date'].date()):<12} {trade['price']:<10.4f} "
              f"{trade['amount']:<15.4f} {trade['cash']:<15.2f} {trade['holdings_value']:<15.2f}")
    
    # 分析每笔交易的盈亏
    print(f"\n每笔交易盈亏分析:")
    print(f"{'序号':<4} {'买入价':<10} {'卖出价':<10} {'收益率':<10} {'利润':<15}")
    print("-" * 60)
    
    trade_pairs = []
    for i in range(0, len(result['trades']), 2):  # 每两次交易为一对买卖
        if i + 1 < len(result['trades']):
            buy_trade = result['trades'][i]
            sell_trade = result['trades'][i+1]
            
            if buy_trade['type'] == 'BUY' and sell_trade['type'] == 'SELL':
                profit_rate = (sell_trade['price'] / buy_trade['price'] - 1) * 100
                profit = buy_trade['amount'] * (sell_trade['price'] - buy_trade['price'])
                
                print(f"{i//2+1:<4} {buy_trade['price']:<10.4f} {sell_trade['price']:<10.4f} "
                      f"{profit_rate:<10.2f}% {profit:<15.2f}")
                
                trade_pairs.append((buy_trade['price'], sell_trade['price'], profit_rate, profit))
    
    # 总结盈利交易和亏损交易
    profitable_trades = [t for t in trade_pairs if t[2] > 0]
    losing_trades = [t for t in trade_pairs if t[2] <= 0]
    
    print(f"\n交易统计:")
    print(f"  盈利交易数: {len(profitable_trades)}")
    print(f"  亏损交易数: {len(losing_trades)}")
    print(f"  胜率: {len(profitable_trades)/(len(profitable_trades)+len(losing_trades))*100:.2f}%")


if __name__ == "__main__":
    main()