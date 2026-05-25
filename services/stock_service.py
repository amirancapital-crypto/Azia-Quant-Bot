#!/usr/bin/env python3
"""
Azia Quant Bot — Stock Service
Finnhub + Polygon.io + yfinance orqali aksiya ma'lumotlari
"""

import os
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from config import (
    FINNHUB_API_KEY, POLYGON_API_KEY,
    FINNHUB_BASE, POLYGON_BASE
)
from database import cache_get, cache_set

logger = logging.getLogger(__name__)


class StockService:
    """Aksiya ma'lumotlari servisi"""

    def __init__(self):
        self.fh_key  = FINNHUB_API_KEY
        self.poly_key = POLYGON_API_KEY

    # ── Ichki yordamchi ──────────────────────────────────────────

    def _fh_get(self, endpoint: str, params: dict = {}) -> Optional[Dict]:
        """Finnhub API dan ma'lumot olish"""
        try:
            if not self.fh_key:
                return None
            params["token"] = self.fh_key
            resp = requests.get(f"{FINNHUB_BASE}/{endpoint}", params=params, timeout=8)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"Finnhub xato: {e}")
        return None

    def _yf_get(self, ticker: str) -> Optional[Dict]:
        """yfinance dan ma'lumot olish (fallback)"""
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            return stock.info
        except Exception as e:
            logger.error(f"yfinance xato: {e}")
        return None

    # ── Narx ────────────────────────────────────────────────────

    def get_quote(self, ticker: str) -> Optional[Dict]:
        """Real-time narx"""
        cache_key = f"quote_{ticker}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        # Finnhub dan
        data = self._fh_get("quote", {"symbol": ticker.upper()})
        if data and data.get("c"):
            result = {
                "price":   data["c"],
                "change":  data.get("d", 0),
                "pct":     data.get("dp", 0),
                "high":    data.get("h", 0),
                "low":     data.get("l", 0),
                "open":    data.get("o", 0),
                "prev":    data.get("pc", 0),
            }
            cache_set(cache_key, result, ttl=60)
            return result
        return None

    # ── Fundamental ─────────────────────────────────────────────

    def get_profile(self, ticker: str) -> Optional[Dict]:
        """Kompaniya profili"""
        cache_key = f"profile_{ticker}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        data = self._fh_get("stock/profile2", {"symbol": ticker.upper()})
        if data and data.get("name"):
            cache_set(cache_key, data, ttl=3600)
            return data
        return None

    def get_metrics(self, ticker: str) -> Optional[Dict]:
        """Fundamental ko'rsatkichlar"""
        cache_key = f"metrics_{ticker}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        data = self._fh_get("stock/metric", {
            "symbol": ticker.upper(),
            "metric": "all"
        })
        if data and data.get("metric"):
            cache_set(cache_key, data["metric"], ttl=3600)
            return data["metric"]
        return None

    # ── Insider ─────────────────────────────────────────────────

    def get_insider(self, ticker: str) -> List[Dict]:
        """Insider tranzaksiyalar"""
        cache_key = f"insider_{ticker}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        data = self._fh_get("stock/insider-transactions", {"symbol": ticker.upper()})
        if data and data.get("data"):
            result = data["data"][:5]
            cache_set(cache_key, result, ttl=3600)
            return result
        return []

    # ── Earnings ────────────────────────────────────────────────

    def get_earnings(self, ticker: str) -> List[Dict]:
        """Choraklik hisobotlar"""
        cache_key = f"earnings_{ticker}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        data = self._fh_get("stock/earnings", {
            "symbol": ticker.upper(),
            "limit": 4
        })
        if data:
            cache_set(cache_key, data, ttl=3600)
            return data
        return []

    # ── Analyst ─────────────────────────────────────────────────

    def get_recommendation(self, ticker: str) -> Optional[Dict]:
        """Analyst reytingi"""
        cache_key = f"rec_{ticker}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        data = self._fh_get("stock/recommendation", {"symbol": ticker.upper()})
        if data and len(data) > 0:
            cache_set(cache_key, data[0], ttl=3600)
            return data[0]
        return None

    # ── Yangiliklar ─────────────────────────────────────────────

    def get_news(self, ticker: str, days: int = 7) -> List[Dict]:
        """So'nggi yangiliklar"""
        cache_key = f"news_{ticker}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        date_to   = datetime.now().strftime("%Y-%m-%d")
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        data = self._fh_get("company-news", {
            "symbol": ticker.upper(),
            "from": date_from,
            "to": date_to
        })
        if data:
            news = [{"title": n.get("headline", "")[:70],
                     "url": n.get("url", ""),
                     "source": n.get("source", "")} for n in data[:3]]
            cache_set(cache_key, news, ttl=600)
            return news
        return []

    # ── Texnik ──────────────────────────────────────────────────

    def _calc_rsi_yf(self, ticker: str) -> Optional[float]:
        """RSI yfinance dan"""
        try:
            import yfinance as yf
            import pandas as pd
            stock = yf.Ticker(ticker)
            hist = stock.history(period="3mo", interval="1d")
            if hist is None or hist.empty:
                return None
            closes = hist["Close"].values
            period = 14
            if len(closes) < period + 1:
                return None
            deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
            gains  = [d if d > 0 else 0 for d in deltas[-period:]]
            losses = [-d if d < 0 else 0 for d in deltas[-period:]]
            avg_gain = sum(gains) / period
            avg_loss = sum(losses) / period
            if avg_loss == 0:
                return 100.0
            rs = avg_gain / avg_loss
            return 100 - (100 / (1 + rs))
        except:
            return None

    # ── Screener natijasi ────────────────────────────────────────

    def get_screener_result(self, ticker: str, is_free: bool = False) -> Optional[str]:
        """Aksiya screener natijasi"""
        try:
            ticker = ticker.upper()

            # Narx
            quote = self.get_quote(ticker)
            if not quote:
                # yfinance fallback
                info = self._yf_get(ticker)
                if not info:
                    return None
                price  = info.get("regularMarketPrice") or info.get("currentPrice") or 0
                pct    = info.get("regularMarketChangePercent") or 0
                name   = info.get("longName") or info.get("shortName") or ticker
                sector = info.get("sector") or "N/A"
                exchange = info.get("exchange") or ""
            else:
                price  = quote["price"]
                pct    = quote["pct"]
                info   = self._yf_get(ticker) or {}
                name   = info.get("longName") or info.get("shortName") or ticker
                sector = info.get("sector") or "N/A"
                exchange = info.get("exchange") or ""

            chg_icon = "📈" if pct >= 0 else "📉"
            chg_sign = "+" if pct >= 0 else ""

            # Bepul versiya
            if is_free:
                return (
                    f"🔎 <b>{ticker} — {name}</b>\n"
                    f"📍 {sector}\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"💰 <b>ASOSIY:</b>\n"
                    f"• Narx: ${price:,.2f} ({chg_sign}{pct:.2f}% {chg_icon})\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"💎 To'liq tahlil uchun obuna oling!"
                )

            # To'liq versiya
            metrics = self.get_metrics(ticker) or {}
            profile = self.get_profile(ticker) or {}
            insider = self.get_insider(ticker)
            earnings = self.get_earnings(ticker)
            rec = self.get_recommendation(ticker) or {}
            news = self.get_news(ticker)

            # Fundamental
            pe       = metrics.get("peBasicExclExtraTTM") or info.get("trailingPE") or 0
            pb       = metrics.get("pbAnnual") or info.get("priceToBook") or 0
            eps      = metrics.get("epsBasicExclExtraAnnual") or info.get("trailingEps") or 0
            mkt_cap  = info.get("marketCap") or 0
            revenue  = info.get("totalRevenue") or 0
            net_inc  = info.get("netIncomeToCommon") or 0
            roe      = info.get("returnOnEquity") or 0
            fcf      = info.get("freeCashflow") or 0
            div      = info.get("dividendRate") or 0
            div_y    = info.get("dividendYield") or 0
            if div_y and div_y > 0.5:
                div_y = div_y / 100

            # 52 hafta
            w52_h = info.get("fiftyTwoWeekHigh") or 0
            w52_l = info.get("fiftyTwoWeekLow") or 0
            w52_pos = ((price - w52_l) / (w52_h - w52_l) * 100) if (w52_h - w52_l) > 0 else 0

            # Texnik
            ma50  = info.get("fiftyDayAverage") or 0
            ma200 = info.get("twoHundredDayAverage") or 0
            beta  = info.get("beta") or 0
            short = info.get("shortPercentOfFloat") or 0
            rsi   = self._calc_rsi_yf(ticker)

            def fmt_big(n):
                if not n: return "N/A"
                if n >= 1e12: return f"${n/1e12:.2f}T"
                if n >= 1e9:  return f"${n/1e9:.2f}B"
                if n >= 1e6:  return f"${n/1e6:.2f}M"
                return f"${n:,.0f}"

            # RSI
            if rsi:
                if rsi >= 70: rsi_txt = f"{rsi:.1f} — Overbought 🔴"
                elif rsi <= 30: rsi_txt = f"{rsi:.1f} — Oversold 🟢"
                else: rsi_txt = f"{rsi:.1f} — Neytral ⚪"
            else:
                rsi_txt = "N/A"

            # Analyst
            rec_map = {
                "strongBuy": "KUCHLI SOTIB OL ✅✅",
                "buy": "SOTIB OL ✅",
                "hold": "USHLAB TUR ⚪",
                "sell": "SOT ❌",
                "strongSell": "KUCHLI SOT ❌❌"
            }
            buy = rec.get("buy", 0) + rec.get("strongBuy", 0)
            sell = rec.get("sell", 0) + rec.get("strongSell", 0)
            hold = rec.get("hold", 0)
            total_rec = buy + sell + hold
            if buy > sell and buy > hold:
                rec_txt = "SOTIB OL ✅"
            elif sell > buy and sell > hold:
                rec_txt = "SOT ❌"
            else:
                rec_txt = "USHLAB TUR ⚪"

            txt = (
                f"🔎 <b>{ticker} — {name}</b>\n"
                f"📍 {sector} | {exchange}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 <b>ASOSIY:</b>\n"
                f"• Narx: ${price:,.2f} ({chg_sign}{pct:.2f}% {chg_icon})\n"
                f"• Bozor kap: {fmt_big(mkt_cap)}\n"
                f"• 52 hafta: ${w52_l:,.2f} — ${w52_h:,.2f}\n"
                f"• 52 hafta pozitsiyasi: {w52_pos:.0f}% (pastdan)\n\n"
                f"📊 <b>FUNDAMENTAL:</b>\n"
                f"• P/E: {pe:.1f}\n" if pe else ""
                f"• P/B: {pb:.1f}\n" if pb else ""
                f"• EPS: ${eps:.2f}\n" if eps else ""
                f"• Daromad: {fmt_big(revenue)}\n"
                f"• Sof foyda: {fmt_big(net_inc)}\n"
                f"• ROE: {roe*100:.1f}%\n" if roe else ""
                f"• FCF: {fmt_big(fcf)}\n"
                f"• Dividend: ${div:.2f} ({div_y*100:.2f}%)\n\n"
                f"📈 <b>TEXNIK:</b>\n"
                f"• RSI (14): {rsi_txt}\n"
                f"• MA50: ${ma50:,.2f} {'✅' if price > ma50 else '❌'}\n" if ma50 else ""
                f"• MA200: ${ma200:,.2f} {'✅' if price > ma200 else '❌'}\n" if ma200 else ""
                f"• Beta: {beta:.2f}\n" if beta else ""
                f"• Short: {short*100:.1f}%\n\n" if short else "\n"
            )

            # Analyst
            if total_rec > 0:
                txt += (
                    f"🏦 <b>ANALYST:</b>\n"
                    f"• Xulosa: {rec_txt}\n"
                    f"• Analitiklar: {total_rec} ta\n\n"
                )

            # Insider
            if insider:
                txt += "👤 <b>INSIDER:</b>\n"
                for ins in insider[:3]:
                    iname = (ins.get("name") or "")[:25]
                    ishares = float(ins.get("share") or 0)
                    idate = str(ins.get("transactionDate") or "")[:10]
                    itype = ins.get("transactionCode") or ""
                    icon = "SOTDI ⚠️" if itype in ["S", "D"] else "OLDI ✅"
                    txt += f"• {iname}: {abs(ishares):,.0f} {icon} | {idate}\n"
                txt += "\n"

            # Earnings
            if earnings:
                txt += "📋 <b>CHORAKLIK:</b>\n"
                for e in earnings[:4]:
                    period = e.get("period") or ""
                    actual = e.get("actual") or 0
                    est    = e.get("estimate") or 0
                    surp   = ((actual - est) / abs(est) * 100) if est else 0
                    icon   = "✅" if surp >= 0 else "❌"
                    txt += f"• {period}: ${actual:.2f} (kut. ${est:.2f}) {surp:+.1f}% {icon}\n"
                txt += "\n"

            # Yangiliklar
            if news:
                txt += "📰 <b>YANGILIKLAR:</b>\n"
                for n in news:
                    txt += f"• <a href='{n['url']}'>{n['title']}</a>\n"
                    if n["source"]:
                        txt += f"  📰 {n['source']}\n"
                txt += "\n"

            txt += (
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚠️ Bu ma'lumot faqat tahlil uchun.\n"
                f"Investitsiya qarori faqat sizga bog'liq."
            )

            return txt

        except Exception as e:
            logger.error(f"Stock screener xato [{ticker}]: {e}")
            return None


# Global instance
stock_service = StockService()
