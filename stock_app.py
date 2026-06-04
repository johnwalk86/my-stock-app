import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 🚀 網頁標題與設定
st.set_page_config(page_title="AI 智能股票交易分析軟體", layout="wide")
st.title("📈 AI 智能股票交易分析軟體 (專業K線均線實戰版)")

# ----------------- 側邊欄設定 (參數與時間範圍) -----------------
st.sidebar.header("🔧 參數設定")

suffix = st.sidebar.selectbox(
    "1. 請選擇股票類型（市場）：",
    ["上市 (.TW)", "上櫃/興櫃 (.TWO)"]
)
tail = ".TW" if "上市" in suffix else ".TWO"

number = st.sidebar.text_input("2. 請輸入股票數字代碼：", "2330")
ticker = f"{number}{tail}"

# ⏱️ K 線圖時間範圍切換
st.sidebar.markdown("---")
st.sidebar.subheader("📅 圖表顯示範圍")
time_frame = st.sidebar.radio("請選擇顯示區間：", ["1個月", "3個月", "6個月"], index=1)
days_map = {"1個月": 22, "3個月": 66, "6個月": 132}
show_days = days_map[time_frame]

# 📊 指標共識參數
st.sidebar.markdown("---")
st.sidebar.subheader("📊 策略最佳參數")
rsi_period = st.sidebar.slider("RSI 天數", min_value=9, max_value=14, value=14)

# 🔍 數據抓取
@st.cache_data
def load_data(stock_code):
    # 抓取過去三年的數據以確保年線 (240MA) 計算準確
    data = yf.download(stock_code, period="3y")
    return data

try:
    df = load_data(ticker)
    
    if df.empty:
        st.error("❌ 找不到該股票數據，請檢查代碼是否正確。")
    else:
        # 🔥【徹底解決格式核心】打散壓平底層數據
        close_series = pd.Series(df['Close'].values.flatten(), index=df.index)
        volume_series = pd.Series(df['Volume'].values.flatten(), index=df.index)
        open_series = pd.Series(df['Open'].values.flatten(), index=df.index)
        high_series = pd.Series(df['High'].values.flatten(), index=df.index)
        low_series = pd.Series(df['Low'].values.flatten(), index=df.index)
        
        # ----------------- 技術指標與 5 大均線計算 -----------------
        df['5MA'] = close_series.rolling(window=5).mean()
        df['10MA'] = close_series.rolling(window=10).mean()
        df['20MA'] = close_series.rolling(window=20).mean()      # 月線
        df['60MA'] = close_series.rolling(window=60).mean()      # 季線
        df['240MA'] = close_series.rolling(window=240).mean()    # 年線
        
        df['RSI'] = ta.momentum.rsi(close_series, window=rsi_period)
        
        macd_obj = ta.trend.MACD(close_series, window_fast=12, window_slow=26, window_sign=9)
        df['MACD_diff'] = macd_obj.macd_diff() # MACD 柱狀體數值
        df['MACD_line'] = macd_obj.macd()
        
        df['5MA_Volume'] = volume
