import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import requests
import re
import datetime

# 🚀 網頁基本設定與隱藏預設選單
st.set_page_config(page_title="AI 智能股票分析", layout="wide")

# 🎨 注入自訂 CSS，打造現代化「浮雕圓角卡片」質感
st.markdown("""
    <style>
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #f0f2f6;
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease-in-out;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0px 6px 15px rgba(0, 0, 0, 0.1);
    }
    </style>
""", unsafe_allow_html=True)

st.title("📈 AI 智能股票交易分析軟體")
st.markdown("<p style='color: #666666; font-size: 1.1em; margin-top: -15px;'>技術指標與三大法人籌碼・雙效視覺化儀表板</p>", unsafe_allow_html=True)
st.divider()

# ----------------- 側邊欄設定 -----------------
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2942/2942253.png", width=80)
st.sidebar.header("🔧 戰略參數設定")
market = st.sidebar.selectbox("1. 市場", ["上市 (.TW)", "上櫃 (.TWO)"])
tail = ".TW" if "上市" in market else ".TWO"
number = st.sidebar.text_input("2. 股票代碼", "2330")
ticker = f"{number}{tail}"

show_days = {"1個月": 22, "3個月": 66, "6個月": 132}[st.sidebar.radio("📅 顯示區間", ["1個月", "3個月", "6個月"], index=1)]
rsi_p = st.sidebar.slider("RSI 天數", 9, 14, 14)
st.sidebar.divider()
st.sidebar.caption("© 2026 AI Stock Trading System")

# 🔍 抓取股票名稱
@st.cache_data
def get_stock_name(full_ticker):
    try:
        info = yf.Ticker(full_ticker).info
        return info.get('shortName', '指定個股')
    except:
        return "指定個股"

# 🔍 抓取三大法人籌碼
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
            
            def get_net_buy(keyword):
                target = today_df[today_df['name'].str.contains(keyword, na=False, case=False)]
                if target.empty: return 0
                return (target['buy'].sum() - target['sell'].sum()) / 1000
                
            return {
                'date': latest_date,
                '外資': get_net_buy('Foreign_Investor'),
                '投信': get_net_buy('Investment_Trust'),
                '自營商': get_net_buy('Dealer')
            }
    except:
        pass
    return None

# 🔍 數據抓取與計算
@st.cache_data
def load_data(t): 
    return yf.download(t, period="1y")

