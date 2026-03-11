import subprocess
import sys
import os
from pathlib import Path
import tempfile
import json


def run_backtest_for_pair(pair, strategy="KDJStrategy", timeframe="1d"):
    """
    使用命令行运行单个交易对的回测
    """
    # 创建临时配置文件
    config_data = {
        "max_open_trades": 1,
        "stake_currency": "USDT",
        "stake_amount": 100,
        "dry_run": True,
        "timeframe": timeframe,
        "strategy": strategy,
        "datadir": "user_data/data/binance",
        "db_url": "sqlite:///test.db",
        "export": "trades",
        "fee": 0.001,
        "exchange": {
            "name": "binance",
            "key": "",
            "secret": "",
            "sandbox": False,
            "ccxt_config": {"enableRateLimit": True},
            "ccxt_async_config": {"enableRateLimit": True},
            "pair_whitelist": [pair],
            "pair_blacklist": []
        },
        "pairlists": [
            {"method": "StaticPairList"}
        ]
    }
    
    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_config:
        json.dump(config_data, temp_config)
        temp_config_path = temp_config.name

    cmd = [
        sys.executable, "-m", "freqtrade", "backtesting",
        "--config", temp_config_path,
        "--strategy", strategy,
        "--timeframe", timeframe,
        "--pairs", pair
    ]
    
    print(f"正在测试 {pair}...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"成功完成 {pair} 的回测")
            # 提取并显示关键结果
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if 'BACKTESTING REPORT' in line or 'TOTAL' in line or 'WINRATE' in line:
                    print(f"  {line.strip()}")
            return True, result.stdout
        else:
            print(f"回测 {pair} 时出错: {result.stderr}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        print(f"回测 {pair} 时超时")
        return False, "Timeout"
    finally:
        # 清理临时文件
        os.unlink(temp_config_path)


def main():
    print("开始测试KDJ策略在BTC/USDT和ETH/USDT上的表现...")
    
    # 测试的交易对
    pairs_to_test = ['BTC/USDT', 'ETH/USDT']
    
    results = {}
    
    for pair in pairs_to_test:
        success, output = run_backtest_for_pair(pair)
        results[pair] = {'success': success, 'output': output}
    
    print("\n" + "="*80)
    print("KDJ策略测试总结:")
    print("="*80)
    
    for pair, result in results.items():
        print(f"\n{pair}:")
        if result['success']:
            # 解析输出，提取关键指标
            output_lines = result['output'].split('\n')
            for line in output_lines:
                if 'TOTAL' in line and 'TRADES' in line:
                    print(f"  {line.strip()}")
                elif 'WINRATE' in line:
                    print(f"  {line.strip()}")
                elif 'AVG DURATION' in line:
                    print(f"  {line.strip()}")
                elif 'PROFIT' in line and '%' in line:
                    print(f"  {line.strip()}")
        else:
            print(f"  回测失败: {result['output']}")


if __name__ == "__main__":
    main()