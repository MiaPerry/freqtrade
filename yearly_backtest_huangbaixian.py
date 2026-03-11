#!/usr/bin/env python3
"""
按年份分析的黄白线策略回测脚本
==================================
使用用户自定义的黄白线策略，对本地下载的币种数据进行年度收益分析

作者: AI Assistant
日期: 2026-03-11
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# 添加项目路径以便导入策略
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from user_data.strategies.HuangBaiXianStrategy import HuangBaiXianStrategy

class YearlyBacktester:
    """按年份分析的回测器"""
    
    def __init__(self, data_dir: str = None):
        """
        初始化回测器
        
        Args:
            data_dir: 数据目录路径
        """
        self.strategy = HuangBaiXianStrategy(data_dir)
        self.yearly_results = {}
        self.summary_stats = {}
        
    def analyze_yearly_performance(self, symbol: str, years: List[int] = None) -> Dict:
        """
        分析单个币种的年度表现
        
        Args:
            symbol: 币种名称
            years: 要分析的年份列表，默认为2023-2026
            
        Returns:
            Dict: 年度分析结果
        """
        if years is None:
            years = [2023, 2024, 2025, 2026]
            
        try:
            # 加载完整数据
            df = self.strategy.load_data(symbol)
            df = self.strategy.preprocess_data(df)
            df = self.strategy.calculate_indicators(df)
            df = self.strategy.generate_signals(df)
            df = self.strategy.calculate_position(df)
            df = self.strategy.calculate_returns(df)
            
            yearly_data = {}
            
            for year in years:
                # 筛选当年数据
                year_df = df[df.index.year == year].copy()
                
                if len(year_df) < 30:  # 数据不足30天跳过
                    continue
                    
                # 计算年度指标
                year_metrics = self._calculate_yearly_metrics(year_df, symbol, year)
                yearly_data[year] = year_metrics
            
            self.yearly_results[symbol] = yearly_data
            return yearly_data
            
        except Exception as e:
            print(f"✗ 分析失败 {symbol}: {str(e)}")
            return {}
    
    def _calculate_yearly_metrics(self, df: pd.DataFrame, symbol: str, year: int) -> Dict:
        """
        计算年度绩效指标
        
        Args:
            df: 年度数据
            symbol: 币种名称
            year: 年份
            
        Returns:
            Dict: 年度指标
        """
        # 基础收益计算
        total_return = df['strategy_cum'].iloc[-1] / df['strategy_cum'].iloc[0] - 1
        benchmark_return = df['benchmark_cum'].iloc[-1] / df['benchmark_cum'].iloc[0] - 1
        
        # 年化收益率(基于实际交易日)
        n_days = len(df)
        if n_days > 0:
            annual_return = (1 + total_return) ** (365 / n_days) - 1
        else:
            annual_return = 0
            
        # 最大回撤
        cummax = df['strategy_cum'].cummax()
        drawdown = df['strategy_cum'] / cummax - 1
        max_drawdown = drawdown.min()
        
        # 交易统计
        buy_signals = df['buy_signal'].sum()
        sell_signals = df['sell_signal'].sum()
        
        # 计算每笔交易盈亏
        trades = df.attrs.get('trades', [])
        profitable_trades = 0
        total_trades = 0
        trade_returns = []
        
        # 只统计完整交易对(买入+卖出)
        for i in range(0, len(trades) - 1, 2):
            if (trades[i][1] == 'buy' and 
                i + 1 < len(trades) and 
                trades[i + 1][1] == 'sell'):
                
                buy_idx = trades[i][0]
                sell_idx = trades[i + 1][0]
                
                # 确保索引在数据范围内
                if buy_idx in df.index and sell_idx in df.index:
                    buy_price = df.loc[buy_idx, 'close']
                    sell_price = df.loc[sell_idx, 'close']
                    trade_return = (sell_price - buy_price) / buy_price
                    
                    total_trades += 1
                    trade_returns.append(trade_return)
                    
                    if trade_return > 0:
                        profitable_trades += 1
        
        # 胜率和盈亏比
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        
        if trade_returns:
            avg_win = np.mean([r for r in trade_returns if r > 0]) if any(r > 0 for r in trade_returns) else 0
            avg_loss = np.mean([abs(r) for r in trade_returns if r <= 0]) if any(r <= 0 for r in trade_returns) else 0
            profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        else:
            avg_win = avg_loss = profit_loss_ratio = 0
        
        metrics = {
            'symbol': symbol,
            'year': year,
            'total_return': total_return,
            'annual_return': annual_return,
            'benchmark_return': benchmark_return,
            'excess_return': total_return - benchmark_return,
            'max_drawdown': max_drawdown,
            'buy_signals': int(buy_signals),
            'sell_signals': int(sell_signals),
            'total_trades': total_trades,
            'profitable_trades': profitable_trades,
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'data_days': n_days,
            'start_date': df.index[0].strftime('%Y-%m-%d'),
            'end_date': df.index[-1].strftime('%Y-%m-%d')
        }
        
        return metrics
    
    def run_yearly_analysis(self, symbols: List[str] = None, years: List[int] = None) -> pd.DataFrame:
        """
        运行年度分析
        
        Args:
            symbols: 币种列表，None表示所有可用币种
            years: 年份列表
            
        Returns:
            DataFrame: 年度分析汇总表
        """
        if symbols is None:
            symbols = self.strategy.get_available_symbols()
            
        if years is None:
            years = [2023, 2024, 2025, 2026]
        
        print(f"\n{'='*80}")
        print(f"黄白线策略年度收益分析")
        print(f"{'='*80}")
        print(f"分析币种数量: {len(symbols)}")
        print(f"分析年份: {years}")
        print(f"{'='*80}")
        
        # 分析每个币种
        for i, symbol in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] 分析 {symbol}...")
            self.analyze_yearly_performance(symbol, years)
        
        # 生成汇总报告
        return self._generate_summary_report()
    
    def _generate_summary_report(self) -> pd.DataFrame:
        """
        生成年度分析汇总报告
        
        Returns:
            DataFrame: 汇总报告
        """
        # 将所有结果展平为列表
        all_results = []
        for symbol, yearly_data in self.yearly_results.items():
            for year, metrics in yearly_data.items():
                all_results.append(metrics)
        
        if not all_results:
            print("✗ 没有有效的分析结果")
            return pd.DataFrame()
        
        # 创建DataFrame
        df = pd.DataFrame(all_results)
        
        # 按年份和收益率排序
        df_sorted = df.sort_values(['year', 'total_return'], ascending=[True, False])
        
        # 打印年度汇总
        self._print_yearly_summary(df_sorted)
        
        # 打印各年份Top表现
        self._print_top_performers(df_sorted)
        
        return df_sorted
    
    def _print_yearly_summary(self, df: pd.DataFrame):
        """打印年度汇总统计"""
        print(f"\n{'='*80}")
        print(f"年度汇总统计")
        print(f"{'='*80}")
        
        for year in sorted(df['year'].unique()):
            year_data = df[df['year'] == year]
            
            avg_return = year_data['total_return'].mean()
            median_return = year_data['total_return'].median()
            positive_rate = (year_data['total_return'] > 0).mean()
            avg_win_rate = year_data['win_rate'].mean()
            avg_max_dd = year_data['max_drawdown'].mean()
            
            print(f"\n{year}年:")
            print(f"  平均收益率: {avg_return*100:>8.2f}%")
            print(f"  中位数收益率: {median_return*100:>6.2f}%")
            print(f"  正收益币种比例: {positive_rate*100:>5.1f}%")
            print(f"  平均胜率: {avg_win_rate*100:>10.1f}%")
            print(f"  平均最大回撤: {avg_max_dd*100:>8.2f}%")
    
    def _print_top_performers(self, df: pd.DataFrame):
        """打印各年份表现最好的币种"""
        print(f"\n{'='*80}")
        print(f"各年份Top 5表现")
        print(f"{'='*80}")
        
        for year in sorted(df['year'].unique()):
            year_data = df[df['year'] == year].nlargest(5, 'total_return')
            
            print(f"\n🏆 {year}年 Top 5:")
            print("-" * 60)
            for idx, (_, row) in enumerate(year_data.iterrows(), 1):
                print(f"{idx}. {row['symbol']:<12} "
                      f"收益率: {row['total_return']*100:>7.2f}% "
                      f"胜率: {row['win_rate']*100:>5.1f}% "
                      f"交易: {row['total_trades']:>2}笔")

def main():
    """主程序入口"""
    # 初始化年度回测器
    backtester = YearlyBacktester()
    
    # 获取可用币种
    available_symbols = backtester.strategy.get_available_symbols()
    print(f"可用币种 ({len(available_symbols)} 个):")
    print(", ".join(available_symbols[:10]) + ("..." if len(available_symbols) > 10 else ""))
    
    # 运行年度分析
    results_df = backtester.run_yearly_analysis()
    
    if not results_df.empty:
        # 保存结果
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"yearly_backtest_results_{timestamp}.csv"
        results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n💾 详细结果已保存到: {output_file}")
        
        # 显示总体统计
        print(f"\n{'='*80}")
        print(f"总体统计")
        print(f"{'='*80}")
        print(f"总分析记录数: {len(results_df)}")
        print(f"平均年收益率: {results_df['total_return'].mean()*100:.2f}%")
        print(f"年收益率标准差: {results_df['total_return'].std()*100:.2f}%")
        print(f"正收益年份数: {(results_df['total_return'] > 0).sum()}")
        print(f"负收益年份数: {(results_df['total_return'] <= 0).sum()}")

if __name__ == "__main__":
    main()