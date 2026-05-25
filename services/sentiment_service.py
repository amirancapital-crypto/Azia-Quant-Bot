#!/usr/bin/env python3
"""
Azia Quant Bot — Sentiment Service
Santiment + LunarCrush + Fear&Greed
"""

import logging
import requests
from typing import Optional, Dict, List

from config import (
    SANTIMENT_API_KEY, SANTIMENT_BASE,
    LUNARCRUSH_API_KEY, ALTERNATIVE_BASE
)
from database import cache_get, cache_set

logger = logging.getLogger(__name__)


class SentimentService:
    """Sentiment tahlil servisi"""

    def __init__(self):
        self.san_key = SANTIMENT_API_KEY
        self.lc_key  = LUNARCRUSH_API_KEY

    # ── Santiment ────────────────────────────────────────────────

    def _san_query(self, query: str) -> Optional[Dict]:
        """Santiment GraphQL so'rov"""
        try:
            if not self.san_key:
                return None
            resp = requests.post(
                SANTIMENT_BASE,
                json={"query": query},
                headers={
                    "Authorization": f"Apikey {self.san_key}",
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            if resp.status_code == 200:
                return resp.json().get("data")
        except Exception as e:
            logger.error(f"Santiment xato: {e}")
        return None

    def get_social_volume(self, ticker: str) -> Optional[Dict]:
        """Social media hajmi"""
        cache_key = f"social_vol_{ticker}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        slug_map = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana"}
        slug = slug_map.get(ticker.upper(), ticker.lower())

        query = f"""
        {{
            getMetric(metric: "social_volume_total") {{
                timeseriesData(
                    slug: "{slug}"
                    from: "utc_now-7d"
                    to: "utc_now"
                    interval: "1d"
                ) {{
                    datetime
                    value
                }}
            }}
        }}
        """
        data = self._san_query(query)
        if data:
            ts = data.get("getMetric", {}).get("timeseriesData", [])
            if ts:
                latest = ts[-1].get("value", 0)
                prev   = ts[-2].get("value", 0) if len(ts) > 1 else latest
                change = ((latest - prev) / prev * 100) if prev > 0 else 0
                result = {"volume": latest, "change": change}
                cache_set(cache_key, result, ttl=3600)
                return result
        return None

    def get_dev_activity(self, ticker: str) -> Optional[Dict]:
        """Developer faolligi"""
        cache_key = f"dev_activity_{ticker}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        slug_map = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana"}
        slug = slug_map.get(ticker.upper(), ticker.lower())

        query = f"""
        {{
            getMetric(metric: "dev_activity") {{
                timeseriesData(
                    slug: "{slug}"
                    from: "utc_now-30d"
                    to: "utc_now"
                    interval: "1w"
                ) {{
                    datetime
                    value
                }}
            }}
        }}
        """
        data = self._san_query(query)
        if data:
            ts = data.get("getMetric", {}).get("timeseriesData", [])
            if ts:
                latest = ts[-1].get("value", 0)
                result = {"activity": latest}
                cache_set(cache_key, result, ttl=3600)
                return result
        return None

    # ── LunarCrush ───────────────────────────────────────────────

    def get_lunarcrush(self, ticker: str) -> Optional[Dict]:
        """LunarCrush social tahlil"""
        cache_key = f"lunarcrush_{ticker}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            if not self.lc_key:
                return None
            resp = requests.get(
                f"https://lunarcrush.com/api4/public/coins/{ticker.lower()}/v1",
                headers={"Authorization": f"Bearer {self.lc_key}"},
                timeout=8
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                result = {
                    "galaxy_score":    data.get("galaxy_score"),
                    "alt_rank":        data.get("alt_rank"),
                    "social_score":    data.get("social_score"),
                    "sentiment":       data.get("sentiment"),
                    "social_volume":   data.get("social_volume"),
                }
                cache_set(cache_key, result, ttl=3600)
                return result
        except Exception as e:
            logger.error(f"LunarCrush xato: {e}")
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
                result = {
                    "value": int(d.get("value", 0)),
                    "label": d.get("value_classification", "")
                }
                cache_set("fear_greed", result, ttl=3600)
                return result
        except Exception as e:
            logger.error(f"Fear&Greed xato: {e}")
        return None

    # ── To'liq sentiment ─────────────────────────────────────────

    def get_sentiment_report(self, ticker: str) -> str:
        """To'liq sentiment hisobot"""
        fg     = self.get_fear_greed()
        social = self.get_social_volume(ticker)
        dev    = self.get_dev_activity(ticker)
        lc     = self.get_lunarcrush(ticker)

        txt = f"😊 <b>SENTIMENT TAHLIL — {ticker.upper()}</b>\n"
        txt += "━━━━━━━━━━━━━━━━━━━━\n\n"

        # Fear & Greed
        if fg:
            v = fg["value"]
            if v <= 25:
                fg_icon = "🟢 Kuchli qo'rquv (Xarid imkoniyati)"
            elif v <= 45:
                fg_icon = "🟡 Qo'rquv"
            elif v <= 55:
                fg_icon = "⚪ Neytral"
            elif v <= 75:
                fg_icon = "🟠 Ochko'zlik"
            else:
                fg_icon = "🔴 Kuchli ochko'zlik (Ehtiyot bo'ling)"
            txt += f"😱 <b>FEAR & GREED:</b>\n• {v}/100 — {fg_icon}\n\n"

        # Social Volume
        if social:
            vol    = social["volume"]
            change = social["change"]
            chg_icon = "📈" if change > 0 else "📉"
            txt += (
                f"📢 <b>SOCIAL VOLUME:</b>\n"
                f"• Hajm: {vol:,.0f} post\n"
                f"• O'zgarish (7k): {change:+.1f}% {chg_icon}\n\n"
            )

        # Developer
        if dev:
            act = dev["activity"]
            if act > 100:
                dev_icon = "🟢 Juda faol"
            elif act > 50:
                dev_icon = "🟡 Faol"
            elif act > 0:
                dev_icon = "🟠 Past faollik"
            else:
                dev_icon = "🔴 Faol emas"
            txt += f"👨‍💻 <b>DEVELOPER:</b>\n• Faollik: {act:.0f} — {dev_icon}\n\n"

        # LunarCrush
        if lc:
            gs = lc.get("galaxy_score")
            if gs:
                gs_icon = "🟢" if gs >= 60 else "🔴" if gs <= 40 else "🟡"
                txt += f"🌙 <b>LUNARCRUSH:</b>\n• Galaxy Score: {gs} {gs_icon}\n"
            sent = lc.get("sentiment")
            if sent:
                sent_icon = "🟢" if sent >= 3 else "🔴" if sent <= 2 else "🟡"
                txt += f"• Kayfiyat: {sent}/5 {sent_icon}\n"
            txt += "\n"

        if not any([fg, social, dev, lc]):
            txt += "• Sentiment API ulanganda ma'lumot chiqadi ⏳\n\n"

        txt += (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ Bu ma'lumot faqat tahlil uchun."
        )

        return txt


# Global instance
sentiment_service = SentimentService()
