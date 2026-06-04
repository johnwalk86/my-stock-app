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
        # 🔥 打散壓平底層數據
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
        
        # 🛠️【已修復】補回漏掉的完整的 5日均量計算語法
        df['5MA_Volume'] = volume_series.rolling(window=5).mean()
        
        # 💡 建立歷史所有天數的訊號標註串列
        buy_signals = [None] * len(df)
        sell_signals = [None] * len(df)
        
        for i in range(1, len(df)):
            p_price = float(close_series.iloc[i-1])
            c_price = float(close_series.iloc[i])
            c_ma20 = float(df['20MA'].iloc[i])
            c_rsi = float(df['RSI'].iloc[i])
            p_diff = float(df['MACD_diff'].iloc[i-1])
            c_diff = float(df['MACD_diff'].iloc[i])
            c_vol = float(volume_series.iloc[i])
            c_vol_ma5 = float(df['5MA_Volume'].iloc[i])
            
            # 買入交易邏輯：股價在20MA之上 + MACD金叉 + RSI > 50 + 當天成交量 > 5日均量
            if c_price > c_ma20 and p_diff < 0 and c_diff > 0 and c_rsi > 50 and c_vol > c_vol_ma5:
                buy_signals[i] = float(low_series.iloc[i]) * 0.96 # 標註在 K 棒下影線下方
            # 賣出交易邏輯：MACD高位死叉(RSI>60時死叉) 或 RSI進入75以上極度超買區
            elif (p_diff > 0 and c_diff < 0 and c_rsi > 60) or (c_rsi >= 75):
                sell_signals[i] = float(high_series.iloc[i]) * 1.04 # 標註在 K 棒上影線上方
                
        df['Buy_Sig'] = buy_signals
        df['Sell_Sig'] = sell_signals

        # 取得最新一天的狀況作文字看板顯示
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
        
        # ----------------- 📊 第一張圖表：專業K線、5大均線與買賣標註 -----------------
        st.subheader(f"📊 區間實戰歷史：專業 K 線、五大均線群與買賣訊號圖標 ({time_frame})")
        
        # 篩選要顯示的區間數據
        plot_df = df.tail(show_days)
        
        fig1, (ax1, ax1_sub) = plt.subplots(2, 1, figsize=(14, 8), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
        
        # 手動繪製標準K線棒
        for idx, row in plot_df.iterrows():
            o = float(open_series.loc[idx])
            c = float(close_series.loc[idx])
            h = float(high_series.loc[idx])
            l = float(low_series.loc[idx])
            
            color = 'red' if c >= o else 'green'
            
            # 畫上下影線
            ax1.vlines(idx, l, h, color=color, linewidth=1.5)
            # 畫K線實體
            height = c - o if c >= o else o - c
            bottom = o if c >= o else c
            ax1.bar(idx, height, bottom=bottom, color=color, width=0.6, alpha=0.9)
            
        # 繪製 5 大主要均線
        ax1.plot(plot_df.index, plot_df['5MA'], label='5MA', color='blue', linewidth=1, alpha=0.7)
        ax1.plot(plot_df.index, plot_df['10MA'], label='10MA', color='purple', linewidth=1, alpha=0.7)
        ax1.plot(plot_df.index, plot_df['20MA'], label='20MA (月線)', color='orange', linewidth=2)
        ax1.plot(plot_df.index, plot_df['60MA'], label='60MA (季線)', color='green', linewidth=1.5, alpha=0.8)
        if not plot_df['240MA'].isna().all():
            ax1.plot(plot_df.index, plot_df['240MA'], label='240MA (年線)', color='darkred', linewidth=1.5, alpha=0.8)
        
        # 🛠️【已修復】移除無效的 edit_mode 參數，修正畫買賣訊號的 Scatter
        ax1.scatter(plot_df.index, plot_df['Buy_Sig'], label='🔼 買入訊號', color='crimson', marker='^', s=180, zorder=6)
        ax1.scatter(plot_df.index, plot_df['Sell_Sig'], label='🔽 賣出訊號', color='darkgreen', marker='v', s=180, zorder=6)
        
        ax1.set_title(f"{ticker} Technical Candlestick Chart", fontsize=14)
        ax1.legend(loc='upper left', prop={'size': 10})
        ax1.grid(True, alpha=0.3)
        
        # 下方連動：成交量
        vol_colors = ['red' if float(close_series.loc[idx]) >= float(open_series.loc[idx]) else 'green' for idx in plot_df.index]
        ax1_sub.bar(plot_df.index, volume_series.tail(show_days).values.flatten(), color=vol_colors, alpha=0.7)
        ax1_sub.set_ylabel('Volume')
        ax1_sub.grid(True, alpha=0.3)
        
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        
        st.pyplot(fig1)
        st.markdown("---")
        
        # ----------------- 📊 第二張圖表：MACD純柱狀體融合RSI -----------------
        st.subheader("📈 指標融合空間：MACD 純柱狀體 + RSI 多頭分界線")
        
        fig2, ax2 = plt.subplots(figsize=(14, 4))
        
        # 1. 畫 MACD 純柱狀體 (左邊 Y 軸)
        diff_vals = plot_df['MACD_diff'].values.flatten()
        macd_colors = ['red' if float(x) >= 0 else 'green' for x in diff_vals]
        ax2.bar(plot_df.index, diff_vals, color=macd_colors, alpha=0.4, label='MACD Histogram (左軸)')
        ax2.axhline(0, color='gray', linestyle='-', alpha=0.5)
        ax2.set_ylabel('MACD Diff')
        ax2.legend(loc='upper left')
        
        # 2. 融合 RSI 到同張圖 (右邊 Y 軸)
        ax2_rsi = ax2.twinx()
        ax2_rsi.plot(plot_df.index, plot_df['RSI'], color='purple', linewidth=2, label='RSI (右軸)')
        ax2_rsi.axhline(50, color='blue', linestyle='--', alpha=0.5, label='多空分界 (50)')
        ax2_rsi.axhline(75, color='orange', linestyle=':', alpha=0.6, label='超買警戒 (75)')
        ax2_rsi.set_ylabel('RSI Value')
        ax2_rsi.legend(loc='upper right')
        
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        
        st.pyplot(fig2)

except Exception as e:
    st.error(f"運行出錯，原因：{e}")
