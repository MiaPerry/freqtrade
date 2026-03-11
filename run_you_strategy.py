"""
运行 you.py 策略并统计各币种收益情况
策略逻辑:
  - BTC MA120 作为牛熊过滤
  - 选动量最强的山寨币 (30日涨幅最大)
  - 入场条件: 收盘价 > MA60
  - 止损: 收盘价 < 入场价 - 2*ATR  或  收盘价 < MA60
"""

import sys
import os
import pandas as pd
import numpy as np

# 数据路径（自动定位项目根目录）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "user_data", "data", "binance")
TIMEFRAME = "1d"


# =====================
# 数据加载
# =====================
def load_data():
    data = {}
    for file in os.listdir(DATA_PATH):
        if not file.endswith(f"-{TIMEFRAME}.feather"):
            continue
        symbol = file.split("-")[0]
        df = pd.read_feather(os.path.join(DATA_PATH, file))
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
        df = df.sort_index()
        data[symbol] = df
    print(f"加载完成: {len(data)} 个币种")
    return data


# =====================
# 指标计算
# =====================
def calc_indicators(df):
    df = df.copy()
    df["ma20"]  = df["close"].rolling(20).mean()
    df["ma60"]  = df["close"].rolling(60).mean()
    df["ma120"] = df["close"].rolling(120).mean()
    df["momentum"] = df["close"] / df["close"].shift(30)
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - df["close"].shift()).abs()
    tr3 = (df["low"]  - df["close"].shift()).abs()
    df["tr"]  = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["atr"] = df["tr"].rolling(14).mean()
    return df


# =====================
# 回测（含逐笔交易记录）
# =====================
def backtest(data):
    btc = data["BTC_USDT"]
    btc_bull = btc["close"] > btc["ma120"]
    dates = btc_bull.index

    equity      = 1.0
    equity_curve = []

    position    = None   # 当前持仓币种
    entry_price = 0.0
    stop        = 0.0

    # 逐笔交易记录
    trades = []
    # 各币种累计统计
    symbol_stats = {}   # symbol -> {"hold_days": int, "pnl_list": [float]}

    for date in dates:
        # BTC 熊市，清仓
        if not btc_bull.loc[date]:
            if position is not None:
                # 强制平仓
                df = data[position]
                if date in df.index:
                    close_price = df.loc[date, "close"]
                    ret = close_price / entry_price - 1
                    equity *= (1 + ret)
                    trades.append({
                        "symbol":      position,
                        "entry_date":  entry_date,
                        "exit_date":   date,
                        "entry_price": entry_price,
                        "exit_price":  close_price,
                        "return":      ret,
                        "exit_reason": "BTC熊市"
                    })
                    _update_stats(symbol_stats, position, ret, entry_date, date)
                position = None
            equity_curve.append(equity)
            continue

        # 空仓，寻找入场
        if position is None:
            # 找动量最强的币
            scores = {}
            for sym, df in data.items():
                if sym == "BTC_USDT":
                    continue
                if date not in df.index:
                    continue
                row = df.loc[date]
                if pd.isna(row["momentum"]):
                    continue
                scores[sym] = row["momentum"]

            if not scores:
                equity_curve.append(equity)
                continue

            coin = max(scores, key=scores.get)
            df   = data[coin]

            if date not in df.index:
                equity_curve.append(equity)
                continue

            row = df.loc[date]
            if row["close"] > row["ma60"]:
                position    = coin
                entry_price = row["close"]
                entry_date  = date
                stop        = entry_price - row["atr"] * 2

        # 持仓管理
        else:
            df = data[position]
            if date not in df.index:
                equity_curve.append(equity)
                continue

            row = df.loc[date]
            ret = row["close"] / entry_price - 1

            # 止损 或 跌破MA60 → 平仓
            if row["close"] < stop or row["close"] < row["ma60"]:
                equity *= (1 + ret)
                trades.append({
                    "symbol":      position,
                    "entry_date":  entry_date,
                    "exit_date":   date,
                    "entry_price": entry_price,
                    "exit_price":  row["close"],
                    "return":      ret,
                    "exit_reason": "止损" if row["close"] < stop else "跌破MA60"
                })
                _update_stats(symbol_stats, position, ret, entry_date, date)
                position = None
            else:
                # 更新权益（持仓浮动）
                daily_ret   = row["close"] / entry_price - 1
                equity     *= (1 + daily_ret)
                entry_price = row["close"]

        equity_curve.append(equity)

    return dates, equity_curve, trades, symbol_stats