try:
    stock_name = get_stock_name(ticker)
    raw_df = load_data(ticker)
    chip_data = get_institutional_data(number)
    
    if raw_df.empty: 
        st.error("❌ 找不到數據，請確認代碼是否正確。")
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
            cond_sell_2 = (p2_d > p1_d) and (p1_d > c_d) and (c_d > 0)
            
            if cond_buy:
                buy_sig[i] = df['Low'].iloc[i] * 0.97
            elif cond_sell_1 or cond_sell_2:
                sell_sig[i] = df['High'].iloc[i] * 1.03
                
        df['Buy'], df['Sell'] = buy_sig, sell_sig
        
        cur_p = df['Close'].iloc[-1]
        prev_p = df['Close'].iloc[-2]
        chg = cur_p - prev_p
        pct_chg = (chg / prev_p) * 100
        
        st.markdown(f"### 📌 【 {stock_name} 】 {ticker} 即時戰況")
        
        # ----------------- 頂部看板 1：技術與策略 -----------------
        c1, c2, c3 = st.columns(3)
        c1.metric("當前股價", f"${cur_p:.2f}", f"{chg:+.2f} ({pct_chg:+.2f}%)", delta_color="inverse")
        c2.metric("當前 RSI", f"{df['RSI'].iloc[-1]:.2f}")
        with c3:
            last_rsi = df['RSI'].iloc[-1]
            last_cd = df['MACD_diff'].iloc[-1]
            last_p1d = df['MACD_diff'].iloc[-2]
            last_p2d = df['MACD_diff'].iloc[-3]
            
            if last_rsi > 50 and last_p1d < 0 and last_cd > 0:
                st.success("🔥 策略系統：MACD翻紅起漲 (建議買進)")
            elif last_rsi > 75:
                st.error("🚨 策略系統：RSI 極度超買 (建議賣出)")
            elif last_p2d > last_p1d and last_p1d > last_cd and last_cd > 0:
                st.warning("⚠️ 策略系統：MACD 動能衰退 (建議減碼)")
            else:
                st.info("⏳ 策略系統：盤整無明顯訊號 (常態觀望)")
        
        st.write("")
        
        # ----------------- 頂部看板 2：籌碼面 -----------------
        f1, f2, f3 = st.columns(3)
        if chip_data:
            chip_date = chip_data['date']
            f_val, t_val, d_val = int(chip_data['外資']), int(chip_data['投信']), int(chip_data['自營商'])
            
            f1.metric(f"🏢 外資買賣超 (更新: {chip_date})", f"{f_val:,} 張", f"{f_val:,}", delta_color="inverse")
            f2.metric(f"🏢 投信買賣超 (更新: {chip_date})", f"{t_val:,} 張", f"{t_val:,}", delta_color="inverse")
            f3.metric(f"🏢 自營商買賣超 (更新: {chip_date})", f"{d_val:,} 張", f"{d_val:,}", delta_color="inverse")
        else:
            st.warning("⏳ 法人籌碼 API 讀取中，請稍後重新整理。")
            
        st.divider()
        
        # ----------------- 📊 圖表 1：K線與標註 -----------------
        st.markdown("#### 📊 區間實戰歷史：專業 K 線與策略圖標")
        plot_df = df.tail(show_days)
        
        # 建立高質感透明背景圖表
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 7), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
        fig.patch.set_alpha(0)
        ax1.set_facecolor('white')
        ax2.set_facecolor('white')
        
        for ax in [ax1, ax2]:
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(True, linestyle='--', alpha=0.4, color='#b0bec5')
        
        for idx, r in plot_df.iterrows():
            o, c, h, l = r['Open'], r['Close'], r['High'], r['Low']
            color = '#ff3333' if c >= o else '#00b050'
            ax1.vlines(idx, l, h, color=color, linewidth=1.5)
            ax1.bar(idx, abs(c-o), bottom=min(o,c), color=color, width=0.6, alpha=0.9)
            
        ax1.plot(plot_df.index, plot_df['5MA'], label='5MA', color='#2196f3', linewidth=1.2, alpha=0.8)
        ax1.plot(plot_df.index, plot_df['10MA'], label='10MA', color='#9c27b0', linewidth=1.2, alpha=0.8)
        ax1.plot(plot_df.index, plot_df['20MA'], label='20MA', color='#ff9800', linewidth=2.5)
        ax1.plot(plot_df.index, plot_df['60MA'], label='60MA', color='#4caf50', linewidth=1.5, alpha=0.8)
        
        # 圖標增加黑邊框，更有立體感
        ax1.scatter(plot_df.index, plot_df['Buy'], color='#ff1744', marker='^', s=160, edgecolors='black', linewidths=0.5, zorder=5, label='Buy Point')
        ax1.scatter(plot_df.index, plot_df['Sell'], color='#00c853', marker='v', s=160, edgecolors='black', linewidths=0.5, zorder=5, label='Sell Point')
        
        ax1.legend(loc='upper left', frameon=True, framealpha=0.9)
        
        vol_color = ['#ff3333' if r['Close'] >= r['Open'] else '#00b050' for _, r in plot_df.iterrows()]
        ax2.bar(plot_df.index, plot_df['Volume'], color=vol_color, alpha=0.6)
        ax2.set_ylabel('Volume', color='gray')
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.tight_layout()
        st.pyplot(fig)
        
        st.divider()
        
        # ----------------- 📊 圖表 2：MACD + RSI -----------------
        st.markdown("#### 📈 趨勢指標融合：MACD 動能柱 + RSI 多空線")
        fig3, ax3 = plt.subplots(figsize=(14, 3.5))
        fig3.patch.set_alpha(0)
        ax3.set_facecolor('white')
        ax3.spines['top'].set_visible(False)
        ax3.grid(True, linestyle='--', alpha=0.4, color='#b0bec5')
        
        macd_c = ['#ff3333' if x >= 0 else '#00b050' for x in plot_df['MACD_diff']]
        ax3.bar(plot_df.index, plot_df['MACD_diff'], color=macd_c, alpha=0.5, label='MACD Diff')
        ax3.axhline(0, color='gray', alpha=0.6)
        ax3.legend(loc='upper left')
        
        ax4 = ax3.twinx()
        ax4.spines['top'].set_visible(False)
        ax4.plot(plot_df.index, plot_df['RSI'], color='#673ab7', linewidth=2.5, label='RSI Line')
        ax4.axhline(50, color='#2196f3', linestyle='--', alpha=0.7, linewidth=1.5)
        ax4.axhline(75, color='#ff9800', linestyle=':', alpha=0.8, linewidth=1.5)
        ax4.legend(loc='upper right')
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.tight_layout()
        st.pyplot(fig3)
        
except Exception as e:
    st.error(f"系統運行錯誤：{e}")
