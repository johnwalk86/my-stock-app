import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import matplotlib.pyplot as plt

# 🚀 網頁標題與設定
st.set_page_config(page_title="AI 智能股票交易分析軟體", layout="wide")
st.title("📈 AI 智能股票交易分析軟體 (日線實戰策略版)")

# ----------------- 側邊欄設定 (改良版下拉選單) -----------------
st.sidebar.header("🔧 參數設定")

suffix = st.sidebar.selectbox(
    "1. 請選擇股票類型（市場）：",
    ["上市 (.TW)", "上櫃/興櫃 (.TWO)"]
)
tail = ".TW" if "上市" in suffix else ".TWO"

number = st.sidebar.text_input("2. 請輸入股票數字代碼：", "2330")
ticker = f"{number}{tail}"

# 日線級別特有最佳共識參數
st.sidebar.markdown("---")
st.sidebar.subheader("📊 策略最佳參數 (已鎖定日線共識)")
rsi_period = st.sidebar.slider("RSI 天數", min_value=9, max_value=14, value=14)
st.sidebar.info("MACD 預設全球共識參數: (12, 26, 9)\n均線預設生命線: 20MA")

# 🔍 數據抓取
@st.cache_data
def load_data(stock_code):
    # 抓取過去兩年的數據以確保均線與量能計算準確
    data = yf.download(stock_code, period="2y")
    return data

