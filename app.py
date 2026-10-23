import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import twstock

st.set_page_config(page_title="台股智慧全自動診斷系統", layout="wide", page_icon="📈")

st.title("📊 台股全方位智慧分析系統 (全自動智能解析版)")
st.caption("支援輸入任意台股代號或中文名稱：自動聯動技術、籌碼、除權息與 AI 決策")

user_input = st.text_input("輸入台股代號或中文名稱（例如：台積電、聯發科、2330、00878）：", value="台積電").strip()

# 利用 twstock 自動智慧對應任意中文名稱或代號
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

def get_twse_chip_data(stock_id):
    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            df = pd.DataFrame(res.json())
            stock_info = df[df['Code'] == stock_id]
            if not stock_info.empty:
                return stock_info.iloc[0].to_dict()
    except Exception:
        pass
    return {}

if stock_code:
    clean_code = stock_code.upper()
    ticker_symbol = f"{clean_code}.TW" if clean_code.isdigit() else clean_code

    with st.spinner(f"正在自動聯動雲端資料庫查詢 【{user_input} ({clean_code})】..."):
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        stock = yf.Ticker(ticker_symbol, session=session)
        hist = stock.history(period="6m")
        
        if hist.empty and clean_code.isdigit():
            ticker_symbol = f"{clean_code}.TWO"
            stock = yf.Ticker(ticker_symbol, session=session)
            hist = stock.history(period="6m")

        if hist.empty:
            st.error(f"無法取得代號或名稱【{user_input}】的數據，請確認名稱是否正確（或直接輸入數字代號）。")
        else:
            info = stock.info
            twse_info = get_twse_chip_data(clean_code)
            
            hist['MA5'] = hist['Close'].rolling(5).mean()
            hist['MA20'] = hist['Close'].rolling(20).mean()
            hist['MA60'] = hist['Close'].rolling(60).mean()
            
            curr_p = hist['Close'].iloc[-1]
            prev_p = hist['Close'].iloc[-2]
            chg = curr_p - prev_p
            chg_pct = (chg / prev_p) * 100
            
            high_20 = hist['High'].tail(20).max()
            low_20 = hist['Low'].tail(20).min()
            vol_curr = hist['Volume'].iloc[-1]
            vol_ma5 = hist['Volume'].tail(5).mean()

            dividends = stock.dividends
            last_div_amount = dividends.iloc[-1] if not dividends.empty else 0.0
            last_div_date = dividends.index[-1].strftime('%Y-%m-%d') if not dividends.empty else "無紀錄/尚未公告"
            div_yield = info.get('dividendYield', 0)
            div_yield_str = f"{div_yield * 100:.2f}%" if div_yield else f"{twse_info.get('YieldRatio', 'N/A')}%"

            quote_type = info.get('quoteType', '')
            is_etf = quote_type == 'ETF' or clean_code.startswith("00")
            
            st.subheader(f"📌 {info.get('longName', clean_code)} ({clean_code}) 核心數據")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("最新收盤價", f"{curr_p:.2f}", f"{chg:+.2f} ({chg_pct:+.2f}%)")
            c2.metric("最新/最近配息金額", f"{last_div_amount:.2f} 元" if last_div_amount else "無")
            c3.metric("最近除息日期", f"{last_div_date}")
            c4.metric("預估年化殖利率", div_yield_str)

            st.markdown("### 💰 股利政策與收益來源結構")
            d1, d2 = st.columns(2)
            if is_etf:
                d1.info("💡 **標的屬性：ETF 基金**\n- **配息模式**：常見為月配、季配或半年配。\n- **收益來源組成**：54C股利所得、資本利得、收益平準金。")
                d2.warning("⚠️ **配息提醒**：若配息來源含有高比例平準金或資本利得，除息前需評估填息動能。")
            else:
                d1.info("💡 **標的屬性：一般企業股票**\n- **配息模式**：年配或季配。\n- **收益來源組成**：主要為企業獲利盈餘分配。")
                d2.warning("⚠️ **填息評估**：個股需評估基本面成長力道與補充保費。")

            st.markdown("### 📈 技術面均線與支撐壓力")
            t1, t2, t3, t4 = st.columns(4)
            t1.metric("5日線 (短線防守)", f"{hist['MA5'].iloc[-1]:.2f}")
            t2.metric("20日線 (月線)", f"{hist['MA20'].iloc[-1]:.2f}")
            t3.metric("60日線 (季線)", f"{hist['MA60'].iloc[-1]:.2f}")
            t4.metric("今日量能", "爆量" if vol_curr > vol_ma5 * 1.5 else "縮量" if vol_curr < vol_ma5 * 0.7 else "常態")

            st.line_chart(hist[['Close', 'MA5', 'MA20', 'MA60']])

            st.markdown("### 📰 相關即時焦點新聞")
            news_list = stock.news[:3] if stock.news else []
            news_summary = ""
            if news_list:
                for idx, n in enumerate(news_list, 1):
                    title = n.get('title', n.get('headline', '無標題'))
                    link = n.get('link', '')
                    st.write(f"{idx}. [{title}]({link})")
                    news_summary += f"- {title}\n"
            else:
                st.write("暫無最新全球/英文焦點新聞")

            st.markdown("---")
            st.markdown("### 🤖 一鍵複製：Gemini 全方位極致診斷指令")
            st.info("點擊下方程式碼區塊右上角的複製按鈕，直接貼給 Gemini，系統將為你產出明日買賣操作指令！")

            prompt = f"""請擔任台股頂級量化籌碼與技術面專家，針對【{info.get('longName', clean_code)} ({clean_code})】進行「鉅細靡遺」的全方位診斷，並直接告訴我明天該如何操作。

【雲端即時彙整數據】
1. 基本面與除權息狀況：
   - 最新收盤價：{curr_p:.2f} (漲跌幅: {chg_pct:+.2f}%)
   - 最近除息日：{last_div_date} | 最近配息金額：{last_div_amount} 元 | 預估殖利率：{div_yield_str}
   - 近20日高點(壓力)：{high_20:.2f} | 近20日低點(支撐)：{low_20:.2f}
   - EPS：{info.get('trailingEps', 'N/A')} | 本益比：{info.get('trailingPE', 'N/A')}
2. 技術與量能架構：
   - 5日線：{hist['MA5'].iloc[-1]:.2f} | 20日線：{hist['MA20'].iloc[-1]:.2f} | 60日線：{hist['MA60'].iloc[-1]:.2f}
   - 今日成交量：{vol_curr:.0f} (5日均量：{vol_ma5:.0f})
3. 最新相關新聞：
{news_summary}

【請針對以下項目進行精準診斷，並給出明確決策】：
1. 🎯 明日操作決策（核心）：明天開盤我該「買進、賣出、做空、還是觀望」？請給出明確的進場點、停損價、停利價與預期持有週期。
2. ⚡ 隔日沖與短線主力軌跡：研判今日是否有隔日沖主力鎖碼？明日開盤是否有高開拉高倒貨的賣壓風險？
3. 📊 籌碼面與信用交易：三大法人（外資/投信/自營商）最近買賣超趨勢、融資融券資券變化與籌碼集中度研判。
4. 🛡️ 股價支撐與賣壓：買盤承接力道如何？上方套牢賣壓重不重？給出具體支撐區與壓力區數字。
5. 💰 除權息與配息分析：預計/最近除息日影響、配息金額評價、配息模式（月/季/年配）與配息收益來源結構（含收益平準金/資本利得/股利分析與填息機率評估）。
6. 📈 完整技術面判讀：KD/RSI/MACD形態、均線排列與明日K線多空型態預測。
7. 🎯 目標價與長短線佈局：短線(1~2週)與長線(3~6個月)趨勢，並給出樂觀/中性/悲觀目標價。"""

            st.code(prompt, language="markdown")
