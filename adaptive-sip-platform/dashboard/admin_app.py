"""
dashboard/admin_app.py — ASRP Admin Panel (Standalone)
Deployed as SEPARATE Railway service → gets its own URL.
Password protected.

Run locally:  streamlit run dashboard/admin_app.py --server.port 8503
"""
from __future__ import annotations
import os, sys, json, requests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from dashboard.ai_agent import load_admin_config, save_admin_config, test_connection

ADMIN_PASSWORD  = os.environ.get("ADMIN_PASSWORD", "asrp2025")
ADMIN_SECRET    = os.environ.get("ADMIN_SECRET",   "asrp-admin-2025")
BACKEND_URL     = os.environ.get("BACKEND_URL",    "http://localhost:8000")

st.set_page_config(
    page_title="ASRP Admin Panel",
    page_icon="⚙️",
    layout="centered",
)

st.markdown("""
<style>
[data-testid="stSidebar"] { display: none; }
.admin-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-radius: 12px; padding: 24px; text-align: center;
    color: white !important; margin-bottom: 24px;
}
.admin-header h1, .admin-header p { color: white !important; margin: 4px 0; }
.status-ok  { background:#052e16; border:1px solid #16a34a; border-radius:8px; padding:12px; color:#4ade80 !important; }
.status-err { background:#2d0a0a; border:1px solid #dc2626; border-radius:8px; padding:12px; color:#f87171 !important; }
</style>
""", unsafe_allow_html=True)

# ── Password gate ─────────────────────────────────────────────────────────────
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    st.markdown("""
    <div class="admin-header">
        <h1>⚙️ ASRP Admin Panel</h1>
        <p>Restricted Access — Enter Password</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        pwd = st.text_input("Admin Password", type="password", placeholder="Enter password...")
        submitted = st.form_submit_button("🔐 Login", use_container_width=True, type="primary")
        if submitted:
            if pwd == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("❌ Wrong password!")
    st.stop()

# ── Main admin UI ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="admin-header">
    <h1>⚙️ ASRP Admin Panel</h1>
    <p>Configure AI, Monitor System, Manage Settings</p>
</div>
""", unsafe_allow_html=True)

col_logout = st.columns([4, 1])[1]
if col_logout.button("🚪 Logout"):
    st.session_state.admin_logged_in = False
    st.rerun()

tab_ai, tab_system, tab_logs = st.tabs(["🤖 AI Configuration", "🖥️ System Status", "📋 Logs"])

