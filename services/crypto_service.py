#!/usr/bin/env python3
"""
Azia Quant Bot — Crypto Service
CoinGecko / CoinMarketCap orqali crypto ma'lumotlari
"""

import os
import logging
import requests
from typing import Optional, Dict, Any

from config import (
    COINGECKO_API_KEY, COINMARKETCAP_API_KEY,
    COINGECKO_BASE, COINMARKETCAP_BASE,
    CRYPTO_TICKER_MAP, ALTERNATIVE_BASE
)
from database import cache_get, cache_set

logger = logging.getLogger(__name__)


class CryptoService:
    """Crypto ma'lumotlari servisi"""

    def __init__(self):
        self.cg_key  = COINGECKO_API_KEY
        self.cmc_key = COINMARKETCAP_API_KEY

    # ── Ichki yordamchi ──────────────────────────────────────────

    def _cg_get(self, endpoint: str, params: dict = {}) -> Optional[Any]:
        """CoinGecko API dan ma'lumot olish"""
        try:
            headers = {}
            if self.cg_key:
                headers["x-cg-pro-api-key"] = self.cg_key
            resp = requests.get(
                f"{COINGECKO_BASE}/{endpoint}",
                params=params,
                headers=headers,
                timeout=10
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"CoinGecko xato: {e}")
        return None

    def _cmc_get(self, endpoint: str, params: dict = {}) -> Optional[Any]:
        """CoinMarketCap API dan ma'lumot olish"""
        try:
            if not self.cmc_key:
                return None
            headers = {"X-CMC_PRO_API_KEY": self.cmc_key}
            resp = requests.get(
                f"{COINMARKETCAP_BASE}/{endpoint}",
                params=params,
                headers=headers,
                timeout=10
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"CoinMarketCap xato: {e}")
        return None

    # ── Coin ID ──────────────────────────────────────────────────

    def get_coin_id(self, ticker: str) -> Optional[str]:
        """Ticker → CoinGecko ID"""
        return CRYPTO_TICKER_MAP.get(ticker.upper())

    # ── Narx ────────────────────────────────────────────────────

    def get_price(self, ticker: str) -> Optional[float]:
        """Real-time narx"""
        cache_key = f"price_crypto_{ticker}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        coin_id = self.get_coin_id(ticker)
        if not coin_id:
            return None

        data = self._cg_get("simple/price", {
            "ids": coin_id,
            "vs_currencies": "usd",
            "include_24hr_change": "true"
        })
        if data and coin_id in data:
            price = data[coin_id].get("usd")
            cache_set(cache_key, price, ttl=60)
            return price
        return None

    # ── To'liq ma'lumot ─────────────────────────────────────────

    def get_coin_data(self, ticker: str) -> Optional[Dict]:
        """Coin haqida to'liq ma'lumot"""
        cache_key = f"coindata_{ticker}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        coin_id = self.get_coin_id(ticker)
        if not coin_id:
            return None

        data = self._cg_get(f"coins/{coin_id}", {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "true",
            "developer_data": "true"
        })
        if data:
            cache_set(cache_key, data, ttl=300)
        return data

    # ── Screener natijasi ────────────────────────────────────────

    def get_screener_result(self, ticker: str, is_free: bool = False) -> Optional[str]:
        """Crypto screener natijasi"""
        try:
            data = self.get_coin_data(ticker)
            if not data:
                return None

            name     = data.get("name", ticker)
            symbol   = data.get("symbol", "").upper()
            market   = data.get("market_data", {})
            dev      = data.get("developer_data", {})
            comm     = data.get("community_data", {})
            desc     = data.get("description", {}).get("en", "")[:200]

            price     = market.get("current_price", {}).get("usd", 0)
            change_1h = market.get("price_change_percentage_1h_in_currency", {}).get("usd", 0) or 0
            change_24 = market.get("price_change_percentage_24h") or 0
            change_7d = market.get("price_change_percentage_7d") or 0
            mkt_cap   = market.get("market_cap", {}).get("usd", 0)
            volume    = market.get("total_volume", {}).get("usd", 0)
            high_24   = market.get("high_24h", {}).get("usd", 0)
            low_24    = market.get("low_24h", {}).get("usd", 0)
            ath       = market.get("ath", {}).get("usd", 0)
            atl       = market.get("atl", {}).get("usd", 0)
            ath_pct   = market.get("ath_change_percentage", {}).get("usd", 0) or 0
            circ      = market.get("circulating_supply") or 0
            total_s   = market.get("total_supply") or 0
            rank      = data.get("market_cap_rank") or 0

            # RSI hisoblash (taxminiy)
            rsi = self._calc_rsi(ticker)

            def fmt_big(n):
                if not n: return "N/A"
                if n >= 1e12: return f"${n/1e12:.2f}T"
                if n >= 1e9:  return f"${n/1e9:.2f}B"
                if n >= 1e6:  return f"${n/1e6:.2f}M"
                return f"${n:,.0f}"

            def chg_icon(v):
                return "📈" if v >= 0 else "📉"

            def chg_fmt(v):
                return f"+{v:.2f}%" if v >= 0 else f"{v:.2f}%"

            # Bepul versiya
            if is_free:
                txt = (
                    f"🔍 <b>{symbol} — {name}</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"💰 <b>NARX:</b>\n"
                    f"• Narx: ${price:,.4f}\n"
                    f"• 24s: {chg_icon(change_24)} {chg_fmt(change_24)}\n"
                    f"• 7k: {chg_icon(change_7d)} {chg_fmt(change_7d)}\n\n"
                    f"📊 <b>BOZOR:</b>\n"
                    f"• Market Cap: {fmt_big(mkt_cap)}\n"
                    f"• Rank: #{rank}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"💎 To'liq tahlil uchun obuna oling!"
                )
                return txt

            # To'liq versiya
            staking = market.get("staking_apy") or 0
            commits = dev.get("commit_count_4_weeks") or 0
            stars   = dev.get("stars") or 0
            forks   = dev.get("forks") or 0

            # Fear & Greed
            fg = self.get_fear_greed()
            fg_txt = f"{fg['value']}/100 — {fg['label']}" if fg else "N/A"

            rsi_txt = "N/A"
            rsi_icon = ""
            if rsi:
                if rsi >= 70:
                    rsi_icon = "🔴 Overbought"
                elif rsi <= 30:
                    rsi_icon = "🟢 Oversold"
                else:
                    rsi_icon = "⚪ Neytral"
                rsi_txt = f"{rsi:.1f} — {rsi_icon}"

            txt = (
                f"🔍 <b>{symbol} — {name}</b>\n"
                f"📍 Rank #{rank}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 <b>NARX:</b>\n"
                f"• Narx: ${price:,.4f}\n"
                f"• 1s: {chg_icon(change_1h)} {chg_fmt(change_1h)}\n"
                f"• 24s: {chg_icon(change_24)} {chg_fmt(change_24)}\n"
                f"• 7k: {chg_icon(change_7d)} {chg_fmt(change_7d)}\n"
                f"• 24s High: ${high_24:,.4f}\n"
                f"• 24s Low: ${low_24:,.4f}\n\n"
                f"📊 <b>BOZOR:</b>\n"
                f"• Market Cap: {fmt_big(mkt_cap)}\n"
                f"• Hajm (24s): {fmt_big(volume)}\n"
                f"• Muomaladagi: {circ:,.0f}\n"
                f"• Jami taklif: {total_s:,.0f}\n\n"
                f"📈 <b>ATH/ATL:</b>\n"
                f"• ATH: ${ath:,.4f} ({ath_pct:.1f}%)\n"
                f"• ATL: ${atl:,.4f}\n\n"
                f"📉 <b>TEXNIK:</b>\n"
                f"• RSI (14): {rsi_txt}\n\n"
                f"😱 <b>FEAR & GREED:</b>\n"
                f"• {fg_txt}\n\n"
                f"👨‍💻 <b>DEVELOPER:</b>\n"
                f"• Commitlar (4 hafta): {commits}\n"
                f"• GitHub Stars: {stars:,}\n"
                f"• Forks: {forks:,}\n\n"
            )

            if staking:
                txt += f"💸 <b>STAKING APY:</b> {staking:.2f}%\n\n"

            txt += (
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚠️ Bu ma'lumot faqat tahlil uchun.\n"
                f"Investitsiya qarori faqat sizga bog'liq."
            )

            return txt

        except Exception as e:
            logger.error(f"Crypto screener xato [{ticker}]: {e}")
            return None

    # ── RSI hisoblash ────────────────────────────────────────────

    def _calc_rsi(self, ticker: str, period: int = 14) -> Optional[float]:
        """RSI taxminiy hisoblash (OHLCV dan)"""
        try:
            cache_key = f"rsi_{ticker}"
            cached = cache_get(cache_key)
            if cached is not None:
                return cached

            coin_id = self.get_coin_id(ticker)
            if not coin_id:
                return None

            data = self._cg_get(f"coins/{coin_id}/market_chart", {
                "vs_currency": "usd",
                "days": "30",
                "interval": "daily"
            })
            if not data or "prices" not in data:
                return None

            prices = [p[1] for p in data["prices"]]
            if len(prices) < period + 1:
                return None

            deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            gains = [d if d > 0 else 0 for d in deltas[-period:]]
            losses = [-d if d < 0 else 0 for d in deltas[-period:]]

            avg_gain = sum(gains) / period
            avg_loss = sum(losses) / period

            if avg_loss == 0:
                return 100.0

            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            cache_set(cache_key, rsi, ttl=600)
            return rsi

        except Exception as e:
            logger.error(f"RSI xato: {e}")
            return None

    # ── Fear & Greed ─────────────────────────────────────────────

    def get_fear_greed(self) -> Optional[Dict]:
        """Fear & Greed Index"""
        cached = cache_get("fear_greed")
        if cached is not None:
            return cached

        try:
            resp = requests.get(f"{ALTERNATIVE_BASE}/fng/", timeout=8)
            if resp.status_code == 200:
                d = resp.json().get("data", [{}])[0]
                value = int(d.get("value", 0))
                label = d.get("value_classification", "")
                result = {"value": value, "label": label}
                cache_set("fear_greed", result, ttl=3600)
                return result
        except Exception as e:
            logger.error(f"Fear&Greed xato: {e}")
        return None

    # ── Top coins ────────────────────────────────────────────────

    def get_top_coins(self, limit: int = 10) -> Optional[list]:
        """Top N coin"""
        cached = cache_get(f"top_coins_{limit}")
        if cached is not None:
            return cached

        data = self._cg_get("coins/markets", {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": limit,
            "page": 1
        })
        if data:
            cache_set(f"top_coins_{limit}", data, ttl=300)
        return data

    # ── Yangiliklar ─────────────────────────────────────────────

    def get_crypto_news(self, ticker: str = "", limit: int = 5) -> list:
        """CryptoPanic dan yangiliklar"""
        from config import CRYPTOPANIC_API_KEY, CRYPTOPANIC_BASE
        cached = cache_get(f"news_{ticker}")
        if cached is not None:
            return cached

        try:
            params = {"auth_token": CRYPTOPANIC_API_KEY, "public": "true"}
            if ticker:
                params["currencies"] = ticker.upper()
            resp = requests.get(f"{CRYPTOPANIC_BASE}/posts/", params=params, timeout=8)
            if resp.status_code == 200:
                results = resp.json().get("results", [])[:limit]
                news = [{"title": r.get("title", ""), "url": r.get("url", ""),
                         "source": r.get("source", {}).get("title", "")} for r in results]
                cache_set(f"news_{ticker}", news, ttl=600)
                return news
        except Exception as e:
            logger.error(f"CryptoPanic xato: {e}")
        return []


# Global instance
crypto_service = CryptoService()
