#!/usr/bin/env python3
"""
Azia Quant Bot — Alert Worker
Narx ogohlantirishlari tekshirish
"""

import logging
from telegram.ext import ContextTypes

from database import get_all_active_alerts, delete_alert
from services.crypto_service import crypto_service
from services.stock_service import stock_service

logger = logging.getLogger(__name__)


async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    """Har 5 daqiqada alertlarni tekshirish"""
    try:
        alerts = await get_all_active_alerts()
        if not alerts:
            return

        for alert in alerts:
            try:
                await _check_single_alert(context, alert)
            except Exception as e:
                logger.error(f"Alert tekshirishda: {e}")

    except Exception as e:
        logger.error(f"[AlertWorker] Xato: {e}")


async def _check_single_alert(context, alert: dict):
    """Bitta alertni tekshirish"""
    uid         = alert["user_id"]
    ticker      = alert["ticker"]
    ticker_type = alert["ticker_type"]
    alert_type  = alert["alert_type"]
    condition   = alert["condition"]
    target      = float(alert["value"])
    alert_id    = alert["id"]

    # Hozirgi narx olish
    current = _get_current_value(ticker, ticker_type, alert_type)
    if current is None:
        return

    # Shart tekshirish
    triggered = False
    if condition == "above" and current >= target:
        triggered = True
    elif condition == "below" and current <= target:
        triggered = True

    if not triggered:
        return

    # Xabar yuborish
    type_labels = {
        "price": "Narx",
        "rsi":   "RSI",
        "pct":   "O'zgarish"
    }
    cond_labels = {
        "above": "dan yuqori",
        "below": "dan past"
    }

    type_label = type_labels.get(alert_type, alert_type)
    cond_label = cond_labels.get(condition, condition)

    msg = (
        f"🔔 <b>OGOHLANTIRISH!</b>\n\n"
        f"📌 Aktiv: <b>{ticker}</b>\n"
        f"📊 {type_label}: <b>{current:.4f}</b>\n"
        f"🎯 Shart: {target:.4f} {cond_label}\n\n"
        f"⚡ Shart bajarildi!"
    )

    try:
        await context.bot.send_message(
            chat_id=uid,
            text=msg,
            parse_mode="HTML"
        )
        # Alert o'chirish (bir marta ishlaydi)
        await delete_alert(alert_id, uid)
        logger.info(f"[Alert] {ticker} alert yuborildi → {uid}")
    except Exception as e:
        logger.error(f"[Alert] Yuborish xato: {e}")


def _get_current_value(ticker: str, ticker_type: str, alert_type: str):
    """Hozirgi qiymat olish"""
    try:
        if ticker_type == "crypto":
            if alert_type == "price":
                return crypto_service.get_price(ticker)
            elif alert_type == "rsi":
                return crypto_service._calc_rsi(ticker)
        elif ticker_type == "stock":
            quote = stock_service.get_quote(ticker)
            if quote:
                if alert_type == "price":
                    return quote["price"]
                elif alert_type == "pct":
                    return quote["pct"]
    except Exception as e:
        logger.error(f"Qiymat olish xato: {e}")
    return None
