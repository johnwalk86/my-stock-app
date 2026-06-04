import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import requests
import re
import datetime

# 🚀 網頁基本設定
st.set_page_config(page_title="AI 智能股票分析", layout="wide")
st.title("📈 AI 智能股票交易分析軟體 (技術籌碼雙效版)")

# ----------------- 側邊欄設定 -----------------
st.sidebar.header("🔧 參數設定")
market = st.sidebar.selectbox("1. 市場", ["上市 (.TW)", "上櫃 (.TWO)"])
tail = ".TW" if "上市" in market else ".TWO"
number = st.sidebar.text_input("2. 股票代碼", "2330")
ticker = f"{number}{tail}"

show_days = {"1個月": 22, "3個月": 66, "6個月": 132}[st.sidebar.radio("📅 顯示區間", ["1個月", "3個月", "6個月"], index=1)]
rsi_p = st.sidebar.slider("RSI 天數", 9, 14, 14)

# 🔍 抓取股票名稱
@st.cache_data
def get_stock_name(full_ticker):
    try:
        info = yf.Ticker(full_ticker).info
        return info.get('shortName', '指定個股')
    except:
        return "指定個股"

# 🔍 抓取三大法人籌碼 (FinMind 修正英文代碼版)
@st.cache_data(ttl=3600)
def get_institutional_data(stock_id):
    try:
        start_date = (datetime.datetime.now() - datetime.timedelta(days=10)).strftime("%Y-%m-%d")
        url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInstitutionalInvestorsBuySell&data_id={stock_id}&start_date={start_date}"
        res = requests.get(url, timeout=5).json()
        
        if res.get('msg') == 'success' and res.get('data'):
            df_chip = pd.DataFrame(res['data'])
            latest_date = df_chip['date'].max()
            today_df = df_chip[df_chip['date'] == latest_date]
            
            # 🔥 修正：FinMind 的後台欄位其實是英文！
            def get_net_buy(keyword):
                target = today_df[today_df['name'].str.contains(keyword, na=False, case=False)]
                if target.empty: return 0
                return (target['buy'].sum() - target['sell'].sum()) / 1000
                
            return {
                'date': latest_date,
                '外資': get_net_buy('Foreign_Investor'),
                '投信': get_net_buy('Investment_Trust'),
                '自營商': get_net_buy('Dealer') # 包含 Dealer_self 與 Dealer_Hedging
            }
    except:
        pass
    return None

# 🔍 數據抓取
@st.cache_data
def load_data(t): 
    return yf.download(t, period="1y")

try:
    stock_name = get_stock_name(ticker)
    raw_df = load_data(ticker)
    chip_data = get_institutional_data(number)
    
    if raw_df.empty: 
        st.error("❌ 找不到數據，請確認代碼。")
    else:
        if isinstance(raw_df.columns, pd.MultiIndex):
            raw_df.columns = raw_df.columns.droplevel(1)
            
        df = raw_df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna().copy()
        
        df['5MA'] = df['Close'].rolling(5).mean()
        df['10MA'] = df['Close'].rolling(10).mean()
        df['20MA'] = df['Close'].rolling(20).mean()
        df['60MA'] = df['Close'].rolling(60).mean()
        
        df['RSI'] = ta.momentum.rsi(df['Close'], window=rsi_p).fillna(50)
        df['MACD_diff'] = ta.trend.MACD(df['Close'], 12, 26, 9).macd_diff().fillna(0)
        
        buy_sig, sell_sig = [None]*len(df), [None]*len(df)
        
        for i in range(2, len(df)):
            c_rsi = df['RSI'].iloc[i]
            p2_d = df['MACD_diff'].iloc[i-2]
            p1_d = df['MACD_diff'].iloc[i-1]
            c_d = df['MACD_diff'].iloc[i]
            
            cond_buy = (c_rsi > 50) and (p1_d < 0) and (c_d > 0)
            cond_sell_1 = (c_rsi > 75)
            cond_sell_2 = (p2_d > p1_d)
