"""
dashboard/app.py — ASRP v2.0
Adaptive SIP Research Platform — Simple, Smart, Colorful UI
"""

from __future__ import annotations
import os, sys, io
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.data_loader import generate_synthetic, download_yahoo, resample_monthly
from core.backtest import compare_strategies, run_backtest_with_config
from core.strategy_engine import load_strategy_config
from core.batch_runner import run_batch, fetch_price_series
from core.comparator import build_leaderboard
from core.optimizer import grid_search, DEFAULT_GRID
from core.ticker_lists import TICKER_UNIVERSES
from database import db_manager
from reports.report_generator import generate_excel_report
from dashboard.ai_agent import (
    load_admin_config, save_admin_config,
    get_ai_response, test_connection
)

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ASRP — Adaptive SIP Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Sidebar styling */
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0f2027 0%, #203a43 50%, #2c5364 100%) !important; }
[data-testid="stSidebar"] * { color: white !important; }
[data-testid="stSidebar"] .stRadio label { font-size: 15px !important; padding: 8px 0; }

/* Hero card */
.info-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 14px; padding: 28px 24px; margin: 10px 0;
    color: white !important; text-align: center;
}
.info-card h2, .info-card p, .info-card * { color: white !important; }

/* Stat cards — dark theme safe */
.stat-card {
    background: #1e293b;
    border-radius: 12px; padding: 18px;
    border-left: 5px solid #667eea; margin: 6px 0;
    color: #f1f5f9 !important;
}
.stat-card h4 { color: #93c5fd !important; margin-bottom: 8px; font-size: 16px; }
.stat-card p  { color: #e2e8f0 !important; margin: 4px 0; font-size: 14px; line-height: 1.5; }
.stat-card b  { color: #ffffff !important; }
.stat-card em { color: #94a3b8 !important; }

/* Page section cards */
.page-card {
    background: #1e293b;
    border-radius: 12px; padding: 18px;
    border: 1px solid #334155; margin: 6px 0;
    color: #f1f5f9 !important;
}
.page-card h4 { color: #a5b4fc !important; }
.page-card p  { color: #cbd5e1 !important; }

/* Market state badges */
.badge-bull   { background:#16a34a; color:#ffffff !important; padding:4px 12px; border-radius:20px; font-size:13px; font-weight:bold; display:inline-block; }
.badge-bear   { background:#dc2626; color:#ffffff !important; padding:4px 12px; border-radius:20px; font-size:13px; font-weight:bold; display:inline-block; }
.badge-side   { background:#d97706; color:#ffffff !important; padding:4px 12px; border-radius:20px; font-size:13px; font-weight:bold; display:inline-block; }
.badge-rec    { background:#2563eb; color:#ffffff !important; padding:4px 12px; border-radius:20px; font-size:13px; font-weight:bold; display:inline-block; }
.badge-high   { background:#065f46; color:#ffffff !important; padding:4px 12px; border-radius:20px; font-size:13px; font-weight:bold; display:inline-block; }

/* Highlight result boxes */
.highlight-green {
    background: #052e16; border: 1px solid #16a34a;
    border-radius: 10px; padding: 14px 16px; margin: 8px 0;
    color: #bbf7d0 !important;
}
.highlight-green b { color: #4ade80 !important; }
.highlight-red {
    background: #2d0a0a; border: 1px solid #dc2626;
    border-radius: 10px; padding: 14px 16px; margin: 8px 0;
    color: #fecaca !important;
}
.highlight-red b { color: #f87171 !important; }
.highlight-blue {
    background: #0c1a3a; border: 1px solid #2563eb;
    border-radius: 10px; padding: 14px 16px; margin: 8px 0;
    color: #bfdbfe !important;
}
.highlight-blue b { color: #60a5fa !important; }

/* Badge label under color code guide */
.badge-label { color: #94a3b8 !important; font-size: 12px; margin-top: 6px; display: block; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
ADAPTIVE_YAML    = "strategies/adaptive_sip_v1_1.yaml"
TRADITIONAL_YAML = "strategies/traditional_sip.yaml"

# ── Session state defaults ────────────────────────────────────────────────────
for k, v in {
    "last_compare": None, "last_asset_name": None,
    "last_price_df": None, "last_batch": None,
    "last_grid": None, "strategy_overrides": {},
    "chat_history": [], "admin_config": load_admin_config(),
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Helper: colour dataframe market states ────────────────────────────────────
STATE_COLORS = {
    "BULL":     "background-color:#052e16; color:#4ade80; font-weight:bold",
    "NEW HIGH": "background-color:#14532d; color:#86efac; font-weight:bold",
    "BEAR":     "background-color:#2d0a0a; color:#f87171; font-weight:bold",
    "SIDEWAYS": "background-color:#1c1400; color:#fcd34d; font-weight:bold",
    "RECOVERY": "background-color:#0c1a3a; color:#60a5fa; font-weight:bold",
    "FIXED":    "background-color:#1e293b; color:#94a3b8",
    "START":    "background-color:#1e293b; color:#64748b",
}


def style_market_state(val):
    return STATE_COLORS.get(str(val), "")


def style_comparison_table(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Highlight better value: dark green bg + bright green text. Worse: dark red + bright red."""
    def highlight_row(row):
        styles = ["background-color:#1e293b; color:#94a3b8"] * len(row)
        if len(row) >= 2:
            try:
                v1 = float(str(row.iloc[0]).replace("%","").replace(",",""))
                v2 = float(str(row.iloc[1]).replace("%","").replace(",",""))
                metric = str(row.name).lower() if hasattr(row, 'name') else ""
                lower_is_better = any(x in metric for x in ["mdd","drawdown","risk","volatility","expense"])
                if lower_is_better:
                    i_good, i_bad = (0, 1) if v1 < v2 else (1, 0)
                else:
                    i_good, i_bad = (0, 1) if v1 > v2 else (1, 0)
                # Good cell: dark green bg, bright green bold text
                styles[i_good] = "background-color:#052e16; color:#4ade80; font-weight:bold"
                # Bad cell: dark red bg, bright red text
                styles[i_bad]  = "background-color:#2d0a0a; color:#f87171"
            except Exception:
                pass
        return styles
    return df.style.apply(highlight_row, axis=1)


def style_leaderboard(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Top rows = bright green text on dark green, bottom = bright red on dark red."""
    n = len(df)
    top3 = max(1, min(3, n // 4))
    bot3 = max(1, min(3, n // 4))

    def row_style(idx):
        if idx < top3:
            # Dark green bg + bright green text — always visible
            return ["background-color:#052e16; color:#4ade80; font-weight:bold"] * df.shape[1]
        elif idx >= n - bot3:
            # Dark red bg + bright red text — always visible
            return ["background-color:#2d0a0a; color:#f87171; font-weight:500"] * df.shape[1]
        # Normal rows: neutral dark + light grey text
        return ["background-color:#1e293b; color:#cbd5e1"] * df.shape[1]

    return df.style.apply(lambda row: row_style(row.name), axis=1)


def get_price_series(source, ticker, start, end, use_cache=True):
    if source == "🎲 Synthetic (Demo — no internet needed)":
        raw = generate_synthetic(start, end)
        return raw[["Date","Close"]].rename(columns={"Close":"Price"}), "DEMO_ASSET"
    price_df = fetch_price_series(ticker, start, end, use_cache=use_cache)
    return price_df, ticker


def metric_delta_color(val, ref, lower_is_better=False):
    diff = val - ref
    if lower_is_better:
        return "normal" if diff < 0 else "inverse"
    return "normal" if diff > 0 else "inverse"


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 ASRP")
    st.markdown("*Adaptive SIP Research Platform*")
    st.markdown("---")
    page = st.radio(
        "📂 Pages",
        [
            "🏠 Home",
            "🔍 Market Search",
            "⚡ Run Backtest",
            "🏆 Batch Analysis",
            "🧮 SIP Calculator",
            "🤖 AI Research Agent",
            "⚙️ Admin Panel",
        ],
        label_visibility="collapsed",
    )
    st.markdown("---")
    cfg = st.session_state.admin_config
    ai_status = "🟢 AI ON" if cfg.get("ai_enabled") else "🔴 AI OFF"
    ai_provider = cfg.get("ai_provider","claude").upper()
    st.caption(f"{ai_status} · {ai_provider}")
    st.caption("v2.0 · Logic Freeze v1.1")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  PAGE 1 — HOME                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
if page == "🏠 Home":
    st.title("📈 Adaptive SIP Research Platform")
    st.markdown("##### *Samajhna aasaan, kaamyabi pakki*")
    st.markdown("---")

    st.markdown("""
    <div class="info-card">
        <h2>🎯 Ye Platform Kya Karta Hai?</h2>
        <p style='font-size:17px'>Ye ek <b>smart SIP research tool</b> hai jo aapko batata hai ki<br>
        agar aapne <b>smart tarike se</b> invest kiya hota (market ke hisab se zyada ya kam),<br>
        toh aapka paisa normal SIP se <b>kitna zyada</b> hota!</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 💡 Seedha Simple Explanation")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="stat-card">
        <h4>🔴 Market Gira (BEAR)</h4>
        <p><b>Normal aadmi:</b> ₹10,000 daal deta hai as usual</p>
        <p><b>Adaptive SIP:</b> ₹20,000–₹50,000 daalta hai</p>
        <p><em>👉 SALE chal rahi hai! Sasta milega!</em></p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="stat-card">
        <h4>🟢 Market Ucha (BULL)</h4>
        <p><b>Normal aadmi:</b> ₹10,000 daal deta hai as usual</p>
        <p><b>Adaptive SIP:</b> ₹5,000 daalta hai</p>
        <p><em>👉 Sab mehnga ho gaya, zyada khareedna waste!</em></p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="stat-card">
        <h4>🟡 Market Flat (SIDEWAYS)</h4>
        <p><b>Normal aadmi:</b> ₹10,000 as usual</p>
        <p><b>Adaptive SIP:</b> ₹10,000 as usual</p>
        <p><em>👉 Koi change nahi, bas wait karo</em></p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🚀 Kya-Kya Kar Sakte Ho Is Tool Mein")
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)

    pages_info = [
        ("🔍 Market Search", "Koi bhi stock ya ETF dhundo aur uska pura price history dekho"),
        ("⚡ Run Backtest", "Past mein Adaptive SIP ne kitna zyada return diya — color-coded results"),
        ("🏆 Batch Analysis", "Ek saath 50 stocks check karo — leaderboard mein best/worst dekho"),
        ("🧮 SIP Calculator", "Simple calculator: kitna daalo, kitne saal, kitna milega"),
        ("🤖 AI Agent", "AI se poocho — 'Reliance acchi hai?', 'Nifty SIP karna chahiye?'"),
        ("⚙️ Admin Panel", "Claude ya Gemini API key daalo, AI enable karo, settings badlo"),
    ]
    cols = st.columns(3)
    for i, (title, desc) in enumerate(pages_info):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="stat-card">
            <h4>{title}</h4>
            <p>{desc}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🎨 Color Code Guide — Ek Nazar Mein Samjho")
    cc1, cc2, cc3, cc4, cc5 = st.columns(5)
    with cc1:
        st.markdown('<div class="badge-high">NEW HIGH 💚</div><span class="badge-label">Naya all-time high<br>SIP kam karo</span>', unsafe_allow_html=True)
    with cc2:
        st.markdown('<div class="badge-bull">BULL 🟢</div><span class="badge-label">Market upar<br>SIP halka kam karo</span>', unsafe_allow_html=True)
    with cc3:
        st.markdown('<div class="badge-side">SIDEWAYS 🟡</div><span class="badge-label">Market flat<br>SIP same rakho</span>', unsafe_allow_html=True)
    with cc4:
        st.markdown('<div class="badge-rec">RECOVERY 🔵</div><span class="badge-label">Sudhar ho raha<br>SIP high rakho</span>', unsafe_allow_html=True)
    with cc5:
        st.markdown('<div class="badge-bear">BEAR 🔴</div><span class="badge-label">Market gira<br>SIP badhao (SALE!)</span>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### ⚡ Shuru Karo — 3 Steps")
    st.markdown("""
    1. **⚡ Run Backtest** page pe jao
    2. **"🎲 Synthetic Demo"** select karo (internet ki zaroorat nahi)
    3. **"Run Backtest"** button dabao — result aa jayega! 🎉
    """)
    st.success("💡 Real stocks ke liye: Market Search → apna stock dhundo → Backtest chalao")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  PAGE 2 — MARKET SEARCH                                                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
elif page == "🔍 Market Search":
    st.title("🔍 Market Search")
    st.info("**Ye page kya karta hai:** Koi bhi stock, index, ya ETF ka price history dekho. "
            "Backtest chalane se pehle yahan se stock check karo.")

    tab_stock, tab_mf, tab_us = st.tabs(["🇮🇳 Indian Stocks / Index", "📦 Indian ETFs / MF Proxy", "🇺🇸 US Stocks"])

    POPULAR_INDIAN = {
        "Nifty 50 Index": "^NSEI",
        "Sensex": "^BSESN",
        "Reliance Industries": "RELIANCE.NS",
        "TCS": "TCS.NS",
        "HDFC Bank": "HDFCBANK.NS",
        "Infosys": "INFY.NS",
        "ICICI Bank": "ICICIBANK.NS",
        "Wipro": "WIPRO.NS",
        "Bajaj Finance": "BAJFINANCE.NS",
        "Axis Bank": "AXISBANK.NS",
    }
    POPULAR_ETF = {
        "Nifty BeES (Nippon ETF)": "NIFTYBEES.NS",
        "SBI Nifty ETF": "SETFNIF50.NS",
        "Kotak Banking ETF": "KOTAKBKETF.NS",
        "Gold BeES": "GOLDBEES.NS",
        "Mirae Asset Nifty ETF": "MAFANG.NS",
        "Bharat Bond ETF Apr 2030": "EBBETF0430.NS",
    }
    POPULAR_US = {
        "S&P 500 ETF (SPY)": "SPY",
        "Apple": "AAPL",
        "Microsoft": "MSFT",
        "Google (Alphabet)": "GOOGL",
        "Tesla": "TSLA",
        "Amazon": "AMZN",
        "NVIDIA": "NVDA",
        "Meta": "META",
        "Nasdaq ETF (QQQ)": "QQQ",
    }

    def search_tab(popular_dict, example_ticker, key_prefix):
        mode = st.radio("Search mode", ["Popular picks", "Type manually"], horizontal=True, key=f"{key_prefix}_mode")
        if mode == "Popular picks":
            name = st.selectbox("Select", list(popular_dict.keys()), key=f"{key_prefix}_sel")
            ticker = popular_dict[name]
            st.caption(f"Yahoo Finance ticker: `{ticker}`")
        else:
            ticker = st.text_input("Ticker (Yahoo Finance format)", value=example_ticker, key=f"{key_prefix}_txt")

        c1, c2 = st.columns(2)
        start = c1.date_input("From", value=date(2015,1,1), key=f"{key_prefix}_s").isoformat()
        end   = c2.date_input("To",   value=date(2025,1,1), key=f"{key_prefix}_e").isoformat()

        if st.button("🔍 Search & Preview", key=f"{key_prefix}_btn", type="primary"):
            with st.spinner("Fetching data from Yahoo Finance..."):
                try:
                    price_df = fetch_price_series(ticker, start, end)
                    st.success(f"✅ {ticker} — {len(price_df)} monthly data points loaded.")
                    start_p, end_p = price_df["Price"].iloc[0], price_df["Price"].iloc[-1]
                    total_ret = (end_p - start_p) / start_p * 100
                    col_a, col_b, col_c = st.columns(3)
                    col_a.metric("Start Price", f"₹{start_p:,.2f}" if ".NS" in ticker or "^N" in ticker or "^B" in ticker else f"${start_p:,.2f}")
                    col_b.metric("End Price",   f"₹{end_p:,.2f}"   if ".NS" in ticker or "^N" in ticker or "^B" in ticker else f"${end_p:,.2f}")
                    col_c.metric("Total Return", f"{total_ret:+.1f}%", delta=f"{total_ret:+.1f}%")
                    fig = px.line(price_df, x="Date", y="Price", title=f"{ticker} — Monthly Price History",
                                  color_discrete_sequence=["#667eea"])
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
                    with st.expander("📋 Raw Data Table"):
                        st.dataframe(price_df, use_container_width=True)
                    st.info("👉 Ab **⚡ Run Backtest** page pe jao aur is ticker se backtest chalao!")
                except Exception as exc:
                    st.error(f"❌ Data fetch failed: {exc}")
                    st.warning("💡 Tip: Internet connected hai? Ticker format sahi hai? (.NS for Indian stocks)")

    with tab_stock:
        st.markdown("**Indian stocks ke liye `.NS` suffix use karo** (e.g. `RELIANCE.NS`, `TCS.NS`)")
        search_tab(POPULAR_INDIAN, "RELIANCE.NS", "ind")

    with tab_mf:
        st.markdown("**Indian Mutual Funds directly available nahi hote.** ETFs best proxy hain — same strategy same fund.")
        st.markdown("""
        | Agar tumhara Fund hai | To ye ETF use karo |
        |---|---|
        | Nifty 50 Index Fund | `NIFTYBEES.NS` |
        | Gold Fund | `GOLDBEES.NS` |
        | Banking Fund | `KOTAKBKETF.NS` |
        """)
        search_tab(POPULAR_ETF, "NIFTYBEES.NS", "etf")

    with tab_us:
        st.markdown("**US stocks ke liye ticker as-is use karo** (e.g. `AAPL`, `SPY`, `GOOGL`)")
        search_tab(POPULAR_US, "SPY", "us")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  PAGE 3 — RUN BACKTEST                                                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
elif page == "⚡ Run Backtest":
    st.title("⚡ Run Backtest")
    st.info("**Ye page kya karta hai:** Koi bhi stock ya index pe test karo — agar Adaptive SIP aur "
            "Traditional SIP dono chalate to past mein kitna return milta. Result color-coded ayega: "
            "🟢 better, 🔴 worse.")

    source = st.radio(
        "📡 Data Source",
        ["🎲 Synthetic (Demo — no internet needed)", "🌐 Yahoo Finance (real data)"],
        horizontal=True
    )
    ticker = None
    if "Yahoo" in source:
        ticker = st.text_input("Ticker (e.g. `^NSEI`, `RELIANCE.NS`, `AAPL`)", value="^NSEI")
        st.caption("Indian: `RELIANCE.NS`, Index: `^NSEI`, US: `AAPL`")

    c1, c2, c3 = st.columns(3)
    start      = c1.date_input("Start Date", value=date(2015,1,1), key="rb_s").isoformat()
    end        = c2.date_input("End Date",   value=date(2025,1,1), key="rb_e").isoformat()
    use_cache  = c3.checkbox("💾 Use DuckDB cache", value=True)

    if st.button("🚀 Run Backtest", type="primary", use_container_width=True):
        with st.spinner("Backtest chal raha hai... thoda wait karo 🏃"):
            try:
                price_df, asset_name = get_price_series(source, ticker, start, end, use_cache)
                strategy_paths = {"traditional": TRADITIONAL_YAML, "adaptive": ADAPTIVE_YAML}
                result = compare_strategies(price_df, strategy_paths, asset_name=asset_name)
                st.session_state.last_compare   = result
                st.session_state.last_asset_name = asset_name
                st.session_state.last_price_df   = price_df
                st.balloons()
                st.success(f"✅ Backtest complete for **{asset_name}**!")
            except Exception as exc:
                st.error(f"❌ Backtest failed: {exc}")

    if st.session_state.last_compare:
        result = st.session_state.last_compare

        # ── Comparison summary with color ─────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📊 Result — Kaun Jita?")

        comp_df = result["comparison"].copy()

        # Show side-by-side metrics
        res = result["results"]
        keys = list(res.keys())

        if len(keys) >= 2:
            k_trad = [k for k in keys if "traditional" in k.lower() or "fixed" in k.lower()]
            k_adap = [k for k in keys if "adaptive" in k.lower()]
            k_trad = k_trad[0] if k_trad else keys[0]
            k_adap = k_adap[0] if k_adap else keys[1]

            trad_sum = res[k_trad]["summary"]
            adap_sum = res[k_adap]["summary"]

            def safe_float(val):
                try: return float(str(val).replace("%","").replace(",",""))
                except: return 0.0

            metric_pairs = [
                ("XIRR %",         "XIRR %",           False),
                ("CAGR %",         "CAGR %",            False),
                ("Sharpe Ratio",   "Sharpe Ratio",      False),
                ("Max Drawdown %", "Max Drawdown %",    True),
                ("Total Return %", "Total Return %",    False),
            ]

            col_t, col_a = st.columns(2)
            col_t.markdown(f"### 📌 Traditional SIP")
            col_a.markdown(f"### 🚀 Adaptive SIP v1.1")

            adaptive_wins = 0
            for label, key, lower_better in metric_pairs:
                tv = safe_float(trad_sum.get(key, 0))
                av = safe_float(adap_sum.get(key, 0))
                adaptive_better = av < tv if lower_better else av > tv
                if adaptive_better:
                    adaptive_wins += 1

                delta_val = av - tv
                delta_str = f"{delta_val:+.2f}%"
                col_t.metric(label, f"{tv:.2f}%" if "%" in label else f"{tv:.3f}")
                col_a.metric(label, f"{av:.2f}%" if "%" in label else f"{av:.3f}",
                             delta=delta_str if adaptive_better else delta_str,
                             delta_color="normal" if adaptive_better else "inverse")

            st.markdown("---")
            if adaptive_wins >= 3:
                st.markdown(f'<div class="highlight-green"><b>🏆 Adaptive SIP NE JEETA!</b><br>'
                            f'Adaptive SIP better raha <b>{adaptive_wins}/5</b> key metrics mein.<br>'
                            'Smart investing pays off! 💪</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="highlight-blue"><b>ℹ️ Result Mixed Raha</b><br>'
                            'Traditional SIP better raha zyada metrics mein is dataset pe.<br>'
                            'Note: Adaptive SIP shines during volatile/bear markets.</div>', unsafe_allow_html=True)

        # ── Full comparison table ─────────────────────────────────────────────
        with st.expander("📋 Full Metrics Table (styled)", expanded=True):
            try:
                styled = style_comparison_table(comp_df)
                st.dataframe(styled, use_container_width=True)
            except Exception:
                st.dataframe(comp_df, use_container_width=True)

        # ── Transaction tables per strategy ───────────────────────────────────
        st.markdown("### 📅 Monthly Transaction Log")
        tabs = st.tabs([res[k]["strategy_name"] for k in keys])
        for tab, key in zip(tabs, keys):
            with tab:
                txn_df = pd.DataFrame(res[key]["transactions"])
                if "Market State" in txn_df.columns:
                    try:
                        styled_txn = txn_df.style.applymap(
                            style_market_state, subset=["Market State"]
                        )
                        st.dataframe(styled_txn, use_container_width=True, height=400)
                    except Exception:
                        st.dataframe(txn_df, use_container_width=True, height=400)
                else:
                    st.dataframe(txn_df, use_container_width=True, height=400)

                # Key highlight stats
                if "Current SIP" in txn_df.columns and "Market State" in txn_df.columns:
                    bear_months = (txn_df["Market State"] == "BEAR").sum()
                    bull_months = (txn_df["Market State"].isin(["BULL","NEW HIGH"])).sum()
                    max_sip = txn_df["Current SIP"].max()
                    min_sip = txn_df["Current SIP"].min()
                    h1, h2, h3, h4 = st.columns(4)
                    h1.metric("🔴 Bear Months", int(bear_months), help="Months jab zyada invest kiya")
                    h2.metric("🟢 Bull Months", int(bull_months), help="Months jab kam invest kiya")
                    h3.metric("📈 Max SIP",     f"₹{max_sip:,.0f}")
                    h4.metric("📉 Min SIP",     f"₹{min_sip:,.0f}")

        # ── Charts ────────────────────────────────────────────────────────────
        st.markdown("### 📈 Visual Charts")
        chart_tabs = st.tabs(["Portfolio Growth", "SIP Amount", "Drawdown"])
        with chart_tabs[0]:
            fig = go.Figure()
            for key in keys:
                txn_df = pd.DataFrame(res[key]["transactions"])
                name = res[key]["strategy_name"]
                color = "#28a745" if "adaptive" in key.lower() else "#6c757d"
                fig.add_trace(go.Scatter(
                    x=txn_df["Date"], y=txn_df["Portfolio Value"],
                    name=f"{name} — Portfolio", line=dict(color=color, width=2)
                ))
                fig.add_trace(go.Scatter(
                    x=txn_df["Date"], y=txn_df["Total Investment"],
                    name=f"{name} — Invested", line=dict(color=color, dash="dash", width=1)
                ))
            fig.update_layout(title="Portfolio Value vs Total Investment", height=450,
                              legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig, use_container_width=True)

        with chart_tabs[1]:
            fig2 = go.Figure()
            for key in keys:
                txn_df = pd.DataFrame(res[key]["transactions"])
                if "Current SIP" in txn_df.columns:
                    name = res[key]["strategy_name"]
                    color = "#667eea" if "adaptive" in key.lower() else "#adb5bd"
                    fig2.add_trace(go.Scatter(
                        x=txn_df["Date"], y=txn_df["Current SIP"],
                        name=name, fill="tozeroy" if "adaptive" in key.lower() else None,
                        line=dict(color=color)
                    ))
            fig2.update_layout(title="Monthly SIP Amount Over Time", height=400)
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("🔴 Peak = bear market mein zyada invest kiya (SALE!) | 🔵 Trough = bull market mein kam invest kiya (mehnga)")

        with chart_tabs[2]:
            for key in keys:
                txn_df = pd.DataFrame(res[key]["transactions"])
                if "Drawdown %" in txn_df.columns:
                    fig3 = px.area(txn_df, x="Date", y="Drawdown %",
                                   title=f"Drawdown % — {res[key]['strategy_name']}",
                                   color_discrete_sequence=["#dc3545"])
                    fig3.update_layout(height=350)
                    st.plotly_chart(fig3, use_container_width=True)

        # ── Download ──────────────────────────────────────────────────────────
        st.markdown("---")
        asset_name = st.session_state.last_asset_name or "ASSET"
        try:
            tmp_path = "reports/output/_dash_tmp.xlsx"
            os.makedirs("reports/output", exist_ok=True)
            generate_excel_report(result, tmp_path, asset_name=asset_name)
            with open(tmp_path, "rb") as f:
                st.download_button(
                    "📥 Download Full Excel Report",
                    f.read(),
                    file_name=f"ASRP_{asset_name}_Report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
        except Exception as exc:
            st.warning(f"Excel report generate nahi hua: {exc}")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  PAGE 4 — BATCH ANALYSIS                                                   ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
elif page == "🏆 Batch Analysis":
    st.title("🏆 Batch Analysis")
    st.info("**Ye page kya karta hai:** Ek saath kaafi stocks pe backtest chalao. "
            "Leaderboard mein 🟢 **Top performers** aur 🔴 **Worst performers** clearly dikhenge.")

    universe = st.selectbox("📦 Stock Universe", list(TICKER_UNIVERSES.keys()))
    strategy_choice = st.selectbox("🎯 Strategy", ["Adaptive SIP v1.1", "Traditional SIP"])
    strategy_path = ADAPTIVE_YAML if "Adaptive" in strategy_choice else TRADITIONAL_YAML

    c1, c2 = st.columns(2)
    start = c1.date_input("Start", value=date(2018,1,1), key="batch_s").isoformat()
    end   = c2.date_input("End",   value=date(2025,1,1), key="batch_e").isoformat()

    tickers = TICKER_UNIVERSES[universe]
    st.caption(f"🔢 Total tickers in {universe}: **{len(tickers)}**")

    if st.button(f"🚀 Run Batch — {len(tickers)} stocks", type="primary", use_container_width=True):
        progress_bar = st.progress(0, text="Starting batch...")

        def progress(i, total, ticker_name):
            progress_bar.progress(i / total, text=f"({i}/{total}) Checking: {ticker_name}")

        with st.spinner("Batch chal raha hai... sabr rakho ☕"):
            batch = run_batch(strategy_path, tickers, start, end,
                              batch_tag=universe, progress_cb=progress)
        st.session_state.last_batch = batch
        progress_bar.progress(1.0, text="Done! 🎉")
        ok = len(batch["results"])
        fail = len(batch["errors"])
        st.success(f"✅ Batch complete! **{ok} stocks** processed, {fail} failed.")

    if st.session_state.last_batch:
        batch = st.session_state.last_batch
        lb = batch["leaderboard"]

        st.markdown("### 🏆 Leaderboard")
        st.markdown("🟢 **Top rows = Best performers** | 🔴 **Bottom rows = Worst performers**")

        try:
            styled_lb = style_leaderboard(lb)
            st.dataframe(styled_lb, use_container_width=True, height=500)
        except Exception:
            st.dataframe(lb, use_container_width=True, height=500)

        # Top 3 and Bottom 3 highlights
        if len(lb) >= 3:
            st.markdown("---")
            col_best, col_worst = st.columns(2)
            with col_best:
                st.markdown("### 🥇 Top 3 Stocks")
                for _, row in lb.head(3).iterrows():
                    ticker_val = row.get("Ticker", row.iloc[0])
                    xirr_val = row.get("XIRR %", row.get("CAGR %", "N/A"))
                    st.markdown(f'<div class="highlight-green">🏆 <b>{ticker_val}</b><br>XIRR: <b>{xirr_val}</b></div>',
                                unsafe_allow_html=True)
            with col_worst:
                st.markdown("### ⚠️ Bottom 3 Stocks")
                for _, row in lb.tail(3).iterrows():
                    ticker_val = row.get("Ticker", row.iloc[0])
                    xirr_val = row.get("XIRR %", row.get("CAGR %", "N/A"))
                    st.markdown(f'<div class="highlight-red">📉 <b>{ticker_val}</b><br>XIRR: <b>{xirr_val}</b></div>',
                                unsafe_allow_html=True)

        if batch["errors"]:
            with st.expander(f"⚠️ {len(batch['errors'])} failed tickers"):
                st.json(batch["errors"])

        csv_bytes = lb.to_csv(index=False).encode()
        st.download_button("📥 Download Leaderboard CSV", csv_bytes,
                           file_name="batch_leaderboard.csv")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  PAGE 5 — SIP CALCULATOR                                                   ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
elif page == "🧮 SIP Calculator":
    st.title("🧮 SIP Calculator")
    st.info("**Ye page kya karta hai:** Simple calculator — daalo kitna, kitne saal ke liye, "
            "kya expected return hai — aur dekho kitna milega!")

    tab_simple, tab_adaptive = st.tabs(["📌 Traditional SIP Calculator", "🚀 Adaptive SIP Estimator"])

    with tab_simple:
        st.markdown("### 💰 Simple SIP Calculator")
        st.markdown("*Monthly ek fixed amount daalo — compound magic dekho!*")

        col1, col2, col3 = st.columns(3)
        monthly_sip = col1.number_input("Monthly SIP (₹)", min_value=500, max_value=1000000,
                                         value=10000, step=500)
        annual_return = col2.number_input("Expected Annual Return (%)", min_value=1.0,
                                           max_value=50.0, value=12.0, step=0.5)
        tenure_years = col3.number_input("Investment Period (Years)", min_value=1,
                                          max_value=40, value=10, step=1)

        if st.button("🧮 Calculate", type="primary", key="calc_simple"):
            n = tenure_years * 12
            r = annual_return / 100 / 12
            if r > 0:
                fv = monthly_sip * ((((1 + r)**n) - 1) / r) * (1 + r)
            else:
                fv = monthly_sip * n

            total_invested = monthly_sip * n
            profit = fv - total_invested

            st.markdown("---")
            rc1, rc2, rc3 = st.columns(3)
            rc1.metric("💵 Total Invested",  f"₹{total_invested:,.0f}")
            rc2.metric("💰 Estimated Corpus", f"₹{fv:,.0f}",
                       delta=f"+₹{profit:,.0f} profit")
            rc3.metric("📈 Profit Earned",   f"₹{profit:,.0f}",
                       delta=f"{profit/total_invested*100:.1f}% gain")

            # Pie chart
            fig = go.Figure(data=[go.Pie(
                labels=["Amount Invested", "Profit Earned"],
                values=[total_invested, profit],
                colors=["#667eea", "#28a745"],
                hole=0.4,
            )])
            fig.update_layout(title=f"₹{fv:,.0f} Corpus Breakdown", height=350)
            st.plotly_chart(fig, use_container_width=True)

            # Year-wise growth table
            rows = []
            cumulative = 0
            for yr in range(1, tenure_years + 1):
                months_done = yr * 12
                r_ = annual_return / 100 / 12
                if r_ > 0:
                    corpus = monthly_sip * ((((1 + r_)**months_done) - 1) / r_) * (1 + r_)
                else:
                    corpus = monthly_sip * months_done
                inv = monthly_sip * months_done
                rows.append({"Year": yr, "Total Invested (₹)": f"{inv:,.0f}",
                              "Corpus (₹)": f"{corpus:,.0f}",
                              "Profit (₹)": f"{corpus-inv:,.0f}"})
            yr_df = pd.DataFrame(rows)
            with st.expander("📋 Year-by-Year Breakdown"):
                st.dataframe(yr_df, use_container_width=True)

    with tab_adaptive:
        st.markdown("### 🚀 Adaptive SIP Estimator")
        st.markdown("*Dikhata hai ki Adaptive SIP ne HISTORICALLY kitna alag result diya hoga.*")

        col1, col2, col3 = st.columns(3)
        base_sip_calc = col1.number_input("Base SIP (₹)", value=10000, step=500, key="adap_sip")
        source_calc = col2.selectbox("Data Source",
            ["🎲 Synthetic Demo", "🌐 Yahoo Finance"])
        ticker_calc = None
        if "Yahoo" in source_calc:
            ticker_calc = col3.text_input("Ticker", value="^NSEI", key="adap_ticker")

        c1, c2 = st.columns(2)
        start_calc = c1.date_input("Start", value=date(2015,1,1), key="calc_s").isoformat()
        end_calc   = c2.date_input("End",   value=date(2025,1,1), key="calc_e").isoformat()

        if st.button("🚀 Run Adaptive Estimate", type="primary", key="calc_adap"):
            with st.spinner("Calculating..."):
                try:
                    price_df, asset_name = get_price_series(
                        "🎲 Synthetic (Demo — no internet needed)" if "Synthetic" in source_calc else "🌐 Yahoo Finance (real data)",
                        ticker_calc, start_calc, end_calc
                    )
                    strategy_paths = {"traditional": TRADITIONAL_YAML, "adaptive": ADAPTIVE_YAML}
                    result = compare_strategies(price_df, strategy_paths, asset_name=asset_name)

                    res = result["results"]
                    keys = list(res.keys())
                    k_trad = next((k for k in keys if "traditional" in k.lower()), keys[0])
                    k_adap = next((k for k in keys if "adaptive" in k.lower()), keys[-1])

                    ts = res[k_trad]["summary"]
                    as_ = res[k_adap]["summary"]

                    def sf(v):
                        try: return float(str(v).replace("%","").replace(",",""))
                        except: return 0.0

                    st.markdown("---")
                    st.markdown(f"### Result for **{asset_name}**")
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        st.markdown("#### 📌 Traditional SIP")
                        st.metric("XIRR", f"{sf(ts.get('XIRR %',0)):.2f}%")
                        st.metric("Total Return", f"{sf(ts.get('Total Return %',0)):.2f}%")
                        st.metric("Final Corpus", f"₹{sf(ts.get('Portfolio Value',0)):,.0f}")
                    with cc2:
                        st.markdown("#### 🚀 Adaptive SIP")
                        adap_xirr = sf(as_.get("XIRR %",0))
                        trad_xirr = sf(ts.get("XIRR %",0))
                        st.metric("XIRR", f"{adap_xirr:.2f}%",
                                  delta=f"{adap_xirr-trad_xirr:+.2f}%")
                        adap_ret = sf(as_.get("Total Return %",0))
                        trad_ret = sf(ts.get("Total Return %",0))
                        st.metric("Total Return", f"{adap_ret:.2f}%",
                                  delta=f"{adap_ret-trad_ret:+.2f}%")
                        adap_pv = sf(as_.get("Portfolio Value",0))
                        trad_pv = sf(ts.get("Portfolio Value",0))
                        st.metric("Final Corpus", f"₹{adap_pv:,.0f}",
                                  delta=f"+₹{adap_pv-trad_pv:,.0f}")
                    st.info("💡 Ye historical estimate hai. Real results vary karte hain market conditions ke hisab se.")
                except Exception as exc:
                    st.error(f"❌ Error: {exc}")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  PAGE 6 — AI RESEARCH AGENT                                                ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
elif page == "🤖 AI Research Agent":
    st.title("🤖 AI Research Agent")
    cfg = st.session_state.admin_config

    if not cfg.get("ai_enabled", False):
        st.warning("⚠️ AI abhi OFF hai! **Admin Panel** pe jao, API key daalo, AI ON karo.")
        st.info("💡 Supported: **Claude** (Anthropic) aur **Gemini** (Google) — dono kaam karte hain!")
        st.stop()

    provider = cfg.get("ai_provider", "claude").upper()
    model_name = cfg.get("claude_model" if provider == "CLAUDE" else "gemini_model", "")
    st.info(f"**Ye page kya karta hai:** AI se stocks, funds, SIP strategy ke baare mein poocho. "
            f"AI real financial knowledge ke saath jawab dega. | Active: **{provider}** — `{model_name}`")

    # Suggested questions
    st.markdown("#### 💬 Kuch sawal poocho...")
    sugg_cols = st.columns(3)
    suggestions = [
        "Nifty 50 mein SIP karna chahiye ya gold?",
        "HDFC Top 100 Fund kaisa hai?",
        "2008 crash mein kya hua tha?",
        "Adaptive SIP ka sabse bada faayda kya hai?",
        "US stocks mein invest karna chahiye?",
        "₹5000/month SIP mein 20 saal mein kitna milega?",
    ]
    for i, col in enumerate(sugg_cols * 2):
        if i < len(suggestions):
            if col.button(f"💭 {suggestions[i]}", key=f"sugg_{i}", use_container_width=True):
                st.session_state.chat_history.append(
                    {"role": "user", "content": suggestions[i]}
                )

    st.markdown("---")

    # Chat history display
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(msg["content"])

    # Chat input
    user_input = st.chat_input("Kuch bhi poocho stocks, funds, SIP ke baare mein...")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner(f"{provider} soch raha hai... 🤔"):
                reply = get_ai_response(
                    user_input,
                    st.session_state.chat_history[:-1],
                    cfg
                )
            st.markdown(reply)
            st.session_state.chat_history.append({"role": "assistant", "content": reply})

    if st.session_state.chat_history:
        if st.button("🗑️ Chat Clear Karo", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  PAGE 7 — ADMIN PANEL                                                      ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
elif page == "⚙️ Admin Panel":
    st.title("⚙️ Admin Panel")
    st.info("**Ye page kya karta hai:** AI ke liye API key daalo. Claude (Anthropic) ya Gemini (Google) "
            "— jo bhi tumhare paas ho. Key save hogi aur AI Research Agent ready ho jayega!")

    tab_ai, tab_strategy, tab_data = st.tabs(["🤖 AI Configuration", "📊 Strategy Settings", "💾 Data Cache"])

    with tab_ai:
        st.markdown("### 🔑 AI API Key Setup")

        cfg = st.session_state.admin_config

        provider = st.selectbox(
            "🤖 AI Provider (kaun sa use karna hai?)",
            ["claude", "gemini"],
            index=0 if cfg.get("ai_provider","claude") == "claude" else 1,
            format_func=lambda x: "🔵 Claude (Anthropic)" if x == "claude" else "🟡 Gemini (Google)"
        )

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🔵 Claude (Anthropic)")
            st.markdown("API key lene ke liye: [console.anthropic.com](https://console.anthropic.com)")
            claude_key = st.text_input(
                "Claude API Key",
                value=cfg.get("claude_api_key",""),
                type="password",
                placeholder="sk-ant-api03-...",
                key="claude_key_input"
            )
            claude_model = st.selectbox(
                "Claude Model",
                ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
                index=["claude-opus-4-8","claude-sonnet-4-6","claude-haiku-4-5-20251001"].index(
                    cfg.get("claude_model","claude-opus-4-8")
                ) if cfg.get("claude_model","claude-opus-4-8") in ["claude-opus-4-8","claude-sonnet-4-6","claude-haiku-4-5-20251001"] else 0,
                help="Opus = best, Sonnet = balanced, Haiku = fast & cheap"
            )

        with col2:
            st.markdown("#### 🟡 Gemini (Google)")
            st.markdown("API key lene ke liye: [aistudio.google.com](https://aistudio.google.com)")
            gemini_key = st.text_input(
                "Gemini API Key",
                value=cfg.get("gemini_api_key",""),
                type="password",
                placeholder="AIza...",
                key="gemini_key_input"
            )
            gemini_model = st.selectbox(
                "Gemini Model",
                ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"],
                index=["gemini-1.5-pro","gemini-1.5-flash","gemini-2.0-flash"].index(
                    cfg.get("gemini_model","gemini-1.5-pro")
                ) if cfg.get("gemini_model","gemini-1.5-pro") in ["gemini-1.5-pro","gemini-1.5-flash","gemini-2.0-flash"] else 0,
                help="1.5 Pro = best, Flash = fast & cheap"
            )

        ai_enabled = st.toggle(
            "✅ AI Enable Karo",
            value=cfg.get("ai_enabled", False),
            help="Is toggle se AI Research Agent ON/OFF hota hai"
        )

        st.markdown("---")
        save_col, test_col = st.columns(2)
        with save_col:
            if st.button("💾 Save Configuration", type="primary", use_container_width=True):
                new_cfg = {
                    "ai_provider":   provider,
                    "claude_api_key": claude_key.strip(),
                    "gemini_api_key": gemini_key.strip(),
                    "claude_model":  claude_model,
                    "gemini_model":  gemini_model,
                    "ai_enabled":    ai_enabled,
                }
                save_admin_config(new_cfg)
                st.session_state.admin_config = new_cfg
                st.success("✅ Configuration saved! AI is now " + ("ON 🟢" if ai_enabled else "OFF 🔴"))

        with test_col:
            if st.button("🔌 Test Connection", use_container_width=True):
                test_cfg = {
                    "ai_provider":   provider,
                    "claude_api_key": claude_key.strip(),
                    "gemini_api_key": gemini_key.strip(),
                    "claude_model":  claude_model,
                    "gemini_model":  gemini_model,
                    "ai_enabled":    True,
                }
                with st.spinner("Testing..."):
                    ok, msg = test_connection(test_cfg)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

        st.markdown("---")
        st.markdown("#### 📋 Current Status")
        current_cfg = st.session_state.admin_config
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("AI Status", "🟢 ON" if current_cfg.get("ai_enabled") else "🔴 OFF")
        sc2.metric("Provider", current_cfg.get("ai_provider","—").upper())
        has_key = bool(current_cfg.get(f"{current_cfg.get('ai_provider','claude')}_api_key","").strip())
        sc3.metric("API Key", "✅ Set" if has_key else "❌ Not Set")

    with tab_strategy:
        st.markdown("### 📊 Strategy Parameters (Logic Freeze v1.1)")
        st.caption("In parameters ko change karne se sirf is session ke backtests affect honge (YAML file change nahi hoga).")

        base_cfg = load_strategy_config(ADAPTIVE_YAML)["config"]
        overrides = st.session_state.strategy_overrides

        st.markdown("#### 📖 Parameters Kya Hain?")
        param_help = {
            "BASE_SIP (₹)": ("base_sip", 10000.0,
                "Normal mahine mein kitna invest karna hai (baseline)", False),
            "MINIMUM_SIP (₹)": ("minimum_sip", 2500.0,
                "Bull market mein bhi is se kam nahi karenge", False),
            "REDUCTION_FACTOR": ("reduction_factor", 0.5,
                "Bull mein SIP ko X se multiply karo. 0.5 = half kar do", False),
            "DRAWDOWN_STEP (%)": ("drawdown_step", 5.0,
                "Har 5% ki giri pe ek naya 'slab' count hota hai", False),
            "STEP_MULTIPLIER": ("step_multiplier", 0.5,
                "Har slab ke liye SIP mein itna zyada add hoga BASE se", False),
            "MAX_MULTIPLIER": ("max_multiplier", 5.0,
                "SIP kabhi bhi BASE × MAX se zyada nahi hogi", False),
        }

        new_overrides = {}
        for label, (key, default, help_text, _) in param_help.items():
            current_val = float(overrides.get(key, base_cfg.get(key, default)))
            col_l, col_r = st.columns([2, 1])
            col_l.markdown(f"**{label}** — *{help_text}*")
            val = col_r.number_input(label, value=current_val, key=f"sp_{key}",
                                      label_visibility="collapsed")
            new_overrides[key] = val

        c_save, c_reset = st.columns(2)
        if c_save.button("💾 Save Strategy Overrides"):
            st.session_state.strategy_overrides = new_overrides
            st.success("Saved for this session!")
        if c_reset.button("🔄 Reset to Defaults"):
            st.session_state.strategy_overrides = {}
            st.success("Reset to Logic Freeze v1.1 defaults!")

    with tab_data:
        st.markdown("### 💾 DuckDB Price Cache")
        st.caption(f"Cache path: `{db_manager.DEFAULT_DB_PATH}`")

        try:
            cached = db_manager.list_cached_tickers()
            if len(cached) > 0:
                st.success(f"✅ {len(cached)} tickers cached")
                st.dataframe(cached, use_container_width=True)
            else:
                st.info("Cache abhi khaali hai. Koi bhi real data backtest chalao to data cache ho jayega.")
        except Exception as exc:
            st.info(f"Cache info load nahi hua: {exc}")

        if st.button("🔄 Refresh Cache View"):
            st.rerun()
