import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 🚀 網頁基本設定
st.set_page_config(page_title="AI 智能股票交易分析軟體", layout="wide")
st.title("📈 AI 智能股票交易分析軟體 (專業K線均線實戰版)")

# ----------------- 側邊欄設定 -----------------
st.sidebar.header("🔧 參數設定")

suffix = st.sidebar.selectbox(
    "1. 請選擇股票類型（市場）：",
    ["上市 (.TW)", "上櫃/興櫃 (.TWO)"]
)
tail = ".TW" if "上市" in suffix else ".TWO"

number = st.sidebar.text_input("2. 請輸入股票數字代碼：", "2330")
ticker = f"{number}{tail}"

st.sidebar.markdown("---")
st.sidebar.subheader("📅 圖表顯示範圍")
time_frame = st.sidebar.radio("請選擇顯示區間：", ["1個月", "3個月", "6個月"], index=1)
days_map = {"1個月": 22, "3個月": 66, "6個月": 132}
show_days = days_map[time_frame]

st.sidebar.markdown("---")
st.sidebar.subheader("📊 策略最佳參數")
rsi_period = st.sidebar.slider("RSI 天數", min_value=9, max_value=14, value=14)

# 🔍 數據抓取
@st.cache_data
def load_data(stock_code):
    data = yf.download(stock_code, period="1y")
    return data

