import pandas as pd

def rsi_analysis(data, period:int=14):
    """RSI計算"""
    delta = data['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def atr_analysis(data, period: int = 14):
    """ATR計算"""
    df = data.copy()
    
    # 前日終値
    prev_close = df['close'].shift(1) # １つずれる。
    
    # True Rangeの最大値を求める。
    tr1 = df['high'] - df['low']
    tr2 = abs(df['high'] - prev_close)
    tr3 = abs(df['low'] - prev_close)
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # ATR(True Rangeの移動平均)
    atr = true_range.rolling(window=period).mean()
    atr_percent = (atr / df['close']) * 100
    
    return atr_percent