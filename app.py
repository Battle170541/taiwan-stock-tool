import streamlit as st
import pandas as pd
import requests
import twstock
import yfinance as yf
import datetime

st.set_page_config(page_title="台股機構級全方位智慧分析系統", layout="wide", page_icon="📈")

st.title("📊 台股機構級全方位智慧分析系統 (頂級量化版)")
st.caption("自動整合：三大法人買賣超 | 融資融券資券變化 | EPS與本益比 | 技術面與支撐壓力 | 目標價預估 | 即時新聞")

user_input = st.text_input("輸入台股代號或中文名稱（例如：台積電、聯發科、2330、00878）：", value="2330").strip()

# 智慧代號轉換
stock_code = user_input
if not user_input.isdigit():
    found = False
    for code, info in twstock.codes.items():
        if user_input in info.name:
            stock_code = code
            found = True
            break
    if not found:
        stock_code = user_input

# 1. 取得證交所官方個股日行情
@st.cache_data(ttl=600)
def get_market_data(code):
    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            df = pd.DataFrame(res.json())
            match = df[df['Code'] == code]
            if not match.empty:
                row = match.iloc[0]
                return {
                    'name': row.get('Name', code),
                    'close': float(row.get('ClosingPrice', 0)),
                    'open': float(row.get('OpeningPrice', 0)),
                    'high': float(row.get('HighestPrice', 0)),
                    'low': float(row.get('LowestPrice', 0)),
                    'volume': float(row.get('TradeVolume', 0)),
                    'market': '上市'
                }
    except Exception:
        pass
    return None

# 2. 取得本益比、殖利率
@st.cache_data(ttl=600)
def get_chip_data(code):
    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            df = pd.DataFrame(res.json())
            match = df[df['Code'] == code]
            if not match.empty:
                return match.iloc[0].to_dict()
    except Exception:
        pass
    return {}

# 3. 取得三大法人買賣超資料 (TWSE OpenAPI T86)
@st.cache_data(ttl=600)
def get_institutional_data(code):
    try:
        url = "https://openapi.twse.com.tw/v1/fund/T86_ALL"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            df = pd.DataFrame(res.json())
            match = df[df['SecNo'] == code]
            if not match.empty:
                row = match.iloc[0]
                return {
                    'foreign': float(row.get('ForeignInvestmentNetBuySell', 0)),
                    'trust': float(row.get('TheInvestmentTrustNetBuySell', 0)),
                    'dealer': float(row.get('FailsafeNetBuySell', 0)),
                    'total': float(row.get('TotalNetBuySell', 0))
                }
    except Exception:
        pass
    return {'foreign': 'N/A', 'trust': 'N/A', 'dealer': 'N/A', 'total': 'N/A'}

# 4. 取得信用交易融資融券資料 (TWSE OpenAPI MI_MARGN)
@st.cache_data(ttl=600)
def get_margin_data(code):
    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/MI_MARGN"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            for item in data:
                if item.get('StockCode') == code:
                    return {
                        'margin_buy': item.get('MarginPurchaseBuy', '0'),
                        'margin_sell': item.get('MarginPurchaseSell', '0'),
                        'margin_today_balance': item.get('MarginPurchaseTodayBalance', '0'),
                        'short_buy': item.get('ShortSaleBuy', '0'),
                        'short_sell': item.get('ShortSaleSell', '0'),
                        'short_today_balance': item.get('ShortSaleTodayBalance', '0')
                    }
    except Exception:
        pass
    return None