try:
    df = load_data(ticker)
    
    if df.empty:
        st.error("❌ 找不到該股票數據，請檢查代碼是否正確。")
    else:
        # 🔥 數據結構壓平處理
        close_series = pd.Series(df['Close'].values.flatten(), index=df.index)
        volume_series = pd.Series(df['Volume'].values.flatten(), index=df.index)
        open_series = pd.Series(df['Open'].values.flatten(), index=df.index)
        high_series = pd.Series(df['High'].values.flatten(), index=df.index)
        low_series = pd.Series(df['Low'].values.flatten(), index=df.index)
        
        # 技術指標計算
        df['5MA'] = close_series.rolling(window=5).mean()
        df['10MA'] = close_series.rolling(window=10).mean()
        df['20MA'] = close_series.rolling(window=20).mean()
        df['60MA'] = close_series.rolling(window=60).mean()
        df['RSI'] = ta.momentum.rsi(close_series, window=rsi_period)
        
        macd_obj = ta.trend.MACD(close_series, window_fast=12, window_slow=26, window_sign=9)
        df['MACD_diff'] = macd_obj.macd_diff() 
        df['MACD_line'] = macd_obj.macd()
        df['5MA_Volume'] = volume_series.rolling(window=5).mean()
        
        # 訊號清單初始化
        buy_signals = [None] * len(df)
        sell_signals = [None] * len(df)
        
        # 訊號判斷核心邏輯
        for i in range(1, len(df)):
            c_price = float(close_series.iloc[i])
            c_ma20 = float(df['20MA'].iloc[i])
            c_rsi = float(df['RSI'].iloc[i])
            p_diff = float(df['MACD_diff'].iloc[i-1])
            c_diff = float(df['MACD_diff'].iloc[i])
            c_vol = float(volume_series.iloc[i])
            c_vol_ma5 = float(df['5MA_Volume'].iloc[i])
            
            # 安全單行條件判斷，絕不換行報錯
            cond_buy_1 = (c_price > c_ma20) and (p_diff < 0) and (c_diff > 0)
            cond_buy_2 = (c_rsi > 50) and (c_vol > c_vol_ma5)
            
            cond_sell_1 = (p_diff > 0) and (c_diff < 0) and (c_rsi > 60)
            cond_sell_2 = (c_rsi >= 75)
            
            if cond_buy_1 and cond_buy_2:
                buy_signals[i] = float(low_series.iloc[i]) * 0.96 
            elif cond_sell_1 or cond_sell_2:
                sell_signals[i] = float(high_series.iloc[i]) * 1.04 
                
        df['Buy_Sig'] = buy_signals
        df['Sell_Sig'] = sell_signals

        current_price = float(close_series.iloc[-1])
        prev_price = float(close_series.iloc[-2])
        price_change = current_price - prev_price
        latest_rsi = float(df['RSI'].iloc[-1])
        
        # ----------------- 頂部數據看板 -----------------
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("當前股價", f"${current_price:.2f}", f"{price_change:+.2f}")
        with col2:
            st.metric(f"當前 RSI ({rsi_period}M)", f"{latest_rsi:.2f}")
        with col3:
            if buy_signals[-1] is not None:
                st.success("🔥 策略建議：強勢進攻點（符合買入訊號）")
            elif sell_signals[-1] is not None:
                st.error("🚨 策略建議：波段結束，果斷減碼/撤退")
            else:
                st.markdown("<div style='background-color:#f0f2f6;padding:10px;border-radius:5px;font-weight:bold;color:black;'>⏳ 策略建議：常態運行，持股待漲或觀望</div>", unsafe_allow_html=True)

        st.markdown("---")
        
        # ----------------- 📊 第一張圖表：專業K線、均線與買賣標註 -----------------
        st.subheader(f"📊 區間實戰歷史：專業 K 線、均線群與買賣訊號圖標 ({time_frame})")
        
        plot_df = df.tail(show_days)
        fig1, (ax1, ax1_sub) = plt.subplots(2, 1, figsize=(14, 8), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
        
        # K線棒繪製
        for idx, row in plot_df.iterrows():
            o = float(open_series.loc[idx])
            c = float(close_series.loc[idx])
            h = float(high_series.loc[idx])
            l = float(low_series.loc[idx])
            color = 'red' if c >= o else 'green'
            ax1.vlines(idx, l, h, color=color, linewidth=1.5)
            height = c - o if c >= o else o - c
            bottom = o if c >= o else c
            ax1.bar(idx, height, bottom=bottom, color=color, width=0.6, alpha=0.9)
            
        # 均線與訊號標註
        ax1.plot(plot_df.index, plot_df['5MA'], label='5MA', color='blue', linewidth=1, alpha=0.7)
        ax1.plot(plot_df.index, plot_df['10MA'], label='10MA', color='purple', linewidth=1, alpha=0.7)
        ax1.plot(plot_df.index, plot_df['20MA'], label='20MA (Month Line)', color='orange', linewidth=2)
        ax1.plot(plot_df.index, plot_df['60MA'], label='60MA (Quarter Line)', color='green', linewidth=1.5, alpha=0.8)
        
        ax1.scatter(plot_df.index, plot_df['Buy_Sig'], label='[ Buy Signal ]', color='crimson', marker='^', s=180, zorder=6)
        ax1.scatter(plot_df.index, plot_df['Sell_Sig'], label='[ Sell Signal ]', color='darkgreen', marker='v', s=180, zorder=6)
        
        ax1.set_title(f"{ticker} Technical Candlestick Chart", fontsize=14)
        ax1.legend(loc='upper left', prop={'size': 10})
        ax1.grid(True, alpha=0.3)
        
        # 成交量副圖
        vol_vals = volume_series.tail(show_days).values.flatten()
        vol_colors = ['red' if float(close_series.loc[idx]) >= float(open_series.loc[idx]) else 'green' for idx in plot_df.index]
        ax1_sub.bar(plot_df.index, vol_vals, color=vol_colors, alpha=0.7)
        ax1_sub.set_ylabel('Volume')
        ax1_sub.grid(True, alpha=0.3)
        
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        st.pyplot(fig1)
        st.markdown("---")
        
        # ----------------- 📊 第二張圖表：MACD純柱狀體融合RSI -----------------
        st.subheader("📈 指標融合空間：MACD 純柱狀體 + RSI 多頭分界線")
        
        fig2, ax2 = plt.subplots(figsize=(14, 4))
        
        diff_vals = plot_df['MACD_diff'].values.flatten()
        macd_colors = ['red' if float(x) >= 0 else 'green' for x in diff_vals]
        ax2.bar(plot_df.index, diff_vals, color=macd_colors, alpha=0.4, label='MACD Histogram')
        ax2.axhline(0, color='gray', linestyle='-', alpha=0.5)
        ax2.set_ylabel('MACD Diff')
        ax2.legend(loc='upper left')
        
        ax2_rsi = ax2.twinx()
        ax2_rsi.plot(plot_df.index, plot_df['RSI'], color='purple', linewidth=2, label='RSI Line')
        ax2_rsi.axhline(50, color='blue', linestyle='--', alpha=0.5, label='Bull/Bear Line (50)')
        ax2_rsi.axhline(75, color='orange', linestyle=':', alpha=0.6, label='Overbought (75)')
        ax2_rsi.set_ylabel('RSI Value')
        ax2_rsi.legend(loc='upper right')
        
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        st.pyplot(fig2)

except Exception as e:
    st.error(f"運行出錯，原因：{e}")
