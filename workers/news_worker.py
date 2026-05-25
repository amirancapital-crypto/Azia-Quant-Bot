#!/usr/bin/env python3
"""
Azia Quant Bot — News Worker
Portfel yangiliklari kuzatuv
"""

import logging
from datetime import datetime, timezone, timedelta
from telegram.ext import ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from database import (
    get_all_users, get_portfolio,
    check_channel_access, check_screener_access, check_premium_access
)
from services.news_service import news_service

logger = logging.getLogger(__name__)

# Yuborilgan yangiliklar (xotira)
_sent_news: set = set()


async def check_portfolio_news(context: ContextTypes.DEFAULT_TYPE):
    """Har 30 daqiqada portfel yangiliklar tekshirish"""
    try:
        global _sent_news

        users = await get_all_users()
        if not users:
            return

        # Eski yuborilganlar tozalash (24 soatdan eski)
        if len(_sent_news) > 2000:
            _sent_news.clear()

        for u in users:
            uid = u.get("user_id")
            if not uid:
                continue

            # Faqat pullik obunchilar
            has_sub = (
                await check_channel_access(uid, "signals") or
                await check_screener_access(uid) or
                await check_premium_access(uid)
            )
            if not has_sub:
                continue

            # Portfelni olish
            portfolio = await get_portfolio(uid)
            if not portfolio:
                continue

            # Har aktiv uchun yangilik tekshirish
            for item in portfolio:
                ticker = item.get("ticker", "").upper()
                ticker_type = item.get("ticker_type", "crypto")
                await _check_ticker_news(context, uid, ticker, ticker_type)

    except Exception as e:
        logger.error(f"[NewsWorker] Xato: {e}")


async def _check_ticker_news(context, uid: int, ticker: str, ticker_type: str):
    """Bitta ticker uchun yangilik tekshirish"""
    try:
        # Yangiliklar olish
        if ticker_type == "crypto":
            news_list = news_service.get_crypto_news(ticker, limit=5)
        else:
            news_list = news_service.get_stock_news(ticker, days=1)

        if not news_list:
            return

        # Salbiy kalit so'zlar
        negative_words = [
            "crash", "fall", "drop", "decline", "down", "loss",
            "hack", "breach", "ban", "lawsuit", "fraud", "bankrupt",
            "warning", "risk", "collapse", "suspend", "halt", "plunge",
            "sell-off", "dump", "fear", "panic"
        ]

        for news in news_list:
            title_lower = news["title"].lower()

            # Salbiy yangilikmi?
            is_negative = any(w in title_lower for w in negative_words)
            if not is_negative:
                continue

            # Ticker bor?
            if ticker.upper() not in news["title"].upper():
                continue

            # Qayta yuborilmasin
            news_key = f"{uid}_{news['url']}"
            if news_key in _sent_news:
                continue

            # Yuborish
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text=(
                        f"🚨 <b>PORTFEL OGOHLANTIRISHI!</b>\n\n"
                        f"📌 Aktiv: <b>{ticker}</b>\n\n"
                        f"⚠️ Salbiy yangilik:\n"
                        f"<a href='{news['url']}'>{news['title'][:100]}</a>\n\n"
                        f"💡 Portfelingizni tekshiring!"
                    ),
                    parse_mode="HTML",
                    disable_web_page_preview=False,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "💼 Portfelni ko'rish",
                            callback_data="my_portfolio"
                        )
                    ]])
                )
                _sent_news.add(news_key)
                logger.info(f"[NewsWorker] {ticker} yangilik → {uid}")
            except Exception as e:
                logger.error(f"[NewsWorker] Yuborish xato: {e}")

    except Exception as e:
        logger.error(f"[NewsWorker] {ticker} xato: {e}")
