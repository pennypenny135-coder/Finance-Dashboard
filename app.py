import streamlit as st
import requests
import re
import json
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="金融市場 Dashboard",
    page_icon="🌐",
    layout="wide"
)

st.markdown("""
<style>
    .stApp { background-color: #0b1120; }
    .block-container { padding-top: 1.5rem; }
    .title-box {
        background: linear-gradient(90deg, #1e3a5f, #0b1120);
        border-left: 4px solid #2563eb;
        padding: 12px 20px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .snapshot-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
    }
    .snapshot-table th {
        background: #1f2937;
        color: #9ca3af;
        padding: 8px 12px;
        text-align: left;
        font-weight: 600;
    }
    .snapshot-table td {
        padding: 7px 12px;
        border-bottom: 1px solid #1f2937;
        color: #e5e7eb;
    }
    .snapshot-table tr:hover td { background: #111827; }
    .tag-up   { color: #4ade80; font-weight: bold; }
    .tag-down { color: #f87171; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


# ==================== 數據抓取 ====================
@st.cache_data(ttl=300, show_spinner=False)
def fetch_market_data():
    end = datetime.now()
    start = end - timedelta(days=130)

    tickers = {
        "S&P 500": "^GSPC",
        "IWM": "IWM",
        "VIX": "^VIX",
        "10Y Yield": "^TNX",
        "Oil (WTI)": "CL=F",
        "Gold": "GC=F",
        "DXY": "DX-Y.NYB",
        "USD/HKD": "USDHKD=X",
    }

    data = {}
    for name, sym in tickers.items():
        try:
            df = yf.download(sym, start=start, end=end, progress=False, auto_adjust=True)
            if df.empty or len(df) < 5:
                df = yf.Ticker(sym).history(start=start, end=end)
            if not df.empty and len(df) >= 5:
                s = df["Close"].squeeze().dropna()
                if name == "10Y Yield":
                    s = s / 100
                data[name] = s
            else:
                data[name] = pd.Series(dtype=float)
        except:
            data[name] = pd.Series(dtype=float)
    return data


@st.cache_data(ttl=900, show_spinner=False)
def fetch_fear_greed():
    headers = {"User-Agent": "Mozilla/5.0"}

    # ── 方法 A：alternative.me API（加密市場 F&G 備用）────────
    try:
        resp = requests.get(
            "https://api.alternative.me/fng/?limit=1",
            headers=headers, timeout=10
        )
        jd = resp.json()
        val = int(jd["data"][0]["value"])
        if 0 < val <= 100:
            return val, pd.Timestamp.now()
    except Exception:
        pass

    return 50, pd.Timestamp.now()


# ==================== MA 輔助函數 ====================
def add_ma_traces(fig, series, row, col, base_name, color_main,
                  secondary_y=None, multiply=1.0, dash_main=None):
    if len(series) == 0:
        return
    ps = series * multiply
    ma10 = ps.rolling(10).mean()
    ma20 = ps.rolling(20).mean()
    kw = {"secondary_y": secondary_y} if secondary_y is not None else {}

    fig.add_trace(go.Scatter(
        x=ps.index, y=ps.values, name=base_name,
        line=dict(color=color_main, width=2.5, dash=dash_main or "solid")
    ), row=row, col=col, **kw)

    fig.add_trace(go.Scatter(
        x=ma10.index, y=ma10.values, name=f"{base_name} 10MA",
        line=dict(color="#FFD166", width=1.5, dash="dash")
    ), row=row, col=col, **kw)

    fig.add_trace(go.Scatter(
        x=ma20.index, y=ma20.values, name=f"{base_name} 20MA",
        line=dict(color="#EF476F", width=1.5, dash="dot")
    ), row=row, col=col, **kw)


# ==================== 建立圖表 ====================
def build_fig(data, fg_val, fg_date):
    fig = make_subplots(
        rows=4, cols=2,
        subplot_titles=(
            "IWM (Russell 2000)", "VIX Volatility Index",
            "S&P 500 Index", "10Y Treasury Yield (%)",
            "DXY (左軸) & USD/HKD (右軸)", "WTI Crude Oil (USD/桶)",
            "Gold Futures (USD/盎司)", "Crypto Fear & Greed",
        ),
        vertical_spacing=0.09,
        horizontal_spacing=0.10,
        specs=[
            [{}, {}],
            [{}, {}],
            [{"secondary_y": True}, {}],
            [{}, {"type": "indicator"}],
        ],
    )

    add_ma_traces(fig, data.get("IWM", pd.Series()), 1, 1, "IWM", "#4CC9F0")
    add_ma_traces(fig, data.get("VIX", pd.Series()), 1, 2, "VIX", "#F72585")
    add_ma_traces(fig, data.get("S&P 500", pd.Series()), 2, 1, "S&P 500", "#90BE6D")
    add_ma_traces(fig, data.get("10Y Yield", pd.Series()), 2, 2, "10Y Yield", "#F9844A", multiply=100)
    fig.update_yaxes(title_text="Yield (%)", row=2, col=2)

    add_ma_traces(fig, data.get("Oil (WTI)", pd.Series()), 3, 2, "WTI Oil", "#F8961E")
    add_ma_traces(fig, data.get("Gold", pd.Series()), 4, 1, "Gold", "#FFD60A")

    if fg_val >= 75:
        mood, bc = "極度貪婪 🤑", "#00c853"
    elif fg_val >= 55:
        mood, bc = "貪婪 😏", "#64dd17"
    elif fg_val >= 45:
        mood, bc = "中性 😐", "#ffd600"
    elif fg_val >= 25:
        mood, bc = "恐懼 😨", "#ff9100"
    else:
        mood, bc = "極度恐懼 😱", "#ff1744"

    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=fg_val,
        title={"text": f"Fear & Greed<br><span style='font-size:11px'>{mood}</span>",
               "font": {"color": "white"}},
        number={"font": {"color": bc, "size": 44}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "white"},
            "bar": {"color": bc},
            "bgcolor": "#1a1a2e",
            "steps": [
                {"range": [0, 25], "color": "#4a0d1a"},
                {"range": [25, 45], "color": "#6b2d00"},
                {"range": [45, 55], "color": "#665c00"},
                {"range": [55, 75], "color": "#1f5f1f"},
                {"range": [75, 100], "color": "#0b5d1e"},
            ],
            "threshold": {"line": {"color": "white", "width": 3}, "value": fg_val},
        },
    ), row=4, col=2)

    fig.add_annotation(
        xref="paper", yref="paper", x=0.99, y=0.01,
        text="<b>— 10MA</b>(黃)  <b>··· 20MA</b>(紅)",
        showarrow=False, font=dict(color="white", size=10),
        bgcolor="rgba(0,0,0,0.5)"
    )

    fig.update_layout(
        template="plotly_dark",
        height=1150,
        hovermode="x unified",
        showlegend=False,
        margin=dict(t=60, b=40, l=50, r=50),
        paper_bgcolor="#0b1120",
        plot_bgcolor="#0d1626",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#1f2937", tickformat="%m-%d")
    fig.update_yaxes(showgrid=True, gridcolor="#1f2937")
    return fig


# ==================== 快照表格 ====================
def snapshot_html(data, fg_val, fg_date):
    rows = ""
    for name, s in data.items():
        if len(s) == 0:
            continue
        val = float(s.iloc[-1])
        prev = float(s.iloc[-2]) if len(s) > 1 else val
        chg = val - prev
        pct = (chg / prev * 100) if prev != 0 else 0
        if name == "10Y Yield":
            display = f"{val*100:.3f}%"
            chg_str = f"{chg*100:+.3f}%"
        elif name == "USD/HKD":
            display = f"{val:.4f}"
            chg_str = f"{chg:+.4f}"
        else:
            display = f"{val:,.2f}"
            chg_str = f"{chg:+.2f} ({pct:+.2f}%)"
        color_cls = "tag-up" if chg >= 0 else "tag-down"
        arrow = "▲" if chg >= 0 else "▼"
        rows += f"""<tr>
            <td>{name}</td>
            <td><b>{display}</b></td>
            <td class="{color_cls}">{arrow} {chg_str}</td>
            <td>{s.index[-1].strftime("%Y-%m-%d")}</td>
        </tr>"""

    if fg_val >= 75:
        mood = "極度貪婪"
    elif fg_val >= 55:
        mood = "貪婪"
    elif fg_val >= 45:
        mood = "中性"
    elif fg_val >= 25:
        mood = "恐懼"
    else:
        mood = "極度恐懼"
    rows += f"""<tr>
        <td>Fear & Greed</td>
        <td><b>{fg_val}</b></td>
        <td>{mood}</td>
        <td>{fg_date.strftime("%Y-%m-%d")}</td>
    </tr>"""

    return f"""
    <table class="snapshot-table">
      <thead><tr>
        <th>資產</th><th>最新值</th><th>日變動</th><th>日期</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>"""


# ==================== 主介面 ====================
st.markdown('''<div class="title-box">
  <h2 style="margin:0;color:white;">🌐 金融市場 Dashboard</h2>
  <p style="margin:4px 0 0 0;color:#9ca3af;font-size:13px;">
  S&P 500 · IWM · VIX · 10Y Yield · DXY · USD/HKD · Oil · Gold · Fear & Greed
  </p>
</div>''', unsafe_allow_html=True)

col_refresh, col_time, col_note = st.columns([1, 2, 4])

with col_refresh:
    if st.button("🔄 Refresh 更新數據", type="primary", use_container_width=True):
        fetch_market_data.clear()
        fetch_fear_greed.clear()
        st.rerun()

with col_time:
    st.markdown(
        f"<p style='color:#9ca3af;font-size:13px;padding-top:8px;'>🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')} HKT</p>",
        unsafe_allow_html=True
    )

with col_note:
    st.markdown(
        "<p style='color:#6b7280;font-size:12px;padding-top:8px;'>數據來源：Yahoo Finance · CNN · 每 5 分鐘自動緩存</p>",
        unsafe_allow_html=True
    )

st.divider()

with st.spinner("📡 正在抓取最新市場數據..."):
    data = fetch_market_data()
    fg_val, fg_date = fetch_fear_greed()

fig = build_fig(data, fg_val, fg_date)
st.plotly_chart(fig, use_container_width=True, config={
    "displaylogo": False,
    "displayModeBar": True,
    "responsive": True,
})

st.markdown("### 📋 最新數據快照（含日變動）")
st.markdown(snapshot_html(data, fg_val, fg_date), unsafe_allow_html=True)

st.markdown(
    "<p style='color:#4b5563;font-size:11px;text-align:center;margin-top:20px;'>"
    "數據由 Yahoo Finance 提供，僅供參考，不構成投資建議。</p>",
    unsafe_allow_html=True
)
