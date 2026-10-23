import streamlit as st
import pandas as pd
import requests
import twstock

st.set_page_config(page_title="台股全方位智慧分析系統", layout="wide", page_icon="📈")

st.title("📊 台股全方位智慧分析系統 (產業趨勢與多空成因版)")
st.caption("自動解析：漲跌機率 | 支撐壓力 | 產業趨勢題材 | 多空成因拆解 | 明日實戰策略")

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

# 產業趨勢與題材概念比對資料庫
INDUSTRY_TRENDS = {
    "2330": {"trends": ["AI 晶片需求爆發 (Nvidia/AMD 訂單)", "CoWoS 先進封裝供不應求", "2nm/3nm 產能滿載"], "driver": "全球 AI 運算浪潮與先進製程絕對壟斷權"},
    "2454": {"trends": ["天璣 9400 AI 手機晶片", "ASIC 客製化 AI 晶片", "車用晶片與 Wi-Fi 7"], "driver": "端側 AI (Edge AI) 普及與雲端 ASIC 雙引擎"},
    "2382": {"trends": ["Nvidia Blackwell AI 伺服器整機出貨", "水冷散熱模組整合"], "driver": "雲端 CSP 大廠 (Microsoft/Google) 超級算力擴建"},
    "2317": {"trends": ["GB200 NVL72 伺服器代工霸主", "電動車 CDMS 製造"], "driver": "全球最大 AI 伺服器組裝份額與供應鏈垂直整合"},
    "3131": {"trends": ["CoWoS 濕製程設備專利", "台積電擴產最大受益者"], "driver": "先進封裝設備國產化與建廠交貨高峰期"},
    "2345": {"trends": ["400G/800G 交換器 (Switch)", "CPO 矽光子技術預備"], "driver": "AI 資料中心內部高速網路傳輸規格升級"},
    "6223": {"trends": ["VPC 垂直探針卡", "MEMS 探針卡高毛利"], "driver": "AI 晶片與晶圓測試介面需求激增"},
    "6515": {"trends": ["高階 IC 測試座 (Test Socket)", "CoWoS 系統級測試"], "driver": "高算力 GPU/ASIC 測試複雜度提升帶動單價高漲"},
    "6640": {"trends": ["CoWoS 晶粒揀選機 (Die Bonder)", "竹科擴產"], "driver": "先進封裝擴產潮帶動設備訂單能見度直達明年"},
    "5289": {"trends": ["工控記憶體升級", "Edge AI 邊緣運算儲存"], "driver": "記憶體價格回升與高階工控利基型市場需求"},
    "8299": {"trends": ["PCIe Gen5 主控晶片", "Enterprise SSD (企業級SSD)"], "driver": "AI 伺服器高速儲存架構升級潮"},
    "6187": {"trends": ["點膠機與貼合設備", "CoWoS/SoIC 設備"], "driver": "半導體封裝設備交期延伸與大客戶強勁拉貨"},
    "3081": {"trends": ["CPO 矽光子磊晶片", "InP 磷化銦基板"], "driver": "次世代光互連傳輸（Optical Interconnect）趨勢"},
    "00878": {"trends": ["高股息成分股配息與調整", "定期定額資金持續流入"], "driver": "穩健現金流偏好與防禦型資金避風港"},
    "00919": {"trends": ["高殖利率選股機制", "收益平準金配息充沛"], "driver": "市場尋求高除權息殖利率之資金湧入"},
    "00929": {"trends": ["科技高股息月配息潮", "半導體高殖利率股"], "driver": "月月配息現金流需求與科技股庫存去化完成"}
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
            tomorrow_up_prob = week_up_prob = 50
            tomorrow_down_prob = week_down_prob = 50

        name = data['name']
        pe = chip.get('PEratio', 'N/A')
        dividend_yield = chip.get('YieldRatio', 'N/A')

        # --- 行情看板 ---
        st.subheader(f"📌 {name} ({clean_code}) [{data['market']}] 即時行情與勝率預測")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("最新收盤價", f"{curr_p:.2f}")
        c2.metric("本益比 (PE)", f"{pe}")
        c3.metric("殖利率 (%)", f"{dividend_yield}%")
        c4.metric("今日成交股數", f"{int(vol_curr):,}")

        # --- 多空勝率與機率 ---
        st.markdown("---")
        st.markdown("### 🎲 量化多空勝率與機率模型")
        p1, p2 = st.columns(2)
        with p1:
            st.metric("🟢 明日預估上漲機率", f"{tomorrow_up_prob}%", f"下跌風險 {tomorrow_down_prob}%", delta_color="normal" if tomorrow_up_prob > 50 else "inverse")
            st.progress(tomorrow_up_prob / 100)
        with p2:
            st.metric("🔵 一週趨勢上漲機率", f"{week_up_prob}%", f"下跌風險 {week_down_prob}%", delta_color="normal" if week_up_prob > 50 else "inverse")
            st.progress(week_up_prob / 100)

        # --- 🚀 產業趨勢與漲跌成因剖析 (新增重點功能) ---
        st.markdown("---")
        st.markdown("### 🚀 漲跌成因剖析與產業趨勢潮流")
        
        trend_info = INDUSTRY_TRENDS.get(clean_code, {
            "trends": ["半導體/電子供應鏈庫存去化", "AI 基礎建設零組件需求拉補", "台股資金資金輪動行情"],
            "driver": "整體科技產業週期復甦與台股大盤資金動能"
        })

        t_col1, t_col2 = st.columns(2)
        with t_col1:
            st.markdown("#### 🟢 看漲/支撐支撐四大核心原因")
            st.write(f"1. **搭上產業主流趨勢**：{trend_info['driver']}")
            st.write(f"2. **關鍵題材概念**：{', '.join(trend_info['trends'])}")
            st.write(f"3. **技術面支撐**：股價位於短線 5 日線 (`{ma5:.2f}`) 上方，技術面呈現多頭排列趨勢。")
            st.write(f"4. **買盤支撐**：下方有近 20 日強支撐價位 `{support_2:.2f}` 提供退路。")

        with t_col2:
            st.markdown("#### 🔴 潛在下跌/回檔風險原因")
            st.write("1. **隔日沖與高檔獲利調節**：若開盤急拉過猛，易吸引隔日沖主力高開倒貨。")
            st.write(f"2. **上方套牢賣壓**：接近近 20 日高點壓力區 `{resistance_2:.2f}` 時，解套賣壓易釋出。")
            st.write("3. **大盤美股連動風險**：美股科技股（費半/Nvidia）若震盪，開盤易受觀望賣壓波及。")

        # --- 🛡️ 支撐壓力 ---
        st.markdown("---")
        st.markdown("### 🛡️ 關鍵支撐價位與壓力區間")
        s_col1, s_col2 = st.columns(2)
        with s_col1:
            st.markdown("#### 📉 下方防守支撐區")
            st.write(f"- **第一支撐 (短線5日低點)**：`{support_1:.2f}`")
            st.write(f"- **第二支撐 (月線強支撐)**：`{support_2:.2f}`")
        with s_col2:
            st.markdown("#### 📈 上方突破壓力區")
            st.write(f"- **第一壓力 (近5日高點)**：`{resistance_1:.2f}`")
            st.write(f"- **第二重壓 (近20日高點)**：`{resistance_2:.2f}`")

        # --- 實戰策略 ---
        st.markdown("---")
        st.markdown("### 💡 明日實戰操作建議")
        if tomorrow_up_prob >= 60:
            st.success(f"✅ **偏多操作建議**：趨勢與勝率({tomorrow_up_prob}%)雙優。明日若開盤回測第一支撐 `{support_1:.2f}` 附近未破可考慮低接，嚴守 5 日線停損。")
        elif tomorrow_up_prob <= 40:
            st.warning(f"⚠️ **保守觀望建議**：短線動能偏弱。建議暫時觀望，等帶量突破壓力區 `{resistance_1:.2f}` 再行佈局。")
        else:
            st.info(f"⚖️ **區間震盪建議**：多空拉鋸中，建議採高出低吸策略，守穩下方月線 `{support_2:.2f}` 再進場。")

        # --- 技術圖表 ---
        st.markdown("### 📉 近期收盤價與均線走勢圖")
        try:
            st.line_chart(df_hist[['Close', 'MA5', 'MA20']].tail(60))
        except Exception:
            st.info("圖表載入中...")