def _update_stats(symbol_stats, symbol, ret, entry_date, exit_date):
    if symbol not in symbol_stats:
        symbol_stats[symbol] = {"hold_days": 0, "pnl_list": []}
    hold = (exit_date - entry_date).days
    symbol_stats[symbol]["hold_days"] += hold
    symbol_stats[symbol]["pnl_list"].append(ret)


# =====================
# 打印报告
# =====================
def print_report(dates, equity_curve, trades, symbol_stats, data):
    total_return = equity_curve[-1] - 1

    # 最大回撤
    curve = np.array(equity_curve)
    peak = np.maximum.accumulate(curve)
    drawdown = (curve / peak - 1)
    max_dd = drawdown.min()

    # 年化
    n_days = (dates[-1] - dates[0]).days
    annual = (1 + total_return) ** (365 / n_days) - 1 if n_days > 0 else 0

    print()
    print("=" * 70)
    print("  you.py 策略整体回测结果")
    print("=" * 70)
    print(f"  回测期间:   {dates[0].date()} ~ {dates[-1].date()}  ({n_days} 天)")
    print(f"  总收益率:   {total_return*100:>+.2f}%")
    print(f"  年化收益率: {annual*100:>+.2f}%")
    print(f"  最大回撤:   {max_dd*100:.2f}%")
    print(f"  总交易笔数: {len(trades)} 笔")
    print("=" * 70)

    if not trades:
        print("  无成交记录")
        return

    trades_df = pd.DataFrame(trades)
    wins = (trades_df["return"] > 0).sum()
    win_rate = wins / len(trades_df)
    avg_win  = trades_df[trades_df["return"] > 0]["return"].mean() if wins > 0 else 0
    avg_loss = trades_df[trades_df["return"] <= 0]["return"].mean() if (len(trades_df)-wins) > 0 else 0

    print(f"  胜率:       {win_rate*100:.2f}%  ({wins}胜/{len(trades_df)-wins}负)")
    print(f"  平均盈利:   {avg_win*100:>+.2f}%")
    print(f"  平均亏损:   {avg_loss*100:>+.2f}%")
    print()

    # ── 各币种参与统计 ──
    print("-" * 90)
    print(f"{'币种':<14} {'交易次数':>6} {'总收益':>9} {'平均收益':>9} {'最大单笔':>9} {'最差单笔':>9} {'胜率':>7} {'持仓天数':>8}")
    print("-" * 90)

    rows = []
    for sym, stat in symbol_stats.items():
        pnl = stat["pnl_list"]
        total_pnl = np.prod([1 + r for r in pnl]) - 1
        avg_pnl   = np.mean(pnl)
        max_pnl   = max(pnl)
        min_pnl   = min(pnl)
        wr        = sum(1 for r in pnl if r > 0) / len(pnl)
        hold      = stat["hold_days"]
        rows.append((sym, len(pnl), total_pnl, avg_pnl, max_pnl, min_pnl, wr, hold))

    # 按总收益排序
    rows.sort(key=lambda x: x[2], reverse=True)

    for sym, cnt, tot, avg, mx, mn, wr, hold in rows:
        print(f"{sym:<14} {cnt:>6}   {tot*100:>+7.2f}%  {avg*100:>+7.2f}%  "
              f"{mx*100:>+7.2f}%  {mn*100:>+7.2f}%  {wr*100:>5.1f}%  {hold:>7}天")

    print("-" * 90)
    print()

    # ── 逐笔交易明细（最近20笔）──
    print("最近 20 笔交易明细:")
    print(f"{'币种':<14} {'入场日期':<12} {'出场日期':<12} {'收益':>9} {'出场原因'}")
    print("-" * 65)
    for t in trades[-20:]:
        print(f"{t['symbol']:<14} {str(t['entry_date'].date()):<12} "
              f"{str(t['exit_date'].date()):<12} {t['return']*100:>+7.2f}%  {t['exit_reason']}")
    print()


# =====================
# 入口
# =====================
if __name__ == "__main__":
    print("正在加载数据...")
    data = load_data()

    print("计算指标...")
    for sym in data:
        data[sym] = calc_indicators(data[sym])

    print("开始回测...")
    dates, equity_curve, trades, symbol_stats = backtest(data)

    print_report(dates, equity_curve, trades, symbol_stats, data)
