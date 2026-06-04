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

# 🔍 抓取三大法人籌碼 (使用 FinMind 免費 API)
@st.cache_data(ttl=3600)
def get_institutional_data(stock_id):
    try:
        # 抓取近 10 天確保能拿到最新交易日的資料
        start_date = (datetime.datetime.now() - datetime.timedelta(days=10)).strftime("%Y-%m-%d")
        url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInstitutionalInvestorsBuySell&data_id={stock_id}&start_date={start_date}"
        res = requests.get(url, timeout=5).json()
        
        if res.get('msg') == 'success' and res.get('data'):
            df_chip = pd.DataFrame(res['data'])
            latest_date = df_chip['date'].max()
            today_df = df_chip[df_chip['date'] == latest_date]
            
            # FinMind 單位是「股」，換算成「張」(/1000)
            def get_net_buy(keyword):
                target = today_df[today_df['name'].str.contains(keyword, na=False)]
                if target.empty: return 0
                return (target['buy'].sum() - target['sell'].sum()) / 1000
                
            return {
                'date': latest_date,
                '外資': get_net_buy('外資'),
                '投信': get_net_buy('投信'),
                '自營商': get_net_buy('自營商')
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
    chip_data = get_institutional_data(number) # 抓取籌碼
    
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
            cond_sell_2 = (p2_d > p1_d) and (p1_d > c_d) and (c_d > 0)
            
            if cond_buy:
                buy_sig[i] = df['Low'].iloc[i] * 0.96
            elif cond_sell_1 or cond_sell_2:
                sell_sig[i] = df['High'].iloc[i] * 1.04
                
        df['Buy'], df['Sell'] = buy_sig, sell_sig
        
        cur_p = df['Close'].iloc[-1]
        chg = cur_p - df['Close'].iloc[-2]
        
        st.markdown(f"### 📌 {stock_name} ({ticker}) 即時戰況")
        
        # ----------------- 頂部看板 (第一排：技術與策略) -----------------
        c1, c2, c3 = st.columns(3)
        c1.metric("當前股價", f"${cur_p:.2f}", f"{chg:+.2f}", delta_color="inverse")
        c2.metric("當前 RSI", f"{df['RSI'].iloc[-1]:.2f}")
        with c3:
            last_rsi = df['RSI'].iloc[-1]
            last_cd = df['MACD_diff'].iloc[-1]
            last_p1d = df['MACD_diff'].iloc[-2]
            last_p2d = df['MACD_diff'].iloc[-3]
            
            if last_rsi > 50 and last_p1d < 0 and last_cd > 0:
                st.success("🔥 策略：MACD翻紅起漲 (買進)")
            elif last_rsi > 75:
                st.error("🚨 策略：RSI 極度超買 (賣出)")
            elif last_p2d > last_p1d and last_p1d > last_cd and last_cd > 0:
                st.warning("⚠️ 策略：MACD 動能衰退 (減碼)")
            else:
                st.info("⏳ 策略：常態觀望")
        
        st.markdown("---")
        
        # ----------------- 頂部看板 (第二排：籌碼面) -----------------
        st.markdown("#### 🏢 三大法人最新籌碼動向 (單位：張)")
        f1, f2, f3 = st.columns(3)
        
        if chip_data:
            chip_date = chip_data['date']
            # 將數值轉為整數
            f_val, t_val, d_val = int(chip_data['外資']), int(chip_data['投信']), int(chip_data['自營商'])
            
            # 判斷顏色符號
            def format_chip(val):
                return f"+{val:,}" if val > 0 else f"{val:,}"

            f1.metric(f"外資買賣超 ({chip_date})", f"{format_chip(f_val)}", delta_color="inverse")
            f2.metric(f"投信買賣超 ({chip_date})", f"{format_chip(t_val)}", delta_color="inverse")
            f3.metric(f"自營商買賣超 ({chip_date})", f"{format_chip(d_val)}", delta_color="inverse")
        else:
            st.warning("⏳ 籌碼 API 讀取中或達免費上限，請稍後重試。")
            
        st.markdown("---")
        
        # ----------------- 📊 圖表 1：K線與標註 -----------------
        st.subheader("📊 區間實戰歷史：K 線、均線與訊號標註")
        plot_df = df.tail(show_days)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
        
        for idx, r in plot_df.iterrows():
            o, c, h, l = r['Open'], r['Close'], r['High'], r['Low']
            color = 'red' if c >= o else 'green'
            ax1.vlines(idx, l, h, color=color, linewidth=1.5)
            ax1.bar(idx, abs(c-o), bottom=min(o,c), color=color, width=0.6, alpha=0.9)
            
        ax1.plot(plot_df.index, plot_df['5MA'], label='5MA', color='blue', alpha=0.5)
        ax1.plot(plot_df.index, plot_df['10MA'], label='10MA', color='purple', alpha=0.5)
        ax1.plot(plot_df.index, plot_df['20MA'], label='20MA', color='orange', linewidth=2)
        ax1.plot(plot_df.index, plot_df['60MA'], label='60MA', color='green', alpha=0.5)
        
        ax1.scatter(plot_df.index, plot_df['Buy'], color='crimson', marker='^', s=150, zorder=5, label='Buy')
        ax1.scatter(plot_df.index, plot_df['Sell'], color='darkgreen', marker='v', s=150, zorder=5, label='Sell')
        
        ax1.set_title(f"[{ticker}] Technical Chart", fontsize=14)
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        
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
