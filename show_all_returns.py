"""列出所有币种收益率汇总"""
import sys
sys.path.insert(0, 'user_data/strategies')
from HuangBaiXianStrategy import HuangBaiXianStrategy

strategy = HuangBaiXianStrategy()
strategy.run_batch(plot=False, save_plot=False)

print()
print('=' * 100)
print('所有币种回测汇总 (按总收益率排序)')
print('=' * 100)
header = f"{'排名':<4} {'币种':<14} {'总收益率':>10} {'年化收益率':>10} {'基准收益率':>10} {'超额收益':>10} {'最大回撤':>10} {'胜率':>8} {'交易笔数':>8}"
print(header)
print('-' * 100)

sorted_metrics = sorted(strategy.metrics.items(), key=lambda x: x[1]['total_return'], reverse=True)
for i, (symbol, m) in enumerate(sorted_metrics, 1):
    excess = m['total_return'] - m['benchmark_return']
    row = (
        f"{i:<4} {symbol:<14}"
        f" {m['total_return']*100:>9.2f}%"
        f" {m['annual_return']*100:>9.2f}%"
        f" {m['benchmark_return']*100:>9.2f}%"
        f" {excess*100:>9.2f}%"
        f" {m['max_drawdown']*100:>9.2f}%"
        f" {m['win_rate']*100:>7.2f}%"
        f" {m['total_trades']:>8}"
    )
    print(row)

print('=' * 100)
