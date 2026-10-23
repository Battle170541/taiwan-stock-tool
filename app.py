import streamlit as st
import pandas as pd
import requests
import twstock
import yfinance as yf
import datetime

st.set_page_config(page_title="台股機構級操盤與配息診斷系統", layout="wide", page_icon="📈")

st.title("📊 台股機構級專業操盤與配息診斷系統")
st.caption("專業版：前日漲跌價差 | 三大法人與融資券 | 同業競品比較 | 除息填息與二代健保解析 | 即時新聞")

user_input = st.text_input("輸入台股代號或中文名稱（例如：台積電、聯發科、鴻海、00878）：", value="2330").strip()

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

# 同產業推薦對應表
INDUSTRY_PEERS = {
    "2330": [("2303", "聯電"), ("5347", "世界"), ("6770", "力積電")],
    "2454": [("2379", "瑞昱"), ("3034", "聯詠"), ("3529", "力旺")],
    "2317": [("2382", "廣達"), ("3231", "緯創"), ("6669", "緯穎")],
    "2382": [("2317", "鴻海"), ("3231", "緯創"), ("2356", "英業達")],
    "00878": [("0050", "元大台灣50"), ("00919", "群益台灣精選高息"), ("00929", "復華台灣科技優息")],
    "0050": [("00878", "國泰永續高股息"), ("006208", "富邦台50"), ("00919", "群益台灣精選高息")]
}

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

