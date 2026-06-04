import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import matplotlib.pyplot as plt

# 🚀 網頁標題與設定
st.set_page_config(page_title="AI 智能股票交易分析軟體", layout="wide")
st.title("📈 AI 智能股票交易分析軟體 (模擬版)")
st.subheader("設定您的自選股與交易策略，讓系統自動分析買賣點！")

# ----------------- 側邊欄設定 -----------------
st.sidebar.header("🔧 參數設定")
stock_code = st.sidebar.text_input("輸入股票代碼 (台股請加 .TW)", value="2330.TW")

# 日期選擇
start_date = st.sidebar.date_input("開始日期", value=pd.to_datetime("2026-01-01"))
end_date = st.sidebar.date_input("結束日期", value=pd.to_datetime("2026-06-01"))

# 策略參數
ma_fast = st.sidebar.slider("快線 MA (短天期)", min_value=5, max_value=20, value=5)
ma_slow = st.sidebar.slider("慢線 MA (長天期)", min_value=10, max_value=60, value=20)

# ----------------- 數據抓取與處理 -----------------
@st.cache_data
def load_data(ticker, start, end):
    data = yf.download(ticker, start=start, end=end)
    return data

try:
    df = load_data(stock_code, start_date, end_date)
    
    if df.empty:
        st.error("找不到該股票數據，請檢查代碼是否正確。")
    else:
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
        
        df['MA_Fast'] = ta.trend.sma_indicator(df['Close'], window=ma_fast)
        df['MA_Slow'] = ta.trend.sma_indicator(df['Close'], window=ma_slow)
        
        df['Signal'] = 0
        df.loc[df['MA_Fast'] > df['MA_Slow'], 'Signal'] = 1
        df.loc[df['MA_Fast'] < df['MA_Slow'], 'Signal'] = -1
        df['Position'] = df['Signal'].diff()

        # ----------------- 資訊儀表板 -----------------
        latest_price = df['Close'].iloc[-1]
        price_change = df['Close'].iloc[-1] - df['Close'].iloc[-2]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("當前股價", f"${latest_price:.2f}")
        col2.metric("昨日漲跌", f"${price_change:.2f}")
        
        current_signal = df['Signal'].iloc[-1]
        if current_signal == 1:
            col3.success("🎯 策略建議：偏多操作 (買進/持股)")
        else:
            col3.error("🚨 策略建議：偏空操作 (賣出/空手)")

        # ----------------- 圖表繪製 -----------------
        st.write("### 📊 股價走勢與交易訊號點")
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(df.index, df['Close'], label='Close Price', color='gray', alpha=0.5)
        ax.plot(df.index, df['MA_Fast'], label=f'MA {ma_fast} (Fast)', color='blue')
        ax.plot(df.index, df['MA_Slow'], label=f'MA {ma_slow} (Slow)', color='orange')

        buy_signals = df[df['Position'] == 2]
        ax.scatter(buy_signals.index, df.loc[buy_signals.index, 'Close'], 
                   marker='^', color='red', s=100, label='Buy Signal')

        sell_signals = df[df['Position'] == -2]
        ax.scatter(sell_signals.index, df.loc[sell_signals.index, 'Close'], 
                   marker='v', color='green', s=100, label='Sell Signal')

        ax.set_title(f"{stock_code} Price and Signals")
        ax.legend()
        st.pyplot(fig)

        st.write("### 📋 歷史交易數據明細 (最近10筆)")
        st.dataframe(df[['Close', 'MA_Fast', 'MA_Slow', 'Signal']].tail(10))

except Exception as e:
    st.info("請在左側輸入正確的股票代碼以開始分析。")