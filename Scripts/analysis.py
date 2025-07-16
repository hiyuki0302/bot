
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

def atr_analysis(data):
    """下の計算なんか違いますわ！"""
    array_high = data['high'].values
    array_low = data['low'].values
    array_close = data['close'].values
    
    tr1 = (array_high[1:] - array_low[1:])
    tr2 = abs(array_high[1:] - array_close[0:-1])
    tr3 = abs(array_low[1:] - array_close[0:-1])