import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import matplotlib.pyplot as plt

# 🚀 網頁標題與設定
st.set_page_config(page_title="AI 智能股票交易分析軟體", layout="wide")
st.title("📈 AI 智能股票交易分析軟體 (日線實戰策略版)")

# ----------------- 側邊欄設定 (參數與時間範圍) -----------------
st.sidebar.header("🔧 參數設定")

suffix = st.sidebar.selectbox(
    "1. 請選擇股票類型（市場）：",
    ["上市 (.TW)", "上櫃/興櫃 (.TWO)"]
)
tail = ".TW" if "上市" in suffix else ".TWO"

number = st.sidebar.text_input("2. 請輸入股票數字代碼：", "2330")
ticker = f"{number}{tail}"

# ⏱️ 根據您的需求：新增 K 線圖時間範圍切換
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
    data = yf.download(stock_code, period="2y")
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
        
        # ----------------- 技術指標與訊號計算 -----------------
        df['20MA'] = close_series.rolling(window=20).mean()
        df['RSI'] = ta.momentum.rsi(close_series, window=rsi_period)
        
        macd_obj = ta.trend.MACD(close_series, window_fast=12, window_slow=26, window_sign=9)
        df['MACD_diff'] = macd_obj.macd_diff() # MACD 柱狀體數值
        df['MACD_line'] = macd_obj.macd()
        
        df['5MA_Volume'] = volume_series.rolling(window=5).mean()
        
        # 💡 建立歷史所有天數的訊號標註串列
        buy_signals = [None] * len(df)
        sell_signals = [None] * len(df)
        warn_signals = [None] * len(df)
        
        for i in range(1, len(df)):
            p_price = float(close_series.iloc[i-1])
            c_price = float(close_series.iloc[i])
            c_ma20 = float(df['20MA'].iloc[i])
            c_rsi = float(df['RSI'].iloc[i])
            p_diff = float(df['MACD_diff'].iloc[i-1])
            c_diff = float(df['MACD_diff'].iloc[i])
            c_vol = float(volume_series.iloc[i])
            c_vol_ma5 = float(df['5MA_Volume'].iloc[i])
            
            # 買入條件：站上20MA + MACD金叉 + RSI > 50 + 量能突圍
            if c_price > c_ma20 and p_diff < 0 and c_diff > 0 and c_rsi > 50 and c_vol > c_vol_ma5:
                buy_signals[i] = float(low_series.iloc[i]) * 0.98 # 標註在最低價下方
            # 賣出條件：高位死叉 或 RSI過熱跌破60
            elif (p_diff > 0 and c_diff < 0 and c_rsi > 60) or (c_rsi >= 75):
                sell_signals[i] = float(high_series.iloc[i]) * 1.02 # 標註在最高價上方
            # 留意條件：0軸下出現打底金叉 或 RSI極度低迷反彈
            elif p_diff < 0 and c_diff > 0 and float(df['MACD_line'].iloc[i]) < 0:
                warn_signals[i] = float(low_series.iloc[i]) * 0.99
                
        df['Buy_Sig'] = buy_signals
        df['Sell_Sig'] = sell_signals
        df['Warn_Sig'] = warn_signals

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
            # 即時策略文字建議
            if buy_signals[-1] is not None:
                st.success("🔥 策略建議：強勢進攻點（符合買入訊號）")
            elif sell_signals[-1] is not None:
                st.error("🚨 策略建議：波段結束，果斷減碼/撤退")
            elif warn_signals[-1] is not None:
                st.warning("⚠️ 策略建議：訊號出現，密切留意盤勢變動")
            else:
                st.markdown("<div style='background-color:#f0f2f6;padding:10px;border-radius:5px;font-weight:bold;color:black;'>⏳ 策略建議：常態運行，持股待漲或觀望</div>", unsafe_allow_html=True)

        st.markdown("---")
        
        # ----------------- 📊 第一張圖表：K線與買賣圖標連動成交量 -----------------
        st.subheader(f"📊 區間歷史實戰：K線、20MA 與買賣訊號標註 ({time_frame})")
        
        # 篩選要顯示的區間數據
        plot_df = df.tail(show_days)
        plot_close = close_series.tail(show_days)
        plot_volume = volume_series.tail(show_days)
        
        fig1, (ax1, ax1_sub) = plt.subplots(2, 1, figsize=(14, 7), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
        
        # 主圖：繪製簡化版收盤K線折線與月線
        ax1.plot(plot_df.index, plot_close, label='Close Price', color='dimgray', alpha=0.8, linewidth=2)
        ax1.plot(plot_df.index, plot_df['20MA'], label='20MA (生命線)', color='orange', linewidth=2)
        
        # ✨【重點優化】在主圖上畫出「買、賣、留意」實體圖標！
        ax1.scatter(plot_df.index, plot_df['Buy_Sig'], label='🔼 買入訊號', color='red', marker='^', s=150, zorder=5)
        ax1.scatter(plot_df.index, plot_df['Sell_Sig'], label='🔽 賣出訊號', color='green', marker='v', s=150, zorder=5)
        ax1.scatter(plot_df.index, plot_df['Warn_Sig'], label='⚠️ 留意觀察', color='blue', marker='o', s=100, zorder=5)
        
        ax1.set_title(f"{ticker} Price & Signal Radar", fontsize=14)
        ax1.legend(loc='upper left', prop={'size': 10})
        ax1.grid(True, alpha=0.3)
        
        # 下方連動：成交量
        vol_colors = ['red' if float(close_series.loc[idx]) >= float(open_series.loc[idx]) else 'green' for idx in plot_df.index]
        ax1_sub.bar(plot_df.index, plot_volume.values.flatten(), color=vol_colors, alpha=0.7, label='Volume')
        ax1_sub.set_ylabel('Volume')
        ax1_sub.grid(True, alpha=0.3)
        
        st.pyplot(fig1)
        
        st.markdown("---")
        
        # ----------------- 📊 第二張圖表：MACD純柱狀體融合RSI -----------------
        st.subheader("📈 指標融合空間：MACD 純柱狀體 + RSI 多頭分界線")
        
        fig2, ax2 = plt.subplots(figsize=(14, 4))
        
        # 1. 畫 MACD 純柱狀體 (使用左邊的 Y 軸)
        diff_vals = plot_df['MACD_diff'].values.flatten()
        macd_colors = ['red' if float(x) >= 0 else 'green' for x in diff_vals]
        ax2.bar(plot_df.index, diff_vals, color=macd_colors, alpha=0.4, label='MACD Histogram (Left Y)')
        ax2.axhline(0, color='gray', linestyle='-', alpha=0.5)
        ax2.set_ylabel('MACD Diff')
        ax2.legend(loc='upper left')
        
        # 2. 融合 RSI 到同張圖 (共用 X 軸，建立右邊獨立的 Y 軸)
        ax2_rsi = ax2.twinx()
        ax2_rsi.plot(plot_df.index, plot_df['RSI'], color='purple', linewidth=2, label='RSI (Right Y)')
        ax2_rsi.axhline(50, color='blue', linestyle='--', alpha=0.5, label='Bull/Bear (50)')
        ax2_rsi.axhline(75, color='orange', linestyle=':', alpha=0.6, label='Overbought (75)')
        ax2_rsi.set_ylabel('RSI Value')
        ax2_rsi.legend(loc='upper right')
        
        ax2.grid(True, alpha=0.3)
        
        st.pyplot(fig2)

except Exception as e:
    st.error(f"運行出錯，原因：{e}")