# ── TAB 1: AI CONFIG ──────────────────────────────────────────────────────────
with tab_ai:
    st.markdown("### 🔑 AI Provider & API Keys")
    cfg = load_admin_config()

    provider = st.selectbox(
        "AI Provider",
        ["claude", "gemini"],
        index=0 if cfg.get("ai_provider","claude") == "claude" else 1,
        format_func=lambda x: "🔵 Claude (Anthropic)" if x == "claude" else "🟡 Gemini (Google)",
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🔵 Claude")
        st.caption("Get key: console.anthropic.com")
        claude_key = st.text_input(
            "Claude API Key", value=cfg.get("claude_api_key",""),
            type="password", placeholder="sk-ant-api03-..."
        )
        claude_model = st.selectbox(
            "Model",
            ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
            index=["claude-opus-4-8","claude-sonnet-4-6","claude-haiku-4-5-20251001"].index(
                cfg.get("claude_model","claude-opus-4-8")
            ) if cfg.get("claude_model","claude-opus-4-8") in ["claude-opus-4-8","claude-sonnet-4-6","claude-haiku-4-5-20251001"] else 0,
        )

    with col2:
        st.markdown("#### 🟡 Gemini")
        st.caption("Get key: aistudio.google.com")
        gemini_key = st.text_input(
            "Gemini API Key", value=cfg.get("gemini_api_key",""),
            type="password", placeholder="AIza..."
        )
        gemini_model = st.selectbox(
            "Model",
            ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"],
            index=["gemini-1.5-pro","gemini-1.5-flash","gemini-2.0-flash"].index(
                cfg.get("gemini_model","gemini-1.5-pro")
            ) if cfg.get("gemini_model","gemini-1.5-pro") in ["gemini-1.5-pro","gemini-1.5-flash","gemini-2.0-flash"] else 0,
        )

    ai_enabled = st.toggle("✅ Enable AI Agent", value=cfg.get("ai_enabled", False))

    st.markdown("---")
    b1, b2 = st.columns(2)

    with b1:
        if st.button("💾 Save Config", type="primary", use_container_width=True):
            new_cfg = {
                "ai_provider":   provider,
                "claude_api_key": claude_key.strip(),
                "gemini_api_key": gemini_key.strip(),
                "claude_model":  claude_model,
                "gemini_model":  gemini_model,
                "ai_enabled":    ai_enabled,
            }
            save_admin_config(new_cfg)
            st.success("✅ Saved locally. Backend will pick up on next request.")

    with b2:
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
                st.markdown(f'<div class="status-ok">{msg}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="status-err">{msg}</div>', unsafe_allow_html=True)

    # Sync to backend if configured
    st.markdown("---")
    st.markdown("#### 🔄 Sync Config to Backend API")
    st.caption(f"Backend URL: `{BACKEND_URL}`")

    if st.button("📡 Push Config to Backend", use_container_width=True):
        try:
            payload = {
                "ai_provider":   provider,
                "claude_api_key": claude_key.strip(),
                "gemini_api_key": gemini_key.strip(),
                "claude_model":  claude_model,
                "gemini_model":  gemini_model,
                "ai_enabled":    ai_enabled,
            }
            resp = requests.post(
                f"{BACKEND_URL}/api/admin/config",
                json=payload,
                headers={"X-Admin-Secret": ADMIN_SECRET},
                timeout=10,
            )
            if resp.status_code == 200:
                st.success("✅ Config synced to backend!")
            else:
                st.error(f"❌ Backend returned {resp.status_code}: {resp.text}")
        except Exception as e:
            st.error(f"❌ Could not reach backend: {e}")

    # Current status
    st.markdown("---")
    st.markdown("#### 📊 Current Config Status")
    s1, s2, s3 = st.columns(3)
    s1.metric("AI Status",  "🟢 ON" if cfg.get("ai_enabled") else "🔴 OFF")
    s2.metric("Provider",   cfg.get("ai_provider","—").upper())
    has_key = bool(cfg.get(f"{cfg.get('ai_provider','claude')}_api_key","").strip())
    s3.metric("API Key",    "✅ Set" if has_key else "❌ Missing")


# ── TAB 2: SYSTEM STATUS ──────────────────────────────────────────────────────
with tab_system:
    st.markdown("### 🖥️ Backend Status")

    if st.button("🔄 Check Backend Health"):
        try:
            resp = requests.get(f"{BACKEND_URL}/health", timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                st.markdown(f'<div class="status-ok">✅ Backend is UP — v{data.get("version","?")}</div>',
                            unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="status-err">❌ Backend returned {resp.status_code}</div>',
                            unsafe_allow_html=True)
        except Exception as e:
            st.markdown(f'<div class="status-err">❌ Cannot reach backend: {e}</div>',
                        unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🔐 Environment Variables")
    st.caption("Set these in Railway dashboard:")
    st.code(f"""
ADMIN_PASSWORD = {ADMIN_PASSWORD[:3]}***  (currently set)
ADMIN_SECRET   = {ADMIN_SECRET[:5]}***   (currently set)
BACKEND_URL    = {BACKEND_URL}
""", language="bash")

    st.markdown("---")
    st.markdown("### 🗄️ Config File")
    from dashboard.ai_agent import ADMIN_CONFIG_PATH
    if os.path.exists(ADMIN_CONFIG_PATH):
        with open(ADMIN_CONFIG_PATH) as f:
            raw = json.load(f)
        # Mask keys
        masked = {**raw}
        for k in ("claude_api_key", "gemini_api_key"):
            if masked.get(k):
                masked[k] = masked[k][:6] + "..." + masked[k][-4:]
        st.json(masked)
    else:
        st.info("Config file not created yet. Save config first.")


# ── TAB 3: LOGS ───────────────────────────────────────────────────────────────
with tab_logs:
    st.markdown("### 📋 API Logs")
    log_path = os.path.join(os.path.dirname(__file__), "..", "logs", "api.log")
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            lines = f.readlines()[-100:]  # last 100 lines
        st.text_area("Recent Logs", "".join(lines), height=400)
    else:
        st.info("No log file found. Logs appear here when backend is running.")

    st.markdown("### 🔌 Quick API Test")
    test_endpoint = st.selectbox("Endpoint", ["/health", "/api/ticker-universes", "/api/ai/status"])
    if st.button("Test Endpoint"):
        try:
            resp = requests.get(f"{BACKEND_URL}{test_endpoint}", timeout=8)
            st.json(resp.json())
        except Exception as e:
            st.error(str(e))
