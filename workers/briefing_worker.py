#!/usr/bin/env python3
"""
Azia Quant Bot — Briefing Worker
Har kuni 08:00 da kunlik brifing yuborish
"""

import logging
from typing import Optional
from telegram.ext import ContextTypes

from database import get_all_users, check_channel_access, check_screener_access, check_premium_access
from services.crypto_service import crypto_service
from services.onchain_service import onchain_service
from services.news_service import news_service
from services.ai_service import ai_service
from config import CHANNEL_IDS

logger = logging.getLogger(__name__)


async def send_daily_briefing(context: ContextTypes.DEFAULT_TYPE):
    """Har kuni 08:00 da ishlaydigan worker"""
    try:
        logger.info("[Worker] Kunlik brifing tayyorlanmoqda...")

        # Bozor ma'lumotlari yig'ish
        btc_data = crypto_service.get_coin_data("BTC")
        eth_data = crypto_service.get_coin_data("ETH")
        fg       = onchain_service.get_fear_greed()
        top_news = news_service.get_market_news(limit=5)

        # Ma'lumotlarni birlashtirish
        market_txt = _build_market_summary(btc_data, eth_data, fg, top_news)

        # AI tahlil
        ai_briefing = ai_service.generate_daily_briefing(market_txt)

        if not ai_briefing:
            # AI yo'q bo'lsa oddiy format
            ai_briefing = _build_simple_briefing(btc_data, eth_data, fg)

        # 1. Kanalga yuborish
        public_channel = CHANNEL_IDS.get("public")
        if public_channel:
            try:
                await context.bot.send_message(
                    chat_id=public_channel,
                    text=ai_briefing,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
                logger.info("[Worker] Brifing kanalga yuborildi")
            except Exception as e:
                logger.error(f"[Worker] Kanal xato: {e}")

        # 2. Premium obunchilarga yuborish
        await _send_to_premium_users(context, ai_briefing)

        logger.info("[Worker] Kunlik brifing tugadi")

    except Exception as e:
        logger.error(f"[Worker] Brifing xato: {e}")


def _build_market_summary(btc_data, eth_data, fg, news) -> str:
    """AI uchun bozor xulasasi"""
    txt = ""

    if btc_data:
        m = btc_data.get("market_data", {})
        btc_price  = m.get("current_price", {}).get("usd", 0)
        btc_change = m.get("price_change_percentage_24h", 0)
        txt += f"BTC: ${btc_price:,.0f} ({btc_change:+.1f}%)\n"

    if eth_data:
        m = eth_data.get("market_data", {})
        eth_price  = m.get("current_price", {}).get("usd", 0)
        eth_change = m.get("price_change_percentage_24h", 0)
        txt += f"ETH: ${eth_price:,.0f} ({eth_change:+.1f}%)\n"

    if fg:
        txt += f"Fear & Greed: {fg['value']}/100 ({fg['label']})\n"

    if news:
        txt += "\nSo'nggi yangiliklar:\n"
        for n in news[:3]:
            txt += f"- {n['title']}\n"

    return txt


def _build_simple_briefing(btc_data, eth_data, fg) -> str:
    """AI yo'q bo'lganda oddiy brifing"""
    lines = ["☀️ <b>KUNLIK BRIFING</b>\n━━━━━━━━━━━━━━━━━━━━\n"]

    if btc_data:
        m = btc_data.get("market_data", {})
        price  = m.get("current_price", {}).get("usd", 0)
        change = m.get("price_change_percentage_24h", 0)
        icon   = "📈" if change >= 0 else "📉"
        lines.append(f"₿ <b>BTC:</b> ${price:,.0f} {icon} {change:+.1f}%")

    if eth_data:
        m = eth_data.get("market_data", {})
        price  = m.get("current_price", {}).get("usd", 0)
        change = m.get("price_change_percentage_24h", 0)
        icon   = "📈" if change >= 0 else "📉"
        lines.append(f"Ξ <b>ETH:</b> ${price:,.0f} {icon} {change:+.1f}%")

    if fg:
        v = fg["value"]
        fg_icon = "🟢" if v <= 30 else "🔴" if v >= 70 else "🟡"
        lines.append(f"😱 <b>Fear & Greed:</b> {v}/100 {fg_icon}")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━")
    lines.append("📊 Batafsil tahlil: @azia_quant_bot")

    return "\n".join(lines)


async def _send_to_premium_users(context, message: str):
    """Premium obunchilarga yuborish"""
    try:
        users = await get_all_users()
        sent = 0
        for u in users:
            uid = u.get("user_id")
            if not uid:
                continue
            has_sub = (
                await check_channel_access(uid, "signals") or
                await check_screener_access(uid) or
                await check_premium_access(uid)
            )
            if not has_sub:
                continue
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text=message,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
                sent += 1
            except Exception:
                pass
        logger.info(f"[Worker] Brifing {sent} ta obunchiga yuborildi")
    except Exception as e:
        logger.error(f"[Worker] Premium yuborish xato: {e}")