if stock_code:
    clean_code = stock_code.upper()
    data = get_market_data(clean_code)
    chip = get_chip_data(clean_code)

    if not data or data['close'] == 0:
        st.error(f"無法取得代號或名稱【{user_input} ({clean_code})】的資料，請確認名稱是否正確。")
    else:
        # yfinance 補充取得歷史、EPS、配息與新聞
        eps = "N/A"
        news_list = []
        div_amount = 0.0
        div_date = "尚未公告/無紀錄"
        prev_close = data['close']
        
        try:
            ticker_sym = f"{clean_code}.TW"
            session = requests.Session()
            session.headers.update({'User-Agent': 'Mozilla/5.0'})
            yf_stock = yf.Ticker(ticker_sym, session=session)
            info = yf_stock.info
            eps = info.get('trailingEps', 'N/A')
            news_list = yf_stock.news if yf_stock.news else []
            
            hist_yf = yf_stock.history(period="5d")
            if len(hist_yf) >= 2:
                prev_close = hist_yf['Close'].iloc[-2]
                
            dividends = yf_stock.dividends
            if not dividends.empty:
                div_amount = dividends.iloc[-1]
                div_date = dividends.index[-1].strftime('%Y-%m-%d')
        except Exception:
            pass

        # 計算漲跌價差與幅度
        price_diff = data['close'] - prev_close
        price_diff_pct = (price_diff / prev_close) * 100 if prev_close > 0 else 0.0

        # 計算技術均線與支撐壓力
        try:
            s = twstock.Stock(clean_code)
            df_hist = pd.DataFrame(s.data)
            df_hist['Close'] = df_hist['close']
            df_hist['High'] = df_hist['high']
            df_hist['Low'] = df_hist['low']
            df_hist['MA5'] = df_hist['Close'].rolling(5).mean()
            df_hist['MA20'] = df_hist['Close'].rolling(20).mean()
            
            curr_p = data['close']
            ma5 = df_hist['MA5'].iloc[-1]
            ma20 = df_hist['MA20'].iloc[-1]
            
            support_1 = df_hist['Low'].tail(5).min()
            support_2 = df_hist['Low'].tail(20).min()
            resistance_1 = df_hist['High'].tail(5).max()
            resistance_2 = df_hist['High'].tail(20).max()
            
            # 勝率模型
            base_score = 50
            if curr_p > ma5: base_score += 15
            if ma5 > ma20: base_score += 15
            if price_diff > 0: base_score += 10
            
            tomorrow_up_prob = min(max(base_score, 20), 88)
            tomorrow_down_prob = 100 - tomorrow_up_prob

        except Exception:
            curr_p = data['close']
            ma5 = ma20 = curr_p
            support_1 = support_2 = curr_p * 0.95
            resistance_1 = resistance_2 = curr_p * 1.05
            tomorrow_up_prob = 50
            tomorrow_down_prob = 50

        name = data['name']
        pe = chip.get('PEratio', 'N/A')
        dividend_yield = chip.get('YieldRatio', 'N/A')
        is_etf = clean_code.startswith("00")

        # --- 1. 核心行情看板 (含前一日漲跌價) ---
        st.subheader(f"📌 {name} ({clean_code}) [{data['market']}] 即時行情與風險看板")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("最新收盤價", f"{curr_p:.2f}", f"{price_diff:+.2f} ({price_diff_pct:+.2f}%)", delta_color="normal" if price_diff >= 0 else "inverse")
        c2.metric("本益比 (PE)", f"{pe}")
        c3.metric("每股盈餘 (EPS)", f"{eps}")
        c4.metric("預估殖利率", f"{dividend_yield}%")

        # --- 2. 配息政策、填息與二代健保解析 ---
        st.markdown("---")
        st.markdown("### 💰 股利政策、填息天數與二代健保解析")
        d_col1, d_col2 = st.columns(2)
        
        with d_col1:
            st.markdown("#### 📅 配息基本資訊")
            st.write(f"- **最近配息金額**：`{div_amount:.2f}` 元")
            st.write(f"- **最近除息日期**：`{div_date}`")
            st.write(f"- **填息動能評估**：{'📈 屬權值/高息標的，需視填息當日權值股表現與法人買賣超而定' if is_etf else '🔥 個股基本面強勁時，通常具備快速填息能力'}")
            st.write(f"- **配息邏輯模式**：{'ETF (含收益平準金與資本利得分配)' if is_etf else '企業盈餘發放 (54C 股利所得)'}")

        with d_col2:
            st.markdown("#### 🛡️ 二代健保與稅務提醒")
            st.warning("""
            **⚠️ 二代健保補充保費扣繳規定：**
            * **門檻**：只要單筆股利所得（現金股利）**達到或超過 20,000 元**，發放機構就會自動扣繳 **2.11%** 的二代健保補充保費。
            * **所得稅計算**：個股或 ETF 配息需計入綜合所得稅，可選擇「合併計稅（享 8.5% 抵減稅額，上限 8 萬元）」或「分離課費（28%）」。
            """)

        # --- 3. 明日勝率與風險模型 ---
        st.markdown("---")
        st.markdown("### 🎲 明日漲跌機率與風險評估")
        p_col1, p_col2 = st.columns(2)
        with p_col1:
            st.metric("🟢 明日預估上漲機率", f"{tomorrow_up_prob}%", f"下跌風險 {tomorrow_down_prob}%")
            st.progress(tomorrow_up_prob / 100)
            st.write(f"- **前日波動風險**：昨日價差 `{price_diff:+.2f}` 元，今日開盤需留意追價或停損壓力。")
        with p_col2:
            st.markdown("#### 🛡️ 關鍵支撐與壓力防守價")
            st.write(f"- **第一短支撐 (近5日低點)**：`{support_1:.2f}` 元")
            st.write(f"- **月線強支撐 (近20日低點)**：`{support_2:.2f}` 元")
            st.write(f"- **上方短壓區 (近5日高點)**：`{resistance_1:.2f}` 元")

        # --- 4. 同產業類型股票推薦與參考 ---
        st.markdown("---")
        st.markdown("### 🏆 同產業競品與標的推薦對比")
        peers = INDUSTRY_PEERS.get(clean_code, [("2330", "台積電"), ("2317", "鴻海"), ("2454", "聯發科")])
        
        peer_data = []
        for p_code, p_name in peers:
            p_res = get_market_data(p_code)
            if p_res:
                peer_data.append({
                    "代號": p_code,
                    "名稱": p_name,
                    "最新收盤價": p_res['close'],
                    "市場": p_res['market']
                })
        
        if peer_data:
            df_peers = pd.DataFrame(peer_data)
            st.dataframe(df_peers, use_container_width=True)
            st.info("💡 **操作參考**：同產業標的若同步走強，代表該族群有資金集中效應（如半導體或AI伺服器族群連動）；若出現分歧，則需挑選強勢指標股操作。")
        else:
            st.write("暫無同產業對比數據。")

        # --- 5. 近期焦點新聞 ---
        st.markdown("---")
        st.markdown("### 📰 近期市場焦點新聞")
        if news_list:
            for idx, n in enumerate(news_list[:4], 1):
                title = n.get('title', '財經新聞')
                link = n.get('link', '#')
                publisher = n.get('publisher', '財經媒體')
                st.write(f"{idx}. [{title}]({link}) — *{publisher}*")
        else:
            st.write("目前無即時新聞推播。")

        # --- 6. 明日實戰買賣策略 ---
        st.markdown("---")
        st.markdown("### 💡 明日實戰買賣決策建議")
        if tomorrow_up_prob >= 60:
            st.success(f"✅ **偏多操作建議** (勝率 {tomorrow_up_prob}%)：技術面多頭排列。明日若開盤回測第一支撐 `{support_1:.2f}` 未破可低接，嚴守 5 日線停損。")
        elif tomorrow_up_prob <= 40:
            st.warning(f"⚠️ **保守觀望建議** (下跌風險 {tomorrow_down_prob}%)：短線動能偏弱或受前日回檔影響。建議觀望或等待帶量突破短壓 `{resistance_1:.2f}`。")
        else:
            st.info(f"⚖️ **區間震盪策略**：多空拉鋸。建議採取高出低吸，守穩月線 `{support_2:.2f}` 表現。")

        # --- 走勢圖 ---
        st.markdown("### 📉 近期收盤價與均線走勢圖")
        try:
            st.line_chart(df_hist[['Close', 'MA5', 'MA20']].tail(60))
        except Exception:
            st.info("圖表載入中...")
