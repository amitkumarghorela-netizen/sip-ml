"""
api/main.py — ASRP FastAPI Backend
Runs on Railway. Frontend (Vercel) calls this.
"""
from __future__ import annotations
import os, sys, json
from datetime import date
from typing import Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.data_loader import generate_synthetic
from core.backtest import compare_strategies
from core.strategy_engine import load_strategy_config
from core.batch_runner import run_batch, fetch_price_series
from core.ticker_lists import TICKER_UNIVERSES
from dashboard.ai_agent import load_admin_config, save_admin_config, get_ai_response

ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "asrp-admin-2025")
ADAPTIVE_YAML = "strategies/adaptive_sip_v1_1.yaml"
TRADITIONAL_YAML = "strategies/traditional_sip.yaml"

app = FastAPI(title="ASRP API", version="2.0", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth for admin endpoints ──────────────────────────────────────────────────
def verify_admin(x_admin_secret: str = Header(default="")):
    if x_admin_secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret")


# ── Models ────────────────────────────────────────────────────────────────────
class BacktestRequest(BaseModel):
    source: str = "synthetic"       # "synthetic" | "yahoo"
    ticker: Optional[str] = None
    start: str = "2015-01-01"
    end: str = "2025-01-01"
    use_cache: bool = True

class BatchRequest(BaseModel):
    universe: str = "Nifty 50"
    strategy: str = "adaptive"      # "adaptive" | "traditional"
    start: str = "2018-01-01"
    end: str = "2025-01-01"

class ChatMessage(BaseModel):
    message: str
    history: list = []

class AdminConfig(BaseModel):
    ai_provider: str = "claude"
    claude_api_key: str = ""
    gemini_api_key: str = ""
    claude_model: str = "claude-opus-4-8"
    gemini_model: str = "gemini-1.5-pro"
    ai_enabled: bool = False


# ── Helpers ───────────────────────────────────────────────────────────────────
def safe_float(val):
    try:
        return float(str(val).replace("%", "").replace(",", ""))
    except Exception:
        return 0.0


def _run_backtest_internal(req: BacktestRequest):
    if req.source == "synthetic":
        raw = generate_synthetic(req.start, req.end)
        price_df = raw[["Date", "Close"]].rename(columns={"Close": "Price"})
        asset_name = "DEMO_ASSET"
    else:
        if not req.ticker:
            raise ValueError("ticker is required for yahoo source")
        price_df = fetch_price_series(req.ticker, req.start, req.end, use_cache=req.use_cache)
        asset_name = req.ticker

    strategy_paths = {"traditional": TRADITIONAL_YAML, "adaptive": ADAPTIVE_YAML}
    result = compare_strategies(price_df, strategy_paths, asset_name=asset_name)
    return result, asset_name, price_df


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0"}


@app.get("/api/ticker-universes")
def ticker_universes():
    return {k: list(v) for k, v in TICKER_UNIVERSES.items()}


@app.get("/api/search")
def search_ticker(ticker: str, start: str = "2015-01-01", end: str = "2025-01-01"):
    try:
        price_df = fetch_price_series(ticker, start, end)
        start_p = float(price_df["Price"].iloc[0])
        end_p   = float(price_df["Price"].iloc[-1])
        total_ret = (end_p - start_p) / start_p * 100
        # Convert dates to strings for JSON
        price_df_json = price_df.copy()
        price_df_json["Date"] = price_df_json["Date"].astype(str)
        return {
            "ticker": ticker,
            "points": len(price_df),
            "start_price": round(start_p, 2),
            "end_price":   round(end_p, 2),
            "total_return_pct": round(total_ret, 2),
            "data": price_df_json.to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/backtest")
def run_backtest(req: BacktestRequest):
    try:
        result, asset_name, price_df = _run_backtest_internal(req)
        comp = result["comparison"]
        out_results = {}
        for key, res in result["results"].items():
            txns = res["transactions"]
            # Convert dates to strings for JSON
            txns_json = []
            for t in txns:
                t_copy = dict(t)
                if hasattr(t_copy.get("Date"), "isoformat"):
                    t_copy["Date"] = t_copy["Date"].isoformat()
                elif not isinstance(t_copy.get("Date"), str):
                    t_copy["Date"] = str(t_copy["Date"])
                txns_json.append(t_copy)
            out_results[key] = {
                "strategy_name": res["strategy_name"],
                "summary": res["summary"],
                "transactions": txns_json,
            }
        # Convert price_df dates to strings for JSON
        price_df_json = price_df.copy()
        price_df_json["Date"] = price_df_json["Date"].astype(str)
        return {
            "asset_name": asset_name,
            "comparison": comp.to_dict() if hasattr(comp, "to_dict") else comp,
            "results": out_results,
            "price_data": price_df_json.to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/batch")
def run_batch_endpoint(req: BatchRequest):
    try:
        strategy_path = ADAPTIVE_YAML if req.strategy == "adaptive" else TRADITIONAL_YAML
        tickers = TICKER_UNIVERSES.get(req.universe, [])
        if not tickers:
            raise HTTPException(status_code=400, detail=f"Unknown universe: {req.universe}")
        batch = run_batch(strategy_path, tickers, req.start, req.end, batch_tag=req.universe)
        lb = batch["leaderboard"]
        return {
            "universe": req.universe,
            "total": len(tickers),
            "success": len(batch["results"]),
            "errors":  len(batch["errors"]),
            "leaderboard": lb.to_dict(orient="records") if hasattr(lb, "to_dict") else lb,
            "error_list": batch["errors"],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/ai/chat")
def ai_chat(msg: ChatMessage):
    cfg = load_admin_config()
    if not cfg.get("ai_enabled", False):
        raise HTTPException(status_code=403, detail="AI is not enabled. Configure in Admin Panel.")
    reply = get_ai_response(msg.message, msg.history, cfg)
    return {"reply": reply}


@app.get("/api/ai/status")
def ai_status():
    cfg = load_admin_config()
    return {
        "enabled": cfg.get("ai_enabled", False),
        "provider": cfg.get("ai_provider", "claude"),
    }


# ── Admin-only endpoints (require X-Admin-Secret header) ──────────────────────
@app.get("/api/admin/config", dependencies=[Depends(verify_admin)])
def get_admin_config():
    cfg = load_admin_config()
    # Mask keys in response
    masked = {**cfg}
    for k in ("claude_api_key", "gemini_api_key"):
        if masked.get(k):
            masked[k] = masked[k][:8] + "..." + masked[k][-4:]
    return masked


@app.post("/api/admin/config", dependencies=[Depends(verify_admin)])
def set_admin_config(config: AdminConfig):
    existing = load_admin_config()
    new_cfg = {
        "ai_provider":   config.ai_provider,
        "ai_enabled":    config.ai_enabled,
        "claude_model":  config.claude_model,
        "gemini_model":  config.gemini_model,
        # Only update keys if non-empty (don't wipe existing)
        "claude_api_key": config.claude_api_key if config.claude_api_key else existing.get("claude_api_key",""),
        "gemini_api_key": config.gemini_api_key if config.gemini_api_key else existing.get("gemini_api_key",""),
    }
    save_admin_config(new_cfg)
    return {"status": "saved", "ai_enabled": config.ai_enabled}
