import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 🚀 網頁基本設定
st.set_page_config(page_title="AI 智能股票分析", layout="wide")
st.title("📈 AI 智能股票交易分析軟體 (防當機終極版)")

# ----------------- 側邊欄設定 -----------------
st.sidebar.header("🔧 參數設定")
market = st.sidebar.selectbox("1. 市場", ["上市 (.TW)", "上櫃 (.TWO)"])
tail = ".TW" if "上市" in market else ".TWO"
ticker = f"{st.sidebar.text_input('2. 股票代碼', '2330')}{tail}"

show_days = {"1個月": 22, "3個月": 66, "6個月": 132}[st.sidebar.radio("📅 顯示區間", ["1個月", "3個月", "6個月"], index=1)]
rsi_p = st.sidebar.slider("RSI 天數", 9, 14, 14)

# 🔍 數據抓取
@st.cache_data
def load_data(t): 
    return yf.download(t, period="1y")

try:
    raw_df = load_data(ticker)
    if raw_df.empty: 
        st.error("❌ 找不到數據，請確認代碼。")
    else:
        # 🔥 終極防禦：強制解除 yfinance 的雙層欄位問題
        if isinstance(raw_df.columns, pd.MultiIndex):
            raw_df.columns = raw_df.columns.droplevel(1)
            
        # 提取乾淨數據並清除空值防呆
        df = raw_df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna().copy()
        
        # 指標計算
        df['5MA'] = df['Close'].rolling(5).mean()
        df['10MA'] = df['Close'].rolling(10).mean()
        df['20MA'] = df['Close'].rolling(20).mean()
        df['60MA'] = df['Close'].rolling(60).mean()
        
        # 填補計算初期的 NaN 避免 float() 崩潰
        df['RSI'] = ta.momentum.rsi(df['Close'], window=rsi_p).fillna(50)
        df['MACD_diff'] = ta.trend.MACD(df['Close'], 12, 26, 9).macd_diff().fillna(0)
        
        buy_sig, sell_sig = [None]*len(df), [None]*len(df)
        
        # 🎯 買賣邏輯判斷
        for i in range(2, len(df)):
            c_rsi = df['RSI'].iloc[i]
            p2_d = df['MACD_diff'].iloc[i-2]
            p1_d = df['MACD_diff'].iloc[i-1]
            c_d = df['MACD_diff'].iloc[i]
            
            # 買進：RSI > 50 且 MACD 綠棒轉紅棒 (前日小於0，今日大於0)
            if c_rsi > 50 and p1_d < 0 and c_d > 0:
                buy_sig[i] = df['Low'].iloc[i] * 0.96
            # 賣出：RSI > 75 或 MACD 紅棒連續兩天衰退 (前天>昨天>今天 且 皆為正)
            elif (c_rsi > 75) or (p2_d > p1_d and p1_d > c_d and c_d > 0):
                sell_sig[i] = df['High'].iloc[i] * 1.04
                
        df['Buy'], df['Sell'] = buy_sig, sell_sig
        
        # ----------------- 頂部看板 -----------------
        cur_p = df['Close'].iloc[-1]
        chg = cur_p - df['Close'].iloc[-2]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("當前股價", f"${cur_p:.2f}", f"{chg:+.2f}")
        c2.metric("當前 RSI", f"{df['RSI'].iloc[-1]:.2f}")
        with c3:
            if buy_sig[-1]: st.success("🔥 策略：新起漲點 (買進)")
            elif sell_sig[-1]: st.error("🚨 策略：動能衰退/超買 (賣出)")
            else: st.info("⏳ 策略：常態觀望")
            
        st.markdown("---")
        
        # ----------------- 📊 圖表 1：K線與標註 -----------------
        st.subheader("📊 區間實戰歷史：K 線、均線與訊號標註")
        plot_df = df.tail(show_days)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
        
        # 繪製紅綠 K 線
        for idx, r in plot_df.iterrows():
            o, c, h, l = r['Open'], r['Close'], r['High'], r['Low']
            color = 'red' if c >= o else 'green'
            ax1.vlines(idx, l, h, color=color, linewidth=1.5)
            ax1.bar(idx, abs(c-o), bottom=min(o,c), color=color, width=0.6, alpha=0.9)
            
        # 繪製均線
        ax1.plot(plot_df.index, plot_df['5MA'], label='5MA', color='blue', alpha=0.5)
        ax1.plot(plot_df.index, plot_df['10MA'], label='10MA', color='purple', alpha=0.5)
        ax1.plot(plot_df.index, plot_df['20MA'], label='20MA', color='orange', linewidth=2)
        ax1.plot(plot_df.index, plot_df['60MA'], label='60MA', color='green', alpha=0.5)
        
        # 買賣圖標標註
        ax1.scatter(plot_df.index, plot_df['Buy'], color='crimson', marker='^', s=150, zorder=5, label='Buy')
        ax1.scatter(plot_df.index, plot_df['Sell'], color='darkgreen', marker='v', s=150, zorder=5, label='Sell')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        # 成交量
        vol_color = ['red' if r['Close'] >= r['Open'] else 'green' for _, r in plot_df.iterrows()]
        ax2.bar(plot_df.index, plot_df['Volume'], color=vol_color, alpha=0.6)
        ax2.set_ylabel('Volume')
        ax2.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        st.pyplot(fig)
        
        st.markdown("---")
        
        # ----------------- 📊 圖表 2：MACD + RSI -----------------
        st.subheader("📈 指標融合：MACD 柱狀體 + RSI")
        fig3, ax3 = plt.subplots(figsize=(14, 3.5))
        
        macd_c = ['red' if x >= 0 else 'green' for x in plot_df['MACD_diff']]
        ax3.bar(plot_df.index, plot_df['MACD_diff'], color=macd_c, alpha=0.4, label='MACD')
        ax3.axhline(0, color='gray', alpha=0.5)
        ax3.legend(loc='upper left')
        
        ax4 = ax3.twinx()
        ax4.plot(plot_df.index, plot_df['RSI'], color='purple', linewidth=2, label='RSI')
        ax4.axhline(50, color='blue', linestyle='--', alpha=0.5)
        ax4.axhline(75, color='orange', linestyle=':')
        ax4.legend(loc='upper right')
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        
        st.pyplot(fig3)
        
except Exception as e:
    st.error(f"錯誤：{e}")