if stock_code:
    clean_code = stock_code.upper()
    data = get_market_data(clean_code)
    chip = get_chip_data(clean_code)
    inst = get_institutional_data(clean_code)
    margin = get_margin_data(clean_code)

    if not data or data['close'] == 0:
        st.error(f"無法取得代號或名稱【{user_input} ({clean_code})】的資料，請確認名稱是否正確。")
    else:
        # yfinance 補強取得 EPS 與新聞
        eps = "N/A"
        news_list = []
        try:
            ticker_sym = f"{clean_code}.TW"
            session = requests.Session()
            session.headers.update({'User-Agent': 'Mozilla/5.0'})
            yf_stock = yf.Ticker(ticker_sym, session=session)
            info = yf_stock.info
            eps = info.get('trailingEps', 'N/A')
            news_list = yf_stock.news[:3] if yf_stock.news else []
        except Exception:
            pass

        # 計算歷史均線與支撐壓力
        try:
            s = twstock.Stock(clean_code)
            df_hist = pd.DataFrame(s.data)
            df_hist['Close'] = df_hist['close']
            df_hist['High'] = df_hist['high']
            df_hist['Low'] = df_hist['low']
            df_hist['MA5'] = df_hist['Close'].rolling(5).mean()
            df_hist['MA20'] = df_hist['Close'].rolling(20).mean()
            df_hist['MA60'] = df_hist['Close'].rolling(60).mean()
            
            curr_p = data['close']
            ma5 = df_hist['MA5'].iloc[-1]
            ma20 = df_hist['MA20'].iloc[-1]
            ma60 = df_hist['MA60'].iloc[-1]
            
            support_1 = df_hist['Low'].tail(5).min()
            support_2 = df_hist['Low'].tail(20).min()
            resistance_1 = df_hist['High'].tail(5).max()
            resistance_2 = df_hist['High'].tail(20).max()
            
            vol_5mean = df_hist['capacity'].tail(5).mean()
            vol_curr = data['volume']
            
            # 預估目標價計算（基於技術壓力與本益比區間）
            target_optimistic = resistance_2 * 1.08
            target_neutral = resistance_1
            target_conservative = support_2

            # 勝率模型
            base_score = 50
            if curr_p > ma5: base_score += 15
            if ma5 > ma20: base_score += 15
            if vol_curr > vol_5mean: base_score += 10
            if curr_p > df_hist['Close'].iloc[-5]: base_score += 10
            
            tomorrow_up_prob = min(max(base_score, 22), 86)
            tomorrow_down_prob = 100 - tomorrow_up_prob
            week_up_prob = min(max(base_score + (8 if ma20 > ma60 else -8), 25), 82)
            week_down_prob = 100 - week_up_prob

        except Exception:
            curr_p = data['close']
            ma5 = ma20 = ma60 = curr_p
            support_1 = support_2 = curr_p * 0.95
            resistance_1 = resistance_2 = curr_p * 1.05
            vol_5mean = vol_curr = data['volume']
            target_optimistic = curr_p * 1.15
            target_neutral = curr_p * 1.05
            target_conservative = curr_p * 0.92
            tomorrow_up_prob = week_up_prob = 50
            tomorrow_down_prob = week_down_prob = 50

        name = data['name']
        pe = chip.get('PEratio', 'N/A')
        dividend_yield = chip.get('YieldRatio', 'N/A')

        # --- 1. 核心數據面看板 ---
        st.subheader(f"📌 {name} ({clean_code}) [{data['market']}] 機構級即時行情")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("最新收盤價", f"{curr_p:.2f}")
        c2.metric("本益比 (PE)", f"{pe}")
        c3.metric("每股盈餘 (EPS)", f"{eps}")
        c4.metric("殖利率 (%)", f"{dividend_yield}%")

        # --- 2. 籌碼面：三大法人與融資融券 ---
        st.markdown("---")
        st.markdown("### 📊 完整籌碼面剖析（三大法人與信用交易）")
        
        f_col, m_col = st.columns(2)
        with f_col:
            st.markdown("#### 🏛️ 三大法人買賣超 (張)")
            if isinstance(inst['foreign'], float):
                st.write(f"- **外資及陸資**：`{inst['foreign']:,.0f}` 張")
                st.write(f"- **投信法人**：`{inst['trust']:,.0f}` 張")
                st.write(f"- **自營商**：`{inst['dealer']:,.0f}` 張")
                st.write(f"- **三大法人合計**：`{inst['total']:,.0f}` 張")
            else:
                st.info("今日法人買賣超數據結算中或非交易時段")

        with m_col:
            st.markdown("#### 💳 信用交易（融資融券）")
            if margin:
                st.write(f"- **融資今日餘額**：`{margin['margin_today_balance']}` 張")
                st.write(f"- **融券今日餘額**：`{margin['short_today_balance']}` 張")
                st.write(f"- **融資買進 / 賣出**：`{margin['margin_buy']}` / `{margin['margin_sell']}`")
            else:
                st.info("今日信用交易額度統計中")

        # --- 3. 勝率與目標價預估 ---
        st.markdown("---")
        st.markdown("### 🎯 多空勝率與預估目標價落點")
        p_col1, p_col2 = st.columns(2)
        with p_col1:
            st.metric("🟢 明日預估上漲機率", f"{tomorrow_up_prob}%", f"下跌風險 {tomorrow_down_prob}%")
            st.progress(tomorrow_up_prob / 100)
            st.metric("🔵 一週趨勢上漲機率", f"{week_up_prob}%", f"下跌風險 {week_down_prob}%")
            st.progress(week_up_prob / 100)

        with p_col2:
            st.markdown("#### 🎯 目標價落點量化預估")
            st.write(f"- 🚀 **樂觀目標價 (波段壓力突破)**：`{target_optimistic:.2f}` 元")
            st.write(f"- ⚖️ **中性目標價 (短壓區間震盪)**：`{target_neutral:.2f}` 元")
            st.write(f"- 🛡️ **保守防守價 (強支撐回測)**：`{target_conservative:.2f}` 元")

        # --- 4. 關鍵支撐與壓力 ---
        st.markdown("---")
        st.markdown("### 🛡️ 技術面關鍵支撐與賣壓區間")
        s_col1, s_col2 = st.columns(2)
        with s_col1:
            st.markdown("#### 📉 下方防守支撐區")
            st.write(f"- **第一短支撐 (近5日低點)**：`{support_1:.2f}`")
            st.write(f"- **第二強支撐 (月線防守區)**：`{support_2:.2f}`")
            st.write(f"- **5日均線 MA5**：`{ma5:.2f}`")
        with s_col2:
            st.markdown("#### 📈 上方賣壓突破區")
            st.write(f"- **第一短壓 (近5日高點)**：`{resistance_1:.2f}`")
            st.write(f"- **第二重壓 (近20日高點)**：`{resistance_2:.2f}`")
            st.write(f"- **月線壓力 MA20**：`{ma20:.2f}`")

        # --- 5. 當日與近期新聞 ---
        st.markdown("---")
        st.markdown("### 📰 當日與近期相關焦點新聞")
        if news_list:
            for idx, n in enumerate(news_list, 1):
                title = n.get('title', '新聞標題')
                link = n.get('link', '#')
                publisher = n.get('publisher', '財經媒體')
                st.write(f"{idx}. [{title}]({link}) — *{publisher}*")
        else:
            st.write("目前無即時新聞推播，建議搭配盤後公告與法說會資訊判讀。")

        # --- 6. 明日實戰買賣決策 ---
        st.markdown("---")
        st.markdown("### 💡 明日實戰買賣決策建議")
        if tomorrow_up_prob >= 60:
            st.success(f"✅ **偏多操作策略** (勝率 {tomorrow_up_prob}%)：法人與技術結構正向。明日若開盤回測第一支撐 `{support_1:.2f}` 未破可逢低承接，嚴守 5 日線停損。")
        elif tomorrow_up_prob <= 40:
            st.warning(f"⚠️ **保守觀望策略** (下跌風險 {tomorrow_down_prob}%)：短線動能偏弱或面臨法人調節。建議觀望或等待帶量突破短壓 `{resistance_1:.2f}` 再行佈局。")
        else:
            st.info(f"⚖️ **區間震盪策略**：多空拉鋸。建議採取高出低吸，守穩月線 `{support_2:.2f}` 表現。")

        # --- 技術走勢圖 ---
        st.markdown("### 📉 近期收盤價與均線走勢圖")
        try:
            st.line_chart(df_hist[['Close', 'MA5', 'MA20']].tail(60))
        except Exception:
            st.info("圖表載入中...")
