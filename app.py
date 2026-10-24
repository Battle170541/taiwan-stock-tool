import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from urllib.parse import quote

# =========================================================
# 台股專業分析儀表板（免費資料優先）
# 注意：免費資料可能延遲或缺漏；不將估算值冒充真實籌碼/勝率。
# =========================================================

st.set_page_config(
    page_title="台股專業操盤分析系統",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .stApp { background: #0b0f14; color: #e8edf2; }
    [data-testid="stHeader"] { background: rgba(11,15,20,.92); }
    [data-testid="stMetric"] {
        background: #151b23; border: 1px solid #283241;
        padding: 14px 16px; border-radius: 12px;
    }
    [data-testid="stMetricLabel"] { color: #aab6c5; }
    div[data-testid="stMetricValue"] { font-weight: 750; }
    div[data-testid="stMetricValue"] > div { white-space: normal !important; overflow-wrap: anywhere !important; font-size: clamp(1.0rem, 2.0vw, 1.75rem) !important; }
    [data-testid="stMetricDelta"] { white-space: normal !important; }
    .stDataFrame { width: 100%; }
    div[data-testid="stHorizontalBlock"] { gap: .65rem; }
    .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
    .section-note { color: #9aa8b8; font-size: .88rem; }
    div[data-testid="stTabs"] button { font-weight: 650; }
</style>
""", unsafe_allow_html=True)

HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 12

# 可逐步擴充：industry=主要產業；role=供應鏈位置；notes=關係說明
# 不代表已確認供應商/客戶關係，正式版需用公司營收與公告再驗證。
STOCKS = {
    "2383": {"name":"台光電","industry":"電子零組件／CCL","role":"CCL","peers":[
        ("6213","聯茂","同業競爭","銅箔基板 CCL"),
        ("6274","台燿","同業競爭","高階 CCL／高速材料"),
        ("1815","富喬","上游原料","電子級玻纖布"),
        ("8358","金居","上游原料","電解銅箔"),
        ("2368","金像電","下游應用","高階 PCB／AI 伺服器板"),
        ("3037","欣興","下游應用","PCB／IC 載板"),
        ("3044","健鼎","下游應用","多層 PCB"),
        ("2382","廣達","終端需求","伺服器 ODM"),
        ("2317","鴻海","終端需求","電子製造／伺服器"),
        ("6669","緯穎","終端需求","雲端伺服器")
    ]},
    "2330": {"name":"台積電","industry":"半導體／晶圓代工","role":"晶圓代工","peers":[
        ("2303","聯電","同業競爭","晶圓代工"),
        ("5347","世界","同業競爭","特殊製程晶圓代工"),
        ("6770","力積電","同業競爭","晶圓代工／記憶體相關"),
        ("3131","弘塑","設備供應鏈","半導體濕製程設備"),
        ("6640","均華","設備供應鏈","半導體封裝設備"),
        ("6187","萬潤","設備供應鏈","半導體自動化設備"),
        ("6223","旺矽","測試供應鏈","探針卡／測試介面"),
        ("6515","穎崴","測試供應鏈","測試座"),
        ("2454","聯發科","下游／客戶需求","IC 設計"),
        ("2382","廣達","終端需求","AI 伺服器 ODM")
    ]},
    "3131": {"name":"弘塑","industry":"半導體設備","role":"濕製程設備","peers":[
        ("6187","萬潤","設備同業／相近應用","半導體自動化設備"),
        ("6640","均華","設備同業／相近應用","先進封裝設備"),
        ("3583","辛耘","設備同業／相近應用","半導體設備／再生晶圓"),
        ("2467","志聖","設備同業／相近應用","電子製程設備"),
        ("2330","台積電","下游需求","先進製程／先進封裝需求"),
        ("3711","日月光投控","下游需求","封裝測試"),
        ("3443","創意","終端需求鏈","ASIC 設計服務"),
        ("3661","世芯-KY","終端需求鏈","ASIC 設計服務"),
        ("6223","旺矽","測試供應鏈","探針卡／測試介面"),
        ("6515","穎崴","測試供應鏈","測試座")
    ]},
    "6274": {"name":"台燿","industry":"電子零組件／CCL","role":"CCL","peers":[
        ("2383","台光電","同業競爭","高階 CCL"),
        ("6213","聯茂","同業競爭","銅箔基板 CCL"),
        ("1815","富喬","上游原料","電子級玻纖布"),
        ("8358","金居","上游原料","銅箔"),
        ("2368","金像電","下游應用","高階 PCB"),
        ("3037","欣興","下游應用","PCB／IC 載板"),
        ("2382","廣達","終端需求","伺服器 ODM"),
        ("6669","緯穎","終端需求","雲端伺服器"),
        ("2317","鴻海","終端需求","電子製造"),
        ("2345","智邦","終端需求","網通設備")
    ]},
    "2368": {"name":"金像電","industry":"電子零組件／PCB","role":"高階 PCB","peers":[
        ("3037","欣興","同業／相近應用","PCB／IC 載板"),
        ("3044","健鼎","同業／相近應用","多層 PCB"),
        ("2313","華通","同業／相近應用","HDI／PCB"),
        ("2383","台光電","上游材料","CCL"),
        ("6274","台燿","上游材料","CCL"),
        ("2382","廣達","終端需求","伺服器 ODM"),
        ("6669","緯穎","終端需求","雲端伺服器"),
        ("2317","鴻海","終端需求","電子製造"),
        ("2345","智邦","終端需求","網通設備"),
        ("2330","台積電","AI 產業鏈","晶圓代工")
    ]},
}

def normalize_code(user_input: str):
    s = user_input.strip()
    if s.isdigit():
        return s
    # Use twstock code table if installed, otherwise use local database names.
    try:
        import twstock
        matches = [(code, info.name) for code, info in twstock.codes.items()
                   if info.type in ("股票", "ETF") and s.lower() in info.name.lower()]
        if matches:
            return matches[0][0]
    except Exception:
        pass
    for code, item in STOCKS.items():
        if s in item["name"]:
            return code
    return s.upper()

def candidate_tickers(code):
    # Taiwanese listing suffixes: .TW (TWSE) and .TWO (TPEx)
    return [f"{code}.TW", f"{code}.TWO"]

@st.cache_data(ttl=600, show_spinner=False)
def get_history(code, period, interval):
    errors = []
    for symbol in candidate_tickers(code):
        try:
            df = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=False)
            if df is not None and not df.empty:
                df = df.copy()
                df.index = pd.to_datetime(df.index).tz_localize(None)
                df = df[~df.index.duplicated(keep="last")].sort_index()
                return df, symbol, None
        except Exception as exc:
            errors.append(f"{symbol}: {exc}")
    return pd.DataFrame(), None, "；".join(errors) or "免費行情來源沒有回傳資料"

@st.cache_data(ttl=3600, show_spinner=False)
def get_yf_info(symbol):
    try:
        return yf.Ticker(symbol).info or {}
    except Exception:
        return {}

def calc_indicators(df):
    x = df.copy()
    for c in ["Open","High","Low","Close","Volume"]:
        if c in x:
            x[c] = pd.to_numeric(x[c], errors="coerce")
    for n in [5,10,20,60]:
        x[f"MA{n}"] = x["Close"].rolling(n).mean()
    # MACD 12,26,9
    ema12 = x["Close"].ewm(span=12, adjust=False).mean()
    ema26 = x["Close"].ewm(span=26, adjust=False).mean()
    x["MACD"] = ema12 - ema26
    x["MACD_signal"] = x["MACD"].ewm(span=9, adjust=False).mean()
    x["MACD_hist"] = x["MACD"] - x["MACD_signal"]
    # RSI 14
    delta = x["Close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    x["RSI14"] = 100 - (100 / (1 + rs))
    # Stochastic KD
    low14 = x["Low"].rolling(9).min()
    high14 = x["High"].rolling(9).max()
    rsv = (x["Close"] - low14) / (high14 - low14).replace(0, np.nan) * 100
    x["K"] = rsv.ewm(alpha=1/3, adjust=False).mean()
    x["D"] = x["K"].ewm(alpha=1/3, adjust=False).mean()
    # Bollinger
    mid = x["Close"].rolling(20).mean()
    sd = x["Close"].rolling(20).std()
    x["BB_up"] = mid + 2*sd
    x["BB_low"] = mid - 2*sd
    x["VOL_MA5"] = x["Volume"].rolling(5).mean()
    # ATR(14) for volatility-aware levels
    prev_close = x["Close"].shift(1)
    tr = pd.concat([
        x["High"] - x["Low"],
        (x["High"] - prev_close).abs(),
        (x["Low"] - prev_close).abs()
    ], axis=1).max(axis=1)
    x["ATR14"] = tr.rolling(14).mean()
    # Pivot levels based on prior completed session
    x["PIVOT"] = (x["High"].shift(1) + x["Low"].shift(1) + x["Close"].shift(1)) / 3
    x["S1"] = 2*x["PIVOT"] - x["High"].shift(1)
    x["R1"] = 2*x["PIVOT"] - x["Low"].shift(1)
    return x


def technical_score_frame(x):
    """Score known at close t; used against the following session to avoid look-ahead."""
    z = x.copy()
    score = pd.Series(0, index=z.index, dtype=float)
    for ma in ["MA5", "MA20", "MA60"]:
        score += np.where(z["Close"] > z[ma], 1, np.where(z["Close"] < z[ma], -1, 0))
    score += np.where(z["MACD"] > z["MACD_signal"], 1,
                      np.where(z["MACD"] < z["MACD_signal"], -1, 0))
    z["SignalScore"] = score
    return z


def historical_probabilities(x):
    """Historical conditional frequencies, not a guarantee or a trained predictive model."""
    z = technical_score_frame(x).copy()
    current_score = int(z["SignalScore"].iloc[-1])
    next_close = z["Close"].shift(-1)
    next_open = z["Open"].shift(-1)
    z["NextCloseUp"] = np.where(next_close.notna(), (next_close > z["Close"]).astype(float), np.nan)
    z["NextSessionGreen"] = np.where(next_close.notna() & next_open.notna(), (next_close > next_open).astype(float), np.nan)
    z["NextCloseReturn"] = next_close / z["Close"] - 1
    z = z.iloc[:-1].dropna(subset=["SignalScore", "NextCloseUp", "NextSessionGreen"])
    if z.empty:
        return {}
    # Similar-score historical observations; broad enough to avoid a tiny exact-score sample.
    similar = z[z["SignalScore"].between(current_score-1, current_score+1)]
    if len(similar) < 15:
        similar = z
    return {
        "overnight_up": float(similar["NextCloseUp"].mean() * 100),
        "intraday_green": float(similar["NextSessionGreen"].mean() * 100),
        "n": int(len(similar)),
        "score": current_score,
        "sample_start": similar.index.min().strftime("%Y-%m-%d"),
        "sample_end": similar.index.max().strftime("%Y-%m-%d"),
    }


@st.cache_data(ttl=1800, show_spinner=False)
def get_official_json(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def get_twse_day_history(code, date_yyyymmdd):
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date={date_yyyymmdd}&stockNo={quote(str(code))}&response=json"
    return get_official_json(url)


def get_twse_margin_day(date_yyyymmdd):
    url = f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date={date_yyyymmdd}&selectType=ALL&response=json"
    return get_official_json(url)


def get_twse_institution_day(date_yyyymmdd):
    url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={date_yyyymmdd}&selectType=ALLBUT0999&response=json"
    return get_official_json(url)


def _find_table_rows(payload, code):
    """Find a row whose first column matches stock code, handling TWSE JSON table layouts."""
    if not isinstance(payload, dict):
        return None, None
    tables = payload.get("tables")
    if isinstance(tables, list):
        for table in tables:
            fields = table.get("fields", [])
            rows = table.get("data", [])
            if not rows:
                continue
            for row in rows:
                if row and str(row[0]).strip() == str(code):
                    return fields, row
    fields = payload.get("fields", [])
    rows = payload.get("data", [])
    if isinstance(rows, list):
        for row in rows:
            if row and str(row[0]).strip() == str(code):
                return fields, row
    return None, None


def _num_cell(value):
    try:
        return float(str(value).replace(",", "").replace("--", "0").replace("X", "").strip())
    except Exception:
        return np.nan


@st.cache_data(ttl=1800, show_spinner=False)
def get_recent_chip_data(code, days=5):
    """Fetch recent official TWSE daily data; unsupported/missing dates remain missing."""
    rows = []
    # Iterate a generous calendar window and retain the latest available trading dates.
    today = datetime.now()
    dates = pd.date_range(end=today.normalize(), periods=18, freq="D")[::-1]
    for dt in dates:
        date_s = dt.strftime("%Y%m%d")
        # weekends/holidays naturally return no matching rows
        daily = get_twse_day_history(code, date_s)
        rows_daily = daily.get("data", []) if isinstance(daily, dict) else []
        target_roc = f"{dt.year-1911}/{dt.month:02d}/{dt.day:02d}"
        row = None
        for candidate in rows_daily:
            if candidate and str(candidate[0]).strip().replace("-", "/") == target_roc:
                row = candidate
                break
        if row is None:
            continue
        # STOCK_DAY data fields typically: 日期, 成交股數, 成交金額, 開盤價, 最高價, 最低價, 收盤價, 漲跌價差, 成交筆數
        def dval(idx):
            return _num_cell(row[idx]) if len(row) > idx else np.nan
        item = {
            "日期": str(row[0]),
            "成交量(張)": dval(1) / 1000,
            "開盤價": dval(3), "最高價": dval(4), "最低價": dval(5), "收盤價": dval(6),
            "融資買進(張)": np.nan, "融資賣出(張)": np.nan, "融資餘額(張)": np.nan,
            "融券買進(張)": np.nan, "融券賣出(張)": np.nan, "融券餘額(張)": np.nan,
            "外資買賣超(張)": np.nan, "投信買賣超(張)": np.nan, "自營商買賣超(張)": np.nan,
        }
        margin = get_twse_margin_day(date_s)
        mfields, mrow = _find_table_rows(margin, code)
        if mrow is not None and mfields:
            # Map by field names rather than assuming one fixed column order.
            for j, field in enumerate(mfields):
                if j >= len(mrow): continue
                f = str(field)
                val = _num_cell(mrow[j])
                if "融資買進" in f: item["融資買進(張)"] = val
                elif "融資賣出" in f: item["融資賣出(張)"] = val
                elif "融資今日餘額" in f or "融資餘額" in f: item["融資餘額(張)"] = val
                elif "融券買進" in f: item["融券買進(張)"] = val
                elif "融券賣出" in f: item["融券賣出(張)"] = val
                elif "融券今日餘額" in f or "融券餘額" in f: item["融券餘額(張)"] = val
            # TWSE margin report figures are shares/units in lots of 1,000; normalize if large.
            for k in ["融資買進(張)","融資賣出(張)","融資餘額(張)","融券買進(張)","融券賣出(張)","融券餘額(張)"]:
                if pd.notna(item[k]) and abs(item[k]) > 100000:
                    item[k] = item[k] / 1000
        inst = get_twse_institution_day(date_s)
        ifields, irow = _find_table_rows(inst, code)
        if irow is not None and ifields:
            for j, field in enumerate(ifields):
                if j >= len(irow): continue
                f = str(field)
                val = _num_cell(irow[j])
                # T86 columns are share counts; convert to lots
                if "外陸資買賣超股數" in f or "外資及陸資買賣超股數" in f:
                    item["外資買賣超(張)"] = val / 1000
                elif "投信買賣超股數" in f:
                    item["投信買賣超(張)"] = val / 1000
                elif "自營商買賣超股數" in f:
                    item["自營商買賣超(張)"] = val / 1000
        rows.append(item)
        if len(rows) >= days:
            break
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("日期", ascending=False)

def make_chart(df, show_ma, show_bb, show_macd, show_rsi, show_kd):
    rows = 2 + int(show_macd) + int(show_rsi) + int(show_kd)
    heights = [0.56, 0.16] + ([0.10] if show_macd else []) + ([0.09] if show_rsi else []) + ([0.09] if show_kd else [])
    # Normalize subplot heights
    total = sum(heights)
    heights = [h/total for h in heights]
    titles = ["K 線／均線", "成交量"]
    if show_macd: titles.append("MACD")
    if show_rsi: titles.append("RSI(14)")
    if show_kd: titles.append("KD(9,3,3)")
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.025,
                        row_heights=heights, subplot_titles=titles)
    x = df.index
    # Taiwan color convention: red up, green down
    fig.add_trace(go.Candlestick(
        x=x, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name="K線", increasing_line_color="#ef4444", decreasing_line_color="#22c55e",
        increasing_fillcolor="#ef4444", decreasing_fillcolor="#22c55e",
        whiskerwidth=0.5
    ), row=1, col=1)
    if show_ma:
        for n, color in [(5,"#f59e0b"),(10,"#60a5fa"),(20,"#a78bfa"),(60,"#e5e7eb")]:
            fig.add_trace(go.Scatter(x=x, y=df[f"MA{n}"], mode="lines", name=f"MA{n}",
                                     line=dict(width=1.2, color=color)), row=1, col=1)
    if show_bb:
        fig.add_trace(go.Scatter(x=x, y=df["BB_up"], mode="lines", name="布林上軌",
                                 line=dict(width=1, color="rgba(148,163,184,.7)", dash="dot")), row=1, col=1)
        fig.add_trace(go.Scatter(x=x, y=df["BB_low"], mode="lines", name="布林下軌",
                                 line=dict(width=1, color="rgba(148,163,184,.7)", dash="dot"),
                                 fill="tonexty", fillcolor="rgba(148,163,184,.05)"), row=1, col=1)
    colors = np.where(df["Close"] >= df["Open"], "#ef4444", "#22c55e")
    fig.add_trace(go.Bar(x=x, y=df["Volume"], name="成交量", marker_color=colors), row=2, col=1)
    fig.add_trace(go.Scatter(x=x, y=df["VOL_MA5"], name="量 MA5",
                             line=dict(color="#f59e0b", width=1)), row=2, col=1)
    row = 3
    if show_macd:
        fig.add_trace(go.Bar(x=x, y=df["MACD_hist"], name="MACD 柱",
                             marker_color=np.where(df["MACD_hist"] >= 0, "#ef4444", "#22c55e")), row=row, col=1)
        fig.add_trace(go.Scatter(x=x, y=df["MACD"], name="DIF", line=dict(color="#60a5fa", width=1.3)), row=row, col=1)
        fig.add_trace(go.Scatter(x=x, y=df["MACD_signal"], name="訊號線", line=dict(color="#f59e0b", width=1.3)), row=row, col=1)
        row += 1
    if show_rsi:
        fig.add_trace(go.Scatter(x=x, y=df["RSI14"], name="RSI14", line=dict(color="#c084fc", width=1.5)), row=row, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="#ef4444", opacity=.6, row=row, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#22c55e", opacity=.6, row=row, col=1)
        fig.update_yaxes(range=[0,100], row=row, col=1)
        row += 1
    if show_kd:
        fig.add_trace(go.Scatter(x=x, y=df["K"], name="K", line=dict(color="#60a5fa", width=1.4)), row=row, col=1)
        fig.add_trace(go.Scatter(x=x, y=df["D"], name="D", line=dict(color="#f59e0b", width=1.4)), row=row, col=1)
        fig.add_hline(y=80, line_dash="dot", line_color="#ef4444", opacity=.6, row=row, col=1)
        fig.add_hline(y=20, line_dash="dot", line_color="#22c55e", opacity=.6, row=row, col=1)
        fig.update_yaxes(range=[0,100], row=row, col=1)
    fig.update_layout(
        template="plotly_dark", height=760, paper_bgcolor="#0b0f14", plot_bgcolor="#0b0f14",
        margin=dict(l=8,r=8,t=45,b=8), hovermode="x unified",
        xaxis_rangeslider_visible=False, legend=dict(orientation="h", y=1.02, x=0),
        font=dict(family="Arial, sans-serif", color="#dbe4ee", size=11),
        dragmode="pan"
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(148,163,184,.12)", rangeslider_visible=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(148,163,184,.12)")
    return fig

@st.cache_data(ttl=1800, show_spinner=False)
def get_twse_quote(code):
    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        df = pd.DataFrame(r.json())
        if "Code" not in df.columns:
            return None
        row = df[df["Code"].astype(str) == str(code)]
        if row.empty:
            return None
        d = row.iloc[0].to_dict()
        def num(key):
            return pd.to_numeric(str(d.get(key, "0")).replace(",", "").replace("--","0"), errors="coerce")
        return {"name": d.get("Name", code), "close": num("ClosingPrice"),
                "open": num("OpeningPrice"), "high": num("HighestPrice"),
                "low": num("LowestPrice"), "volume_shares": num("TradeVolume"),
                "source":"TWSE OpenAPI（最新日行情）"}
    except Exception:
        return None

def safe_num(value):
    try:
        v = float(value)
        return v if np.isfinite(v) else None
    except Exception:
        return None

def fmt_num(v, digits=2):
    v = safe_num(v)
    return "—" if v is None else f"{v:,.{digits}f}"

def default_peer_list(code):
    if code in STOCKS:
        return STOCKS[code]["peers"]
    return []

def peer_table(code, period="6mo"):
    peers = default_peer_list(code)
    if not peers:
        return pd.DataFrame()
    main_df, _, _ = get_history(code, period, "1d")
    rows = []
    main_ret = main_df["Close"].pct_change().rename("main") if not main_df.empty else pd.Series(dtype=float)
    for pcode, pname, role, desc in peers:
        pdf, _, _ = get_history(pcode, period, "1d")
        if pdf.empty:
            rows.append({"代號":pcode,"名稱":pname,"供應鏈位置":role,"業務說明":desc,
                         "區間漲跌幅":"—","與主股相關係數":"—"})
            continue
        ret = pdf["Close"].pct_change().rename("peer")
        joined = pd.concat([main_ret, ret], axis=1, join="inner").dropna()
        corr = joined["main"].corr(joined["peer"]) if len(joined) >= 20 else np.nan
        chg = (pdf["Close"].iloc[-1] / pdf["Close"].iloc[0] - 1) * 100 if len(pdf) > 1 else np.nan
        rows.append({"代號":pcode,"名稱":pname,"供應鏈位置":role,"業務說明":desc,
                     "區間漲跌幅":f"{chg:+.2f}%" if np.isfinite(chg) else "—",
                     "與主股相關係數":f"{corr:.2f}" if np.isfinite(corr) else "樣本不足"})
    return pd.DataFrame(rows)

# Header
st.title("📈 台股專業操盤與產業聯動系統")
st.caption("免費資料優先｜台股漲紅跌綠｜互動式多週期 K 線｜產業分類與量價分析")
col_search, col_period = st.columns([2.2, 1])
with col_search:
    user_input = st.text_input("輸入台股代號或名稱", value="2383", placeholder="例如：2383、台光電、2330、台積電")
with col_period:
    period_label = st.selectbox("K 線週期", ["日 K｜近 3 個月","日 K｜近 1 年","週 K｜近 3 年","月 K｜近 5 年"], index=1)

code = normalize_code(user_input)
if not code:
    st.info("請輸入股票代號或名稱。")
    st.stop()

if period_label == "日 K｜近 3 個月":
    period, interval = "3mo", "1d"
elif period_label == "日 K｜近 1 年":
    period, interval = "1y", "1d"
elif period_label == "週 K｜近 3 年":
    period, interval = "3y", "1wk"
else:
    period, interval = "5y", "1mo"

with st.spinner(f"正在取得 {code} 行情資料…"):
    hist, symbol, hist_error = get_history(code, period, interval)
    quote = get_twse_quote(code)
    info = get_yf_info(symbol) if symbol else {}

if hist.empty:
    st.error(f"找不到股票 {user_input}（辨識代號：{code}）的行情資料。請確認代號，或稍後重試。")
    if hist_error:
        st.caption(hist_error)
    st.stop()

df = calc_indicators(hist)
last = df.iloc[-1]
prev = df.iloc[-2] if len(df) > 1 else last
close = safe_num(last["Close"])
prev_close = safe_num(prev["Close"])
change = close - prev_close if close is not None and prev_close is not None else None
change_pct = change / prev_close * 100 if change is not None and prev_close else None
display_name = (quote or {}).get("name") or STOCKS.get(code, {}).get("name") or info.get("shortName") or code
industry = STOCKS.get(code, {}).get("industry", info.get("industry", "尚未分類"))
source_stamp = df.index[-1].strftime("%Y-%m-%d")
latest_volume_lots = safe_num(last["Volume"] / 1000) if safe_num(last["Volume"]) is not None else None

st.markdown(f"## 📌 {display_name}（{code}）")
st.caption(f"市場資料日期：{source_stamp}｜資料代碼：{symbol}｜來源：Yahoo Finance 歷史行情；上市最新行情可用 TWSE OpenAPI 補充。免費資料可能延遲，非逐筆即時報價。")
m1,m2,m3,m4,m5 = st.columns(5)
m1.metric("收盤價", fmt_num(close), f"{change:+.2f}（{change_pct:+.2f}%）" if change is not None and change_pct is not None else None)
m2.metric("成交量（張）", fmt_num(latest_volume_lots,0))
m3.metric("當日高點", fmt_num(last["High"]))
m4.metric("當日低點", fmt_num(last["Low"]))
m5.metric("產業分類", industry)

tabs = st.tabs(["📈 技術分析","🔗 產業與同業","💰 基本面","🎯 交易策略／目標價","📊 近一週籌碼","ℹ️ 資料品質"])

with tabs[0]:
    left, right = st.columns([2,1])
    with left:
        show_ma = st.checkbox("均線 MA5／10／20／60", True)
        show_bb = st.checkbox("布林通道", False)
    with right:
        show_macd = st.checkbox("MACD", True)
        show_rsi = st.checkbox("RSI", True)
        show_kd = st.checkbox("KD", True)
    fig = make_chart(df.tail(500), show_ma, show_bb, show_macd, show_rsi, show_kd)
    st.plotly_chart(fig, width="stretch", config={"displaylogo":False, "scrollZoom":True, "displayModeBar":True})
    a,b,c,d = st.columns(4)
    rsi = safe_num(last["RSI14"])
    k = safe_num(last["K"]); dval = safe_num(last["D"])
    a.metric("MA20", fmt_num(last["MA20"]))
    b.metric("MA60", fmt_num(last["MA60"]))
    c.metric("RSI(14)", fmt_num(rsi,1))
    d.metric("KD", f"{fmt_num(k,1)} / {fmt_num(dval,1)}")
    st.caption("台股慣例：紅 K 表示收高、綠 K 表示收低。技術指標只描述歷史價格，不保證未來走勢。")

with tabs[1]:
    st.subheader("產業分類與供應鏈位置")
    st.write(f"**主要產業：**{industry}　｜　**核心定位：**{STOCKS.get(code,{}).get('role','尚未建立分類')}")
    st.markdown("""
    - **同業競爭：**產品或業務相近，適合比較營收成長、毛利率與估值。
    - **上游原料／設備：**可能影響成本、交期、產能或資本支出。
    - **下游應用／終端需求：**反映訂單需求與終端市場景氣。
    - **股價相關係數：**依同期間日報酬計算；高相關不等於供應商／客戶關係。
    """)
    peer_period = st.selectbox("比較期間", ["3mo","6mo","1y"], index=1, format_func=lambda x: {"3mo":"近 3 個月","6mo":"近 6 個月","1y":"近 1 年"}[x])
    with st.spinner("計算同業報酬與相關係數…"):
        peers = peer_table(code, peer_period)
    if peers.empty:
        st.info("此股票尚未建立供應鏈分類。可在程式碼 STOCKS 字典新增該股票的產業、角色與關聯標的。")
    else:
        st.dataframe(peers, hide_index=True, width="stretch")
        st.caption("分類是研究用初始資料庫，並非官方產業分類或已驗證客戶名單。相關係數至少需要 20 個共同交易日。")

with tabs[2]:
    st.subheader("基本面與估值")
    i1,i2,i3,i4 = st.columns(4)
    i1.metric("TTM EPS", fmt_num(info.get("trailingEps")))
    i2.metric("本益比 PE", fmt_num(info.get("trailingPE")))
    i3.metric("股價淨值比 PB", fmt_num(info.get("priceToBook")))
    i4.metric("營收成長率 YoY", fmt_num(info.get("revenueGrowth")*100 if safe_num(info.get("revenueGrowth")) is not None else None,1) + ("%" if safe_num(info.get("revenueGrowth")) is not None else ""))
    st.markdown("#### 近四季 EPS")
    try:
        ticker = yf.Ticker(symbol)
        inc = ticker.quarterly_income_stmt
        if not inc.empty:
            eps_key = next((x for x in ["Basic EPS","Diluted EPS"] if x in inc.index), None)
            if eps_key:
                eps = inc.loc[eps_key].head(4)
                eps_df = pd.DataFrame({"季度": [pd.to_datetime(x).strftime("%Y-%m-%d") for x in eps.index],
                                       "EPS（元）": pd.to_numeric(eps.values, errors="coerce")})
                st.dataframe(eps_df, hide_index=True, width="stretch")
            else:
                st.info("資料來源未提供可辨識的 EPS 欄位。")
        else:
            st.info("目前無法取得季度損益表。")
    except Exception:
        st.info("目前無法取得季度 EPS；請稍後重試。")
    st.markdown("#### 財務資料使用限制")
    st.caption("Yahoo Finance 欄位可能缺漏、延遲或與公司公告口徑不同；正式交易前應以公開資訊觀測站與交易所公告核對。月營收歷史圖、毛利率、現金流與估值歷史分位數可在下一版接入官方資料源。")

with tabs[3]:
    st.subheader("短線／長線 × 當沖／隔日沖：交易情境與價格區間")
    horizon_col, style_col = st.columns(2)
    with horizon_col:
        horizon = st.radio("分析週期", ["短線（1–5 個交易日）", "長線／波段（20–60 個交易日）"], horizontal=True)
    with style_col:
        trade_style = st.radio("交易方式", ["當沖", "隔日沖"], horizontal=True)

    # Use enough daily history for ATR and conditional historical frequencies.
    daily_hist, _, _ = get_history(code, "2y", "1d")
    daily = calc_indicators(daily_hist) if not daily_hist.empty else df
    probs = historical_probabilities(daily) if len(daily) >= 80 else {}
    today = daily.iloc[-1]
    c = safe_num(today["Close"])
    prev_hi = safe_num(today["High"]); prev_lo = safe_num(today["Low"])
    atr = safe_num(today["ATR14"])
    if atr is None or atr <= 0:
        atr = max(c * 0.02, 0.01)
    pivot = safe_num(today["PIVOT"])
    s1 = safe_num(today["S1"]); r1 = safe_num(today["R1"])
    low5 = safe_num(daily.tail(5)["Low"].min())
    high5 = safe_num(daily.tail(5)["High"].max())
    low20 = safe_num(daily.tail(20)["Low"].min())
    high20 = safe_num(daily.tail(20)["High"].max())
    low60 = safe_num(daily.tail(60)["Low"].min())
    high60 = safe_num(daily.tail(60)["High"].max())
    ma20 = safe_num(today["MA20"]); ma60 = safe_num(today["MA60"])
    if horizon.startswith("短線"):
        support = min([v for v in [s1, low5, ma20] if v is not None]) if any(v is not None for v in [s1,low5,ma20]) else c-atr
        resistance = max([v for v in [r1, high5] if v is not None]) if any(v is not None for v in [r1,high5]) else c+atr
    else:
        support = min([v for v in [low20, low60, ma60] if v is not None]) if any(v is not None for v in [low20,low60,ma60]) else c-2*atr
        resistance = max([v for v in [high20, high60] if v is not None]) if any(v is not None for v in [high20,high60]) else c+2*atr

    if trade_style == "當沖":
        long_entry_low = max(0.01, (s1 if s1 is not None else c-0.5*atr))
        long_entry_high = min(c, pivot if pivot is not None else c)
        short_entry_low = max(c, pivot if pivot is not None else c)
        short_entry_high = r1 if r1 is not None else c+0.5*atr
        long_stop = max(0.01, min(long_entry_low-0.5*atr, prev_lo-0.1*atr))
        short_stop = max(short_entry_high+0.5*atr, prev_hi+0.1*atr)
        long_target = max(resistance, c+0.8*atr)
        short_target = min(support, c-0.8*atr)
    else:
        long_entry_low = max(0.01, support)
        long_entry_high = min(c, support+0.35*atr)
        short_entry_low = max(c, resistance-0.35*atr)
        short_entry_high = resistance
        long_stop = max(0.01, support-0.8*atr)
        short_stop = resistance+0.8*atr
        long_target = max(resistance, c+1.5*atr)
        short_target = min(support-0.5*atr, c-1.5*atr)

    # Display historical conditional frequencies, explicitly not a guaranteed forecast.
    if probs:
        p_intraday = probs["intraday_green"]
        p_overnight = probs["overnight_up"]
        sample_n = probs["n"]
    else:
        p_intraday = p_overnight = None
        sample_n = 0
    shown_prob = p_intraday if trade_style == "當沖" else p_overnight
    prob_col1, prob_col2, prob_col3 = st.columns(3)
    prob_col1.metric("歷史條件上漲頻率", f"{shown_prob:.1f}%" if shown_prob is not None else "樣本不足")
    prob_col2.metric("對應歷史樣本數", f"{sample_n:,} 筆" if sample_n else "—")
    prob_col3.metric("趨勢評分（-4 至 +4）", f"{int(probs['score']):+d}" if probs else "—")
    st.caption(
        f"頻率統計區間：{probs.get('sample_start','—')} 至 {probs.get('sample_end','—')}。"
        "這是相似技術條件下的歷史比例，不是經驗證的未來預測機率；當沖頻率以隔日開收盤紅黑 K 近似，無法替代逐筆或 5 分 K 回測。"
    )

    st.markdown("#### 建議觀察進場區間（條件觸發，不是無條件掛單）")
    def price_range(a,b):
        if a is None or b is None: return "—"
        lo, hi = sorted([float(a), float(b)])
        return f"{lo:,.2f} – {hi:,.2f}"
    p1,p2 = st.columns(2)
    with p1:
        st.markdown("##### 🔴 做多情境")
        st.metric("建議觀察進場區", price_range(long_entry_low, long_entry_high))
        st.metric("參考停損價", f"{long_stop:,.2f}")
        st.metric("預估目標價", f"{long_target:,.2f}")
        st.caption("條件：價格回測支撐不破，或突破壓力且量能確認；未觸發時不追價。")
    with p2:
        st.markdown("##### 🟢 做空情境")
        st.metric("建議觀察進場區", price_range(short_entry_low, short_entry_high))
        st.metric("參考停損價", f"{short_stop:,.2f}")
        st.metric("預估目標價", f"{short_target:,.2f}")
        st.caption("融券／借券資格、券源、當沖資格與券商限制須另行確認；無法放空時只能觀察，不可直接照此執行。")

    st.markdown("#### 支撐／壓力價位")
    q1,q2,q3,q4 = st.columns(4)
    q1.metric("短線支撐", f"{(min(v for v in [s1,low5] if v is not None)):,.2f}" if any(v is not None for v in [s1,low5]) else "—")
    q2.metric("短線壓力", f"{(max(v for v in [r1,high5] if v is not None)):,.2f}" if any(v is not None for v in [r1,high5]) else "—")
    q3.metric("波段支撐", f"{low20:,.2f}" if low20 is not None else "—")
    q4.metric("波段壓力", f"{high20:,.2f}" if high20 is not None else "—")
    st.warning("價位由近期高低點、均線、ATR 與前一交易日樞紐價推算，屬於規則式參考，不是保證會到達的預測。高波動、跳空、處置股與漲跌停可能使價位失效。")
with tabs[4]:
    st.subheader("近一週融資融券與三大法人")
    st.caption("優先嘗試抓取證交所逐日資料。僅在官方端點回傳資料時顯示；空白代表資料未取得，不代表買賣超為零。")
    with st.spinner("查詢最近交易日官方籌碼資料…"):
        chip_df = get_recent_chip_data(code, days=5)
    if chip_df.empty:
        st.info("目前無法取得這檔股票近一週的官方籌碼明細。可能是上櫃股票、非交易日、官方端點格式變動或資料源暫時不可用。此時不會以估算值替代。")
    else:
        st.markdown("#### 每日成交量與融資融券／法人買賣超")
        st.dataframe(chip_df, hide_index=True, width="stretch")
        st.markdown("#### 近一週淨變化摘要")
        net_cols = ["融資買進(張)","融資賣出(張)","融資餘額(張)","融券買進(張)","融券賣出(張)","融券餘額(張)","外資買賣超(張)","投信買賣超(張)","自營商買賣超(張)"]
        sumrow = {}
        for col in net_cols:
            vals = pd.to_numeric(chip_df[col], errors="coerce").dropna()
            sumrow[col] = f"{vals.iloc[0]:+,.0f}" if col.endswith("買賣超(張)") and len(vals) else (f"{vals.iloc[-1]:,.0f}" if len(vals) else "—")
        summary_df = pd.DataFrame([{"指標":k, "數值":v, "說明":"法人欄位為每日買賣超；餘額欄位為當日餘額" if "餘額" in k else "資料列中最近可取得值"} for k,v in sumrow.items()])
        st.dataframe(summary_df, hide_index=True, width="stretch")
    st.caption("注意：本版籌碼串接以 TWSE 官方公開端點為主，對 TPEx 上櫃股票的歷史籌碼尚未完整支援。欄位格式若因官方 API 調整，需同步更新解析器。")

with tabs[5]:
    st.subheader("資料來源與品質")
    st.write(f"- 歷史 K 線：Yahoo Finance（{symbol}）")
    st.write("- 上市最新日行情補充：TWSE OpenAPI")
    st.write("- 上櫃最新行情：目前以 Yahoo Finance 作為主要備援；TPEx 官方資料端點可在下一版擴充。")
    st.write("- 三大法人、融資融券、借券：本版尚未接入完整逐日官方資料，因此不顯示模擬數字。")
    st.write("- 營收歷史：本版尚未完成官方月營收序列整合；Yahoo 財務摘要只作輔助參考。")
    st.write(f"- 最後資料日期：{source_stamp}")
    st.warning("免費資料不等於即時行情。若來源未更新、回傳欄位變更或遭限流，畫面可能缺資料；請以證交所、櫃買中心及公開資訊觀測站公告為準。")

st.markdown("---")
st.caption("台股專業操盤分析系統｜研究輔助用途；所有機率與價位均為歷史統計／規則式估算，不構成投資建議。")
