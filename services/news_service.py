#!/usr/bin/env python3
"""
Azia Quant Bot — News Service
CryptoPanic + Finnhub + RSS
"""

import logging
import requests
import feedparser
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

from config import CRYPTOPANIC_API_KEY, CRYPTOPANIC_BASE, FINNHUB_API_KEY, FINNHUB_BASE
from database import cache_get, cache_set

logger = logging.getLogger(__name__)


class NewsService:
    """Yangiliklar servisi"""

    # ── CryptoPanic ──────────────────────────────────────────────

    def get_crypto_news(self, ticker: str = "", limit: int = 5) -> List[Dict]:
        """CryptoPanic dan crypto yangiliklari"""
        cache_key = f"cryptopanic_{ticker}_{limit}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            if not CRYPTOPANIC_API_KEY:
                return self._get_rss_news(ticker, limit)

            params = {"auth_token": CRYPTOPANIC_API_KEY, "public": "true"}
            if ticker:
                params["currencies"] = ticker.upper()

            resp = requests.get(f"{CRYPTOPANIC_BASE}/posts/", params=params, timeout=8)
            if resp.status_code == 200:
                results = resp.json().get("results", [])[:limit]
                news = []
                for r in results:
                    news.append({
                        "title":  r.get("title", "")[:80],
                        "url":    r.get("url", ""),
                        "source": r.get("source", {}).get("title", ""),
                        "votes":  r.get("votes", {})
                    })
                cache_set(cache_key, news, ttl=600)
                return news
        except Exception as e:
            logger.error(f"CryptoPanic xato: {e}")

        return self._get_rss_news(ticker, limit)

    # ── Finnhub yangiliklar ──────────────────────────────────────

    def get_stock_news(self, ticker: str, days: int = 7) -> List[Dict]:
        """Finnhub dan aksiya yangiliklari"""
        cache_key = f"stock_news_{ticker}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            if not FINNHUB_API_KEY:
                return []

            date_to   = datetime.now().strftime("%Y-%m-%d")
            date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            resp = requests.get(
                f"{FINNHUB_BASE}/company-news",
                params={
                    "symbol": ticker.upper(),
                    "from": date_from,
                    "to": date_to,
                    "token": FINNHUB_API_KEY
                },
                timeout=8
            )
            if resp.status_code == 200:
                results = resp.json()[:5]
                news = [{"title": r.get("headline", "")[:80],
                         "url":   r.get("url", ""),
                         "source": r.get("source", "")} for r in results]
                cache_set(cache_key, news, ttl=600)
                return news
        except Exception as e:
            logger.error(f"Finnhub yangilik xato: {e}")
        return []

    # ── RSS fallback ─────────────────────────────────────────────

    def _get_rss_news(self, query: str = "", limit: int = 5) -> List[Dict]:
        """RSS dan yangiliklar (fallback)"""
        feeds = [
            "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "https://cointelegraph.com/rss",
        ]
        news = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

        for url in feeds:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:10]:
                    title = (entry.get("title") or "").strip()
                    link  = entry.get("link") or ""

                    # Vaqt tekshirish
                    published = entry.get("published_parsed")
                    if published:
                        pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                        if pub_dt < cutoff:
                            continue

                    if query and query.upper() not in title.upper():
                        continue

                    if title and link:
                        news.append({
                            "title":  title[:80],
                            "url":    link,
                            "source": feed.feed.get("title", "")
                        })

                    if len(news) >= limit:
                        break
            except Exception as e:
                logger.error(f"RSS xato [{url}]: {e}")

            if len(news) >= limit:
                break

        return news

    # ── Bozor yangiliklari ───────────────────────────────────────

    def get_market_news(self, limit: int = 5) -> List[Dict]:
        """Umumiy bozor yangiliklari"""
        return self.get_crypto_news("", limit)

    # ── Kanal uchun post ─────────────────────────────────────────

    def format_for_channel(self, news: List[Dict], ticker: str = "") -> str:
        """Kanalga post formatlash"""
        if not news:
            return ""

        title = f"📰 <b>{ticker} YANGILIKLARI</b>" if ticker else "📰 <b>BOZOR YANGILIKLARI</b>"
        txt = f"{title}\n━━━━━━━━━━━━━━━━━━━━\n\n"

        for n in news[:3]:
            txt += f"• <a href='{n['url']}'>{n['title']}</a>\n"
            if n.get("source"):
                txt += f"  📰 {n['source']}\n"
            txt += "\n"

        txt += "━━━━━━━━━━━━━━━━━━━━\n"
        txt += "📊 @azia_quant_bot orqali tahlil qiling"
        return txt


# Global instance
news_service = NewsService()
