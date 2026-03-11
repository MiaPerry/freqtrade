#!/usr/bin/env python3
"""
离线回测脚本 - 对前30个币种进行黄白线策略回测
直接读取本地数据文件，无需网络连接
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path
import talib
from datetime import datetime
import json

class OfflineBacktester:
    def __init__(self, data_dir="user_data/data/binance"):
        self.data_dir = Path(data_dir)
        self.results = {}
        self.total_trades = 0
        self.winning_trades = 0
        self.total_profit = 0
        
    def load_data(self, pair):
        """加载指定交易对的日线数据"""
        filename = f"{pair.replace('/', '_')}-1d.feather"
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            print(f"⚠️  数据文件不存在: {filename}")
            return None
            
        try:
            df = pd.read_feather(filepath)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            print(f"✅ 加载 {pair}: {len(df)} 条记录 ({df.index[0].date()} 到 {df.index[-1].date()})")
            return df
        except Exception as e:
            print(f"❌ 加载 {pair} 失败: {e}")
            return None
    
    def calculate_indicators(self, df):
        """计算黄白线策略所需的技术指标"""
        # 计算移动平均线
        df['ma_short'] = talib.SMA(df['close'], timeperiod=10)  # 白线
        df['ma_long'] = talib.SMA(df['close'], timeperiod=30)   # 黄线
        
        # 计算均线斜率
        df['ma_long_slope'] = df['ma_long'].diff(3)
        
        # 计算金叉死叉信号
        df['golden_cross'] = (df['ma_short'] > df['ma_long']) & (df['ma_short'].shift(1) <= df['ma_long'].shift(1))
        df['death_cross'] = (df['ma_short'] < df['ma_long']) & (df['ma_short'].shift(1) >= df['ma_long'].shift(1))
        
        # 计算其他辅助指标
        df['rsi'] = talib.RSI(df['close'], timeperiod=14)
        
        return df
    
    def apply_strategy(self, df, pair):
        """应用黄白线策略"""
        if df is None or len(df) < 35:
            return None
            
        df = self.calculate_indicators(df)
        
        # 初始化交易记录
        positions = []
        current_position = None
        trades = []
        
        # 策略逻辑
        for i in range(35, len(df)):  # 跳过预热期
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            # 买入条件
            if current_position is None:
                # 金叉买入条件
                if (row['golden_cross'] and 
                    row['close'] > row['ma_long'] and 
                    row['ma_long_slope'] > 0 and
                    row['rsi'] < 70):
                    
                    current_position = {
                        'entry_date': row.name,
                        'entry_price': row['close'],
                        'entry_reason': '金叉买入'
                    }
                
                # 回踩买入条件
                elif (row['ma_short'] > row['ma_long'] and  # 白线在黄线上方
                      row['close'] > row['ma_long'] and     # 股价在黄线上方
                      row['low'] <= row['ma_short'] * 1.02 and  # 接近白线
                      row['close'] > row['ma_short'] and    # 收盘在白线上
                      row['ma_long_slope'] > 0):
                    
                    current_position = {
                        'entry_date': row.name,
                        'entry_price': row['close'],
                        'entry_reason': '回踩白线'
                    }
            
            # 卖出条件
            elif current_position is not None:
                exit_reason = None
                
                # 止损条件
                if row['close'] < row['ma_long']:  # 跌破黄线
                    exit_reason = '跌破黄线'
                elif row['death_cross']:  # 死叉
                    exit_reason = '死叉卖出'
                elif row['ma_long_slope'] <= 0 and row['close'] < row['ma_short']:
                    exit_reason = '趋势转弱'
                
                # 止盈条件
                elif ((row['close'] - current_position['entry_price']) / current_position['entry_price'] > 0.15):
                    exit_reason = '获利了结'
                
                if exit_reason:
                    trade = {
                        'pair': pair,
                        'entry_date': current_position['entry_date'],
                        'exit_date': row.name,
                        'entry_price': current_position['entry_price'],
                        'exit_price': row['close'],
                        'entry_reason': current_position['entry_reason'],
                        'exit_reason': exit_reason,
                        'profit_pct': (row['close'] - current_position['entry_price']) / current_position['entry_price'] * 100
                    }
                    trades.append(trade)
                    current_position = None
        
        # 处理最后一个未平仓交易
        if current_position is not None and len(df) > 0:
            final_price = df['close'].iloc[-1]
            trade = {
                'pair': pair,
                'entry_date': current_position['entry_date'],
                'exit_date': df.index[-1],
                'entry_price': current_position['entry_price'],
                'exit_price': final_price,
                'entry_reason': current_position['entry_reason'],
                'exit_reason': '期末平仓',
                'profit_pct': (final_price - current_position['entry_price']) / current_position['entry_price'] * 100
            }
            trades.append(trade)
        
        return trades
    
    def run_backtest(self):
        """运行完整的回测"""
        print("=" * 80)
        print("📊 前30个币种黄白线策略回测报告")
        print("=" * 80)
        print(f"📅 回测时间: 2023年1月1日至今")
        print(f"📈 策略: 黄白线战法 (MA10金叉MA30)")
        print(f"💰 交易成本: 无 (简化模型)")
        print("=" * 80)
        
        # 前30个主流币种
        top_30_pairs = [
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
            "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "DOT/USDT", "TRX/USDT",
            "MATIC/USDT", "LTC/USDT", "SHIB/USDT", "UNI/USDT", "LINK/USDT",
            "ATOM/USDT", "TON/USDT", "XMR/USDT", "ICP/USDT", "BCH/USDT",
            "ETC/USDT", "NEAR/USDT", "VET/USDT", "APT/USDT", "HBAR/USDT",
            "ALGO/USDT", "FIL/USDT", "FLOW/USDT", "SAND/USDT", "MANA/USDT"
        ]
        
        all_trades = []
        
        for pair in top_30_pairs:
            print(f"\n🔄 测试 {pair}...")
            df = self.load_data(pair)
            if df is not None:
                trades = self.apply_strategy(df, pair)
                if trades:
                    all_trades.extend(trades)
                    self.analyze_pair_trades(pair, trades)
                else:
                    print(f"   📉 {pair}: 无交易信号")
            else:
                print(f"   ⚠️  {pair}: 无数据")
        
        # 总体分析
        self.analyze_overall_results(all_trades)
        
        return all_trades
    
    def analyze_pair_trades(self, pair, trades):
        """分析单个交易对的结果"""
        if not trades:
            return
            
        profits = [t['profit_pct'] for t in trades]
        winning_trades = [p for p in profits if p > 0]
        
        print(f"   📈 交易次数: {len(trades)}")
        print(f"   💰 总收益: {sum(profits):+.2f}%")
        print(f"   🎯 胜率: {len(winning_trades)/len(trades)*100:.1f}%")
        print(f"   📊 平均收益: {np.mean(profits):+.2f}%")
        if winning_trades:
            print(f"   🏆 最佳单笔: {max(profits):+.2f}%")
            print(f"   💔 最差单笔: {min(profits):+.2f}%")
    
    def analyze_overall_results(self, all_trades):
        """分析总体回测结果"""
        if not all_trades:
            print("\n❌ 无有效交易产生")
            return
            
        print("\n" + "=" * 80)
        print("🏆 总体回测结果")
        print("=" * 80)
        
        # 基本统计
        total_trades = len(all_trades)
        profits = [t['profit_pct'] for t in all_trades]
        winning_trades = [p for p in profits if p > 0]
        
        print(f"📊 总交易次数: {total_trades}")
        print(f"💰 总收益: {sum(profits):+.2f}%")
        print(f"🎯 整体胜率: {len(winning_trades)/total_trades*100:.1f}%")
        print(f"📈 平均收益: {np.mean(profits):+.2f}%")
        print(f"📊 收益标准差: {np.std(profits):.2f}%")
        
        if winning_trades:
            print(f"🏆 最佳单笔收益: {max(profits):+.2f}%")
            print(f"💔 最差单笔收益: {min(profits):+.2f}%")
            print(f"💪 平均盈利: {np.mean(winning_trades):+.2f}%")
            avg_loss = np.mean([p for p in profits if p <= 0])
            print(f"😢 平均亏损: {avg_loss:+.2f}%")
            print(f"⚖️  盈亏比: {abs(np.mean(winning_trades)/avg_loss):.2f}")
        
        # 按币种统计
        print(f"\n💹 各币种表现:")
        print("-" * 50)
        pair_stats = {}
        for trade in all_trades:
            pair = trade['pair']
            if pair not in pair_stats:
                pair_stats[pair] = []
            pair_stats[pair].append(trade['profit_pct'])
        
        for pair, profits in sorted(pair_stats.items(), key=lambda x: sum(x[1]), reverse=True):
            total_profit = sum(profits)
            win_rate = len([p for p in profits if p > 0]) / len(profits) * 100
            print(f"{pair:10s} | 交易{len(profits):2d}次 | 总收益{total_profit:>+7.2f}% | 胜率{win_rate:>5.1f}%")
        
        # 交易信号分析
        print(f"\n🔔 交易信号分布:")
        print("-" * 30)
        entry_reasons = [t['entry_reason'] for t in all_trades]
        exit_reasons = [t['exit_reason'] for t in all_trades]
        
        for reason in set(entry_reasons):
            count = entry_reasons.count(reason)
            print(f"买入信号 - {reason}: {count}次")
            
        for reason in set(exit_reasons):
            count = exit_reasons.count(reason)
            print(f"卖出信号 - {reason}: {count}次")

if __name__ == "__main__":
    # 创建回测器并运行
    backtester = OfflineBacktester()
    trades = backtester.run_backtest()
    
    # 保存结果
    if trades:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = f"backtest_results_top30_{timestamp}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(trades, f, indent=2, default=str)
        print(f"\n💾 详细交易记录已保存到: {result_file}")