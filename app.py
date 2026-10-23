import streamlit as st
import pandas as pd
import requests
import twstock

st.set_page_config(page_title="台股智慧全自動診斷系統", layout="wide", page_icon="📈")

st.title("📊 台股全方位智慧分析系統 (官方直連版)")
st.caption("直連證交所官方 OpenAPI，突破雲端封鎖，支援任意代號與中文名稱自動解析")

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

# 取得證交所上市即時/最新收盤價資料
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

# 取得三大法人與本益比資料
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
        st.error(f"無法取得代號或名稱【{user_input} ({clean_code})】的資料，請確認名稱是否正確（或直接輸入數字代號）。")
    else:
        # 利用 twstock 取得歷史資料來算均線
        stock_history = None
        try:
            s = twstock.Stock(clean_code)
            if len(s.data) > 20:
                df_hist = pd.DataFrame(s.data)
                df_hist['Close'] = df_hist['close']
                df_hist['MA5'] = df_hist['Close'].rolling(5).mean()
                df_hist['MA20'] = df_hist['Close'].rolling(20).mean()
                df_hist['MA60'] = df_hist['Close'].rolling(60).mean()
                stock_history = df_hist
        except Exception:
            pass

        curr_p = data['close']
        vol = data['volume']
        name = data['name']
        
        pe = chip.get('PEratio', 'N/A')
        dividend_yield = chip.get('YieldRatio', 'N/A')

        st.subheader(f"📌 {name} ({clean_code}) [{data['market']}] 核心數據")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("最新收盤價", f"{curr_p:.2f}")
        c2.metric("本益比 (PE)", f"{pe}")
        c3.metric("殖利率 (%)", f"{dividend_yield}%")
        c4.metric("今日成交股數", f"{int(vol):,}")

        st.markdown("### 📈 技術面與均線架構")
        if stock_history is not None and not stock_history.empty:
            ma5 = stock_history['MA5'].iloc[-1]
            ma20 = stock_history['MA20'].iloc[-1]
            ma60 = stock_history['MA60'].iloc[-1]
            
            t1, t2, t3 = st.columns(3)
            t1.metric("5日線 (短線防守)", f"{ma5:.2f}")
            t2.metric("20日線 (月線)", f"{ma20:.2f}")
            t3.metric("60日線 (季線)", f"{ma60:.2f}")

            st.line_chart(stock_history[['Close', 'MA5', 'MA20']].tail(60))
        else:
            st.info("正在載入歷史均線數據...")

        is_etf = clean_code.startswith("00")
        st.markdown("### 💰 股利政策與收益來源結構")
        if is_etf:
            st.info("💡 **標的屬性：ETF 基金**\n- **配息模式**：常見為月配、季配或半年配。\n- **收益來源組成**：54C股利所得、資本利得、收益平準金。")
        else:
            st.info("💡 **標的屬性：一般企業股票**\n- **配息模式**：年配或季配。\n- **收益來源組成**：企業累積盈餘分配。")

        st.markdown("---")
        st.markdown("### 🤖 一鍵複製：Gemini 全方位極致診斷指令")
        st.info("點擊下方區塊右上角的複製按鈕，直接貼給 Gemini，產出明日買賣決策！")

        prompt = f"""請擔任台股頂級量化籌碼與技術面專家，針對【{name} ({clean_code})】進行「鉅細靡遺」的全方位診斷，並直接告訴我明天該如何操作。

【官方即時彙整數據】
1. 基本面與評價：
   - 最新收盤價：{curr_p:.2f} (市場：{data['market']})
   - 本益比：{pe} | 殖利率：{dividend_yield}%
   - 今日成交量：{int(vol):,} 股
2. 籌碼與技術面：
   - 相關法人籌碼與信用交易狀態
   - 請根據台股盤勢與目前價位進行多空評估。

【請針對以下項目進行精準診斷，並給出明確決策】：
1. 🎯 明日操作決策（核心）：明天開盤我該「買進、賣出、做空、還是觀望」？請給出明確的進場點、停損價、停利價與預期持有週期。
2. ⚡ 隔日沖與短線主力軌跡：研判今日是否有隔日沖主力鎖碼？明日開盤是否有高開拉高倒貨的賣壓風險？
3. 📊 籌碼面與信用交易：三大法人最近買賣超趨勢與融資融券變化。
4. 🛡️ 股價支撐與賣壓：買盤承接力道如何？上方套牢賣壓重不重？給出具體支撐區與壓力區數字。
5. 💰 除權息與配息分析：配息金額評價與填息機率評估。
6. 📈 完整技術面判讀：均線排列與明日K線多空型態預測。
7. 🎯 目標價與長短線佈局：短線(1~2週)與長線(3~6個月)趨勢，並給出樂觀/中性/悲觀目標價。"""

        st.code(prompt, language="markdown")