try:
    df = load_data(ticker)
    
    if df.empty:
        st.error("❌ 找不到該股票數據，請檢查代碼是否正確。")
    else:
        # 🔥【關鍵修正核心】將 Yahoo Finance 的多維結構壓平成一維
        close_series = df['Close'].squeeze()
        volume_series = df['Volume'].squeeze()
        
        # ----------------- 技術指標計算 -----------------
        # 1. 20MA 均線
        df['20MA'] = close_series.rolling(window=20).mean()
        
        # 2. RSI (14)
        df['RSI'] = ta.momentum.rsi(close_series, window=rsi_period)
        
        # 3. MACD (12, 26, 9)
        macd_obj = ta.trend.MACD(close_series, window_fast=12, window_slow=26, window_sign=9)
        df['MACD_line'] = macd_obj.macd()
        df['MACD_signal'] = macd_obj.macd_signal()
        df['MACD_diff'] = macd_obj.macd_diff() # 柱狀體
        
        # 4. 成交量與 5日均量
        df['5MA_Volume'] = volume_series.rolling(window=5).mean()
        
        # 取得最新一天的數據進行策略比對
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        current_price = float(close_series.iloc[-1])
        prev_price = float(close_series.iloc[-2])
        price_change = current_price - prev_price
        
        latest_rsi = float(latest['RSI'])
        latest_macd_line = float(latest['MACD_line'])
        latest_ma20 = float(latest['20MA'])
        latest_vol = float(volume_series.iloc[-1])
        latest_vol_ma5 = float(df['5MA_Volume'].iloc[-1])
        
        # 買入條件檢查
        c_macd_gold = (prev['MACD_diff'] < 0 and latest['MACD_diff'] > 0) # MACD金叉
        c_macd_below_0 = (latest_macd_line < 0) # 0軸下方
        c_rsi_above_50 = (latest_rsi > 50) # RSI > 50
        c_above_20ma = (current_price > latest_ma20) # 站上20MA
        c_vol_boom = (latest_vol > latest_vol_ma5) # 量能大於5日均量
        
        # 賣出條件檢查
        c_rsi_overbought = (latest_rsi >= 75) # RSI進入超買區
        c_macd_dead = (prev['MACD_diff'] > 0 and latest['MACD_diff'] < 0) # MACD高位死叉
        c_rsi_drop_60 = (latest_rsi < 60)
        
        # ----------------- 頂部數據看板 -----------------
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("當前股價", f"${current_price:.2f}", f"{price_change:+.2f}")
        with col2:
            st.metric("當前 RSI ({})".format(rsi_period), f"{latest_rsi:.2f}")
        with col3:
            # 綜合策略推演
            if c_above_20ma and c_macd_gold and c_rsi_above_50:
                st.success("🔥 策略建議：強勢進攻點（符合最強買入訊號）")
            elif c_macd_gold and c_macd_below_0:
                st.info("🌱 策略建議：築底分批建倉訊號")
            elif c_macd_dead and c_rsi_drop_60:
                st.error("🚨 策略建議：波段結束，果斷減碼/逃命")
            elif c_rsi_overbought:
                st.warning("⚠️ 策略建議：極度超買，請勿追高隨時撤退")
            else:
                st.markdown("<div style='background-color:#f0f2f6;padding:10px;border-radius:5px;font-weight:bold;color:black;'>⏳ 策略建議：常態運行，持股待漲或觀望</div>", unsafe_allow_html=True)

        st.markdown("---")
        
        # ----------------- 圖像化區塊一：日線操作手冊雷達（檢查表） -----------------
        st.subheader("📋 日線級別實戰策略 - 當前訊號圖像化檢查表")
        
        grid1, grid2, grid3, grid4, grid5 = st.columns(5)
        
        with grid1:
            status = "🟢 符合" if c_macd_gold else "⚪ 未觸發"
            st.markdown(f"**1. MACD 金叉**\n### {status}")
            st.caption("右側動能反轉確認")
            
        with grid2:
            status = "🟢 符合" if c_rsi_above_50 else "⚪ 未觸發"
            st.markdown(f"**2. RSI > 50**\n### {status}")
            st.caption("多頭多空分界線突破")
            
        with grid3:
            status = "🟢 符合" if c_above_20ma else "⚪ 未觸發"
            st.markdown(f"**3. 股價站上月線**\n### {status}")
            st.caption("站穩 20MA 生命線")
            
        with grid4:
            status = "🟢 爆量" if c_vol_boom else "⚪ 均量"
            st.markdown(f"**4. 成交量突圍**\n### {status}")
            st.caption("大於 5 日均量確認")
            
        with grid5:
            # 逃命預警
            if c_rsi_overbought or (c_macd_dead and c_rsi_drop_60):
                status = "🔴 警報觸發"
            else:
                status = "🟢 安全"
            st.markdown(f"**5. 風險狀態**\n### {status}")
            st.caption("高檔死叉/超買風險")

        st.markdown("---")
        
        # ----------------- 圖像化區塊二：專業多圖連動圖表 -----------------
        st.subheader("📈 股價、量能與指標三合一主圖連動")
        
        # 畫出高質量的多合一圖表
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10), sharex=True, gridspec_kw={'height_ratios': [2, 1, 1]})
        
        # 主圖：股價 + 20MA
        ax1.plot(df.index[-120:], close_series.iloc[-120:], label='Close Price', color='dimgray', alpha=0.8)
        ax1.plot(df.index[-120:], df['20MA'].iloc[-120:], label='20MA (Month Line)', color='orange', linewidth=2)
        ax1.set_title(f"{ticker} Real-time Analysis (Last 120 Days)", fontsize=14)
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        # 副圖一：RSI + 50分界線 + 75超買線
        ax2.plot(df.index[-120:], df['RSI'].iloc[-120:], color='purple', label='RSI ({})'.format(rsi_period))
        ax2.axhline(50, color='blue', linestyle='--', alpha=0.5, label='Bull/Bear (50)')
        ax2.axhline(75, color='red', linestyle=':', alpha=0.6, label='Overbought (75)')
        ax2.set_ylabel('RSI')
        ax2.legend(loc='upper left')
        ax2.grid(True, alpha=0.3)
        
        # 副圖二：MACD 柱狀體與快慢線
        ax3.plot(df.index[-120:], df['MACD_line'].iloc[-120:], color='black', label='MACD')
        ax3.plot(df.index[-120:], df['MACD_signal'].iloc[-120:], color='blue', linestyle='--', label='Signal')
        # 柱狀體翻紅翻綠
        colors = ['red' if x >= 0 else 'green' for x in df['MACD_diff'].iloc[-120:]]
        ax3.bar(df.index[-120:], df['MACD_diff'].iloc[-120:], color=colors, label='Histogram', alpha=0.6)
        ax3.axhline(0, color='gray', linestyle='-', alpha=0.5)
        ax3.set_ylabel('MACD')
        ax3.legend(loc='upper left')
        ax3.grid(True, alpha=0.3)
        
        st.pyplot(fig)
        
        # ----------------- 圖像化區塊三：快速對照表 -----------------
        st.markdown("### 📊 實戰策略核心快速對照表")
        st.table(pd.DataFrame({
            "情境": ["築底階段", "強勢進攻", "轉弱警訊", "崩跌風險"],
            "MACD 狀態": ["0軸下金叉，柱狀體翻紅", "0軸上運行，開口向上", "高位死叉，柱狀體翻綠", "0軸下死叉運行"],
            "RSI 狀態": ["低點抬高（底背離）", "穩定在 50 - 70 之間突破", "跌破 50 或 頂背離", "低於 30 但持續鈍化"],
            "量能與均線配合": ["成交量開始溫和放大", "股價站穩 20MA + 爆量", "跌破 20MA 月線", "均線下彎空頭排列"],
            "核心建議動作": ["分批建倉佈局", "重倉持股待漲", "果斷減碼撤退", "觀望，切勿盲目接刀"]
        }))

except Exception as e:
    st.error(f"運行出錯，原因：{e}")
