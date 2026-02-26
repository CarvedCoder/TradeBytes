"""
FinAI Visualization Platform — FastAPI Backend
Production-grade API for all 5 visualization modules
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import market, portfolio, regime, trades

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = FastAPI(title="FinAI Viz API", version="2.0.0", description="Financial Intelligence Visualization Backend")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(market.router,    prefix="/api/market",     tags=["market"])
app.include_router(portfolio.router, prefix="/api/portfolio",  tags=["portfolio"])
app.include_router(regime.router,    prefix="/api/regime",     tags=["regime"])
app.include_router(trades.router,    prefix="/api/trades",     tags=["trades"])

@app.get("/")
async def root():
    return {"status": "online", "version": "2.0.0", "modules": ["market", "portfolio", "regime", "trades"]}