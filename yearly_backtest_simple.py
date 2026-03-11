#!/usr/bin/env python3
"""
简化版年度回测脚本 - 不依赖matplotlib
=====================================
使用黄白线策略分析各币种年度收益表现

作者: AI Assistant
日期: 2026-03-11
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class SimpleYearlyBacktester:
    """简化版年度回测器"""
    
    def __init__(self, data_dir: str = None):
        """初始化"""
        if data_dir is None:
            project_root = Path(__file__).parent
            self.data_dir = project_root / "user_data" / "data" / "binance"
        else:
            self.data_dir = Path(data_dir)
    
    def load_data(self, symbol: str) -> pd.DataFrame:
        """加载数据"""
        file_path = self.data_dir / f"{symbol}-1d.feather"
        if not file_path.exists():
            raise FileNotFoundError(f"数据文件不存在: {file_path}")
        
        df = pd.read_feather(file_path)
        df.columns = df.columns.str.lower()
        if 'date' in df.columns:
            df['timestamp'] = pd.to_datetime(df['date'])
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        return df
    
    def get_available_symbols(self) -> list:
        """获取可用币种"""
        symbols = []
        for file_path in self.data_dir.glob("*-1d.feather"):
            symbol = file_path.stem.replace("-1d", "")
            symbols.append(symbol)
        return sorted(symbols)
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        df = df.copy()
        df['ma10'] = df['close'].rolling(window=10, min_periods=10).mean()
        df['ma30'] = df['close'].rolling(window=30, min_periods=30).mean()
        df['ma30_slope'] = (df['ma30'] - df['ma30'].shift(5)) / df['ma30'].shift(5)
        return df.iloc[30:]  # 剔除预热期数据
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = df.copy()
        df['price_above_ma30'] = df['close'] > df['ma30']
        df['golden_cross'] = (df['ma10'] > df['ma30']) & (df['ma10'].shift(1) <= df['ma30'].shift(1))
        df['death_cross'] = (df['ma10'] < df['ma30']) & (df['ma10'].shift(1) >= df['ma30'].shift(1))
        df['ma30_down'] = df['ma30_slope'] <= 0
        
        # 买入信号
        df['buy_signal'] = df['price_above_ma30'] & df['golden_cross']
        
        # 卖出信号
        df['sell_signal'] = (df['close'] < df['ma30']) | df['death_cross'] | df['ma30_down']
        
        return df
    
    def calculate_position(self, df: pd.DataFrame) -> tuple:
        """计算仓位和交易记录"""
        df = df.copy()
        df['position'] = 0
        
        position = 0
        trades = []
        
        for i in range(len(df)):
            if df.iloc[i]['buy_signal'] and position == 0:
                position = 1
                trades.append(('buy', df.index[i], df.iloc[i]['close']))
            elif df.iloc[i]['sell_signal'] and position == 1:
                position = 0
                trades.append(('sell', df.index[i], df.iloc[i]['close']))
            
            df.iloc[i, df.columns.get_loc('position')] = position
        
        return df, trades
    
    def calculate_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算收益"""
        df = df.copy()
        df['daily_return'] = df['close'].pct_change()
        df['strategy_return'] = df['position'].shift(1) * df['daily_return']
        df['strategy_cum'] = (1 + df['strategy_return']).cumprod()
        df['benchmark_cum'] = (1 + df['daily_return']).cumprod()
        return df
    
    def analyze_yearly_performance(self, symbol: str, years: list = None) -> dict:
        """分析年度表现"""
        if years is None:
            years = [2023, 2024, 2025, 2026]
        
        try:
            # 加载和处理数据
            df = self.load_data(symbol)
            df = self.calculate_indicators(df)
            df = self.generate_signals(df)
            df, trades = self.calculate_position(df)
            df = self.calculate_returns(df)
            
            yearly_results = {}
            
            for year in years:
                year_df = df[df.index.year == year].copy()
                if len(year_df) < 30:
                    continue
                
                # 计算年度指标
                start_value = year_df['strategy_cum'].iloc[0]
                end_value = year_df['strategy_cum'].iloc[-1]
                total_return = (end_value / start_value) - 1
                
                bench_start = year_df['benchmark_cum'].iloc[0]
                bench_end = year_df['benchmark_cum'].iloc[-1]
                benchmark_return = (bench_end / bench_start) - 1
                
                # 年化收益率
                n_days = len(year_df)
                annual_return = (1 + total_return) ** (365 / n_days) - 1
                
                # 最大回撤
                cummax = year_df['strategy_cum'].cummax()
                drawdown = year_df['strategy_cum'] / cummax - 1
                max_drawdown = drawdown.min()
                
                # 交易统计
                buy_signals = year_df['buy_signal'].sum()
                sell_signals = year_df['sell_signal'].sum()
                
                # 计算完整交易的盈亏
                profitable_trades = 0
                total_trades = 0
                trade_returns = []
                
                year_trades = [t for t in trades if t[1].year == year]
                
                for i in range(0, len(year_trades) - 1, 2):
                    if (year_trades[i][0] == 'buy' and 
                        i + 1 < len(year_trades) and 
                        year_trades[i + 1][0] == 'sell'):
                        
                        buy_price = year_trades[i][2]
                        sell_price = year_trades[i + 1][2]
                        trade_return = (sell_price - buy_price) / buy_price
                        
                        total_trades += 1
                        trade_returns.append(trade_return)
                        
                        if trade_return > 0:
                            profitable_trades += 1
                
                win_rate = profitable_trades / total_trades if total_trades > 0 else 0
                
                if trade_returns:
                    avg_win = np.mean([r for r in trade_returns if r > 0]) if any(r > 0 for r in trade_returns) else 0
                    avg_loss = np.mean([abs(r) for r in trade_returns if r <= 0]) if any(r <= 0 for r in trade_returns) else 0
                    profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
                else:
                    avg_win = avg_loss = profit_loss_ratio = 0
                
                yearly_results[year] = {
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
                    'start_date': year_df.index[0].strftime('%Y-%m-%d'),
                    'end_date': year_df.index[-1].strftime('%Y-%m-%d')
                }
            
            return yearly_results
            
        except Exception as e:
            print(f"✗ 分析失败 {symbol}: {str(e)}")
            return {}
    
    def run_analysis(self, symbols: list = None, years: list = None) -> pd.DataFrame:
        """运行完整分析"""
        if symbols is None:
            symbols = self.get_available_symbols()
            
        if years is None:
            years = [2023, 2024, 2025, 2026]
        
        print("=" * 80)
        print("黄白线策略年度收益分析报告")
        print("=" * 80)
        print(f"分析币种: {len(symbols)} 个")
        print(f"分析年份: {years}")
        print("=" * 80)
        
        all_results = []
        
        for i, symbol in enumerate(symbols, 1):
            print(f"[{i}/{len(symbols)}] 分析 {symbol}...")
            yearly_data = self.analyze_yearly_performance(symbol, years)
            
            for year_data in yearly_data.values():
                all_results.append(year_data)
        
        if not all_results:
            print("✗ 没有有效结果")
            return pd.DataFrame()
        
        # 创建结果DataFrame
        results_df = pd.DataFrame(all_results)
        results_df = results_df.sort_values(['year', 'total_return'], ascending=[True, False])
        
        # 打印汇总
        self.print_summary(results_df)
        
        return results_df
    
    def print_summary(self, df: pd.DataFrame):
        """打印分析汇总"""
        print("\n" + "=" * 80)
        print("年度汇总统计")
        print("=" * 80)
        
        for year in sorted(df['year'].unique()):
            year_data = df[df['year'] == year]
            
            avg_return = year_data['total_return'].mean()
            median_return = year_data['total_return'].median()
            positive_rate = (year_data['total_return'] > 0).mean()
            avg_win_rate = year_data['win_rate'].mean()
            avg_max_dd = year_data['max_drawdown'].mean()
            
            print(f"\n{year}年:")
            print(f"  币种数量: {len(year_data)}")
            print(f"  平均收益率: {avg_return*100:>8.2f}%")
            print(f"  中位数收益率: {median_return*100:>6.2f}%")
            print(f"  正收益币种比例: {positive_rate*100:>5.1f}%")
            print(f"  平均胜率: {avg_win_rate*100:>10.1f}%")
            print(f"  平均最大回撤: {avg_max_dd*100:>8.2f}%")
        
        # 年度Top表现
        print("\n" + "=" * 80)
        print("各年份Top 5表现")
        print("=" * 80)
        
        for year in sorted(df['year'].unique()):
            year_data = df[df['year'] == year].nlargest(5, 'total_return')
            print(f"\n🏆 {year}年 Top 5:")
            print("-" * 60)
            for idx, (_, row) in enumerate(year_data.iterrows(), 1):
                print(f"{idx}. {row['symbol']:<12} "
                      f"收益率: {row['total_return']*100:>7.2f}% "
                      f"胜率: {row['win_rate']*100:>5.1f}% "
                      f"交易: {row['total_trades']:>2}笔")
        
        # 总体统计
        print("\n" + "=" * 80)
        print("总体统计")
        print("=" * 80)
        print(f"总分析记录数: {len(df)}")
        print(f"平均年收益率: {df['total_return'].mean()*100:.2f}%")
        print(f"年收益率标准差: {df['total_return'].std()*100:.2f}%")
        print(f"正收益记录数: {(df['total_return'] > 0).sum()}")
        print(f"负收益记录数: {(df['total_return'] <= 0).sum()}")
        print(f"总体胜率: {df['win_rate'].mean()*100:.1f}%")

def main():
    """主程序"""
    backtester = SimpleYearlyBacktester()
    
    # 获取可用币种
    symbols = backtester.get_available_symbols()
    print(f"可用币种 ({len(symbols)} 个):")
    print(", ".join(symbols[:15]) + ("..." if len(symbols) > 15 else ""))
    
    # 运行分析
    results_df = backtester.run_analysis()
    
    if not results_df.empty:
        # 保存结果
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"yearly_analysis_results_{timestamp}.csv"
        results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n💾 详细结果已保存到: {output_file}")

if __name__ == "__main__":
    main()