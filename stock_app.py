import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import requests
import re

# 🚀 網頁基本設定
st.set_page_config(page_title="AI 智能股票分析", layout="wide")
st.title("📈 AI 智能股票交易分析軟體 (實戰策略版)")

# ----------------- 側邊欄設定 -----------------
st.sidebar.header("🔧 參數設定")
market = st.sidebar.selectbox("1. 市場", ["上市 (.TW)", "上櫃 (.TWO)"])
tail = ".TW" if "上市" in market else ".TWO"
number = st.sidebar.text_input("2. 股票代碼", "2330")
ticker = f"{number}{tail}"

show_days = {"1個月": 22, "3個月": 66, "6個月": 132}[st.sidebar.radio("📅 顯示區間", ["1個月", "3個月", "6個月"], index=1)]
rsi_p = st.sidebar.slider("RSI 天數", 9, 14, 14)

# 🔍 抓取中文名稱爬蟲
@st.cache_data
def get_stock_name(stock_id):
    try:
        url = f"https://tw.stock.yahoo.com/quote/{stock_id}"
        h = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=h, timeout=5)
        match = re.search(r'<title>(.*?)\s*\(\d+\)', res.text)
        return match.group(1) if match else "Unknown"
    except:
        return "Unknown"

# 🔍 數據抓取
@st.cache_data
def load_data(t): 
    return yf.download(t, period="1y")

try:
    # 抓取中文名與歷史數據
    stock_name = get_stock_name(number)
    raw_df = load_data(ticker)
    
    if raw_df.empty: 
        st.error("❌ 找不到數據，請確認代碼。")
    else:
        # 🔥 防禦：強制解除 yfinance 雙層欄位
        if isinstance(raw_df.columns, pd.MultiIndex):
            raw_df.columns = raw_df.columns.droplevel(1)
            
        df = raw_df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna().copy()
        
        # 指標計算
        df['5MA'] = df['Close'].rolling(5).mean()
        df['10MA'] = df['Close'].rolling(10).mean()
        df['20MA'] = df['Close'].rolling(20).mean()
        df['60MA'] = df['Close'].rolling(60).mean()
        
        df['RSI'] = ta.momentum.rsi(df['Close'], window=rsi_p).fillna(50)
        df['MACD_diff'] = ta.trend.MACD(df['Close'], 12, 26, 9).macd_diff().fillna(0)
        
        buy_sig, sell_sig = [None]*len(df), [None]*len(df)
        
        # 🎯 買賣邏輯判斷
        for i in range(2, len(df)):
            c_rsi = df['RSI'].iloc[i]
            p2_d = df['MACD_diff'].iloc[i-2]
            p1_d = df['MACD_diff'].iloc[i-1]
            c_d = df['MACD_diff'].iloc[i]
            
            # 買進：RSI > 50 且 MACD 綠轉紅 (使用括號包覆確保不斷行)
            cond_buy = (c_rsi > 50) and (p1_d < 0) and (c_d > 0)
            
            # 賣出：RSI > 75 或 MACD 紅棒連兩天衰退
            cond_sell_1 = (c_rsi > 75)
            cond_sell_2 = (p2_d > p1_d) and (p1_d > c_d) and (c_d > 0)
            
            if cond_buy:
                buy_sig[i] = df['Low'].iloc[i] * 0.96
            elif cond_sell_1 or cond_sell_2:
                sell_sig[i] = df['High'].iloc[i] * 1.04
                
        df['
