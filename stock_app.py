import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

st.set_page_config(page_title="AI Stock App", layout="wide")
st.title("📈 AI 智能股票交易分析軟體 (實戰策略優化版)")

st.sidebar.header("🔧 參數設定")
suffix = st.sidebar.selectbox("1. 市場", ["上市 (.TW)", "上櫃 (.TWO)"])
tail = ".TW" if "上市" in suffix else ".TWO"
number = st.sidebar.text_input("2. 股票代碼", "2330")
ticker = f"{number}{tail}"

time_frame = st.sidebar.radio("📅 顯示區間", ["1個月", "3個月", "6個月"], index=1)
days_map = {"1個月": 22, "3個月": 66, "6個月": 132}
show_days = days_map[time_frame]
rsi_period = st.sidebar.slider("RSI 天數", 9, 14, 14)

@st.cache_data
def load_data(stock_code):
    return yf.download(stock_code, period="1y")

try:
    df = load_data(ticker)
    if df.empty:
        st.error("❌ 找不到該股票數據。")
    else:
        close_series = pd.Series(df['Close'].values.flatten(), index=df.index)
        volume_series = pd.Series(df['Volume'].values.flatten(), index=df.index)
        open_series = pd.Series(df['Open'].values.flatten(), index=df.index)
        high_series = pd.Series(df['High'].values.flatten(), index=df.index)
        low_series = pd.Series(df['Low'].values.flatten(), index=df.index)
        
        df['5MA'] = close_series.rolling(5).mean()
        df['10MA'] = close_series.rolling(10).mean()
        df['20MA'] = close_series.rolling(20).mean()
        df['60MA'] = close_series.rolling(60).mean()
        df['RSI'] = ta.momentum.rsi(close_series, window=rsi_period)
        
        macd_obj = ta.trend.MACD(close_series, 12, 26, 9)
        df['MACD_diff'] = macd_obj.macd_diff() 
        df['5MA_Volume'] = volume_series.rolling(5).mean()
        
        buy_signals, sell_signals = [None]*len(df), [None]*len(df)
        
        for i in range(2, len(df)):
            c_rsi = float(df['RSI'].iloc[i])
            p1_diff, c_diff = float(df['MACD_diff'].iloc[i-1]), float(df['MACD_diff'].iloc[i])
            p2_diff = float(df['MACD_diff'].iloc[i-2])
            
            # 🔥 新邏輯：RSI > 50 且 MACD 綠轉紅買進
            if c_rsi > 50 and p1_diff < 0 and c_diff > 0:
                buy_signals[i] = float(low_series.iloc[i]) * 0.96
            # 🔥 新邏輯：RSI > 75 或 MACD 紅棒連續兩天縮短賣出
            elif (c_rsi > 75) or (p2_diff > p1_diff and p1_diff > c_diff and c_diff > 0):
                sell_signals[i] = float(high_series.iloc[i]) * 1.04
                
        df['Buy_Sig'], df['Sell_Sig'] = buy_signals, sell_signals
        current_
