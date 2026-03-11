"""
调试脚本：检查策略的 startup_candle_count
"""
import sys
sys.path.insert(0, 'd:/myProject/LH/freqtrade')

from freqtrade.configuration import Configuration
from freqtrade.resolvers.strategy_resolver import StrategyResolver

# 加载配置
config = Configuration.from_files(['user_data/config.json'])
config['timerange'] = '20230503-20260308'
config['timeframe'] = '1d'

# 加载策略
strategy = StrategyResolver.load_strategy(config)

print(f"Strategy: {strategy.strategy_name}")
print(f"startup_candle_count: {strategy.startup_candle_count}")
print(f"Interface version: {strategy.interface_version}")
