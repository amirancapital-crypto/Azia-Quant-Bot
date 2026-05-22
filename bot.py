#!/usr/bin/env python3
"""
Azia Quant Bot — Obuna boshqaruv boti
Yangilangan versiya: Screener, yangi bo'limlar, tuzatishlar
"""

import os
import sqlite3
import asyncio
import yfinance as yf
import requests
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, PicklePersistence
)
from telegram.error import TelegramError

# ===================== ENV LOADER =====================
def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        os.environ[key.strip()] = val.strip()
        except Exception as e:
            print(f"[WARNING] .env faylini o'qishda xatolik: {e}")

load_env()

# ===================== SOZLAMALAR =====================
BOT_TOKEN        = os.environ.get("BOT_TOKEN", "8692951194:AAHdeM3za7Rodmc9h3sOnW1NerhHIuHVWfU")
ADMIN_USERNAME   = os.environ.get("ADMIN_USERNAME", "Kvantium_Trader").lstrip("@")
CARD_NUMBER      = os.environ.get("CARD_NUMBER", "9860 6004 2047 6449")
CARD_OWNER       = os.environ.get("CARD_OWNER", "Amanova S")

ADMIN_IDS = []
_admin_id_env = os.environ.get("ADMIN_ID")
if _admin_id_env:
    for x in _admin_id_env.split(","):
        try:
            ADMIN_IDS.append(int(x.strip()))
        except ValueError:
            continue

# Yopiq kanallar ID lari
CHANNEL_IDS = {
    "signals":   int(os.environ.get("CHANNEL_SIGNALS_ID",   -1003859590519)),
    "onchain":   int(os.environ.get("CHANNEL_ONCHAIN_ID",   -1003797469259)),
    "crypto_edu":int(os.environ.get("CHANNEL_CRYPTO_EDU_ID",-1003951825296)),
    "stock_edu": int(os.environ.get("CHANNEL_STOCK_EDU_ID", -1003745532785)),
}

# Kanal bo'limlari (havola yuboriladi)
CHANNEL_SECTIONS = {"signals", "onchain", "crypto_edu", "stock_edu"}

# Screener bo'limlari (havola yuborilmaydi, bot ichida ishlaydi)
SCREENER_SECTIONS = {"aksiya_scr", "crypto_scr"}

# Narxlar: kanal bo'limlari (signals, onchain)
PRICES = {3: 50, 6: 100, 0: 300}  # 0 = doimiy

# Yillik narxlar
YEARLY_PRICES = {
    "crypto_edu": 100,
}

# Screener narxlari (yillik)
SCREENER_PRICES = {
    "aksiya_scr": 100,
    "crypto_scr":  50,
}

SECTION_NAMES = {
    "signals":    "📊 Crypto va Aksiya Signallar",
    "onchain":    "🔗 Onchain Trading",
    "crypto_edu": "📚 Crypto Darslar",
    "stock_edu":  "📈 Fond Bozori Darslar",
    "aksiya_scr": "🔎 Aksiya Screener",
    "crypto_scr": "🔍 Crypto Screener",
}

# ===================== DATABASE SYNC =====================
def _init_db_sync():
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        c = conn.cursor()
        # Asosiy obunalar jadvali
        c.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT,
                section TEXT NOT NULL,
                duration_months INTEGER NOT NULL,
                start_date TEXT,
                end_date TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Adminlar jadvali
        c.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY,
                chat_id INTEGER NOT NULL
            )
        """)
        # Screener obunalari jadvali
        c.execute("""
            CREATE TABLE IF NOT EXISTS screener_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT,
                section TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    except sqlite3.Error as e:
        print(f"[ERROR] Database init xatosi: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def _save_subscription_sync(user_id, username, full_name, section, duration):
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        c = conn.cursor()
        c.execute("""
            INSERT INTO subscriptions (user_id, username, full_name, section, duration_months)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username or "", full_name or "Noma'lum", section, duration))
        sub_id = c.lastrowid
        conn.commit()
        return sub_id
    except sqlite3.Error as e:
        print(f"[ERROR] Subscription saqlashda xatolik: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def _get_subscription_sync(sub_id):
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM subscriptions WHERE id=?", (sub_id,))
        row = c.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"[ERROR] Subscription olishda xatolik: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def _approve_subscription_sync(sub_id, duration_months):
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        c = conn.cursor()
        now = datetime.now()
        if duration_months == 0:
            end_date = None
        else:
            end_date = (now + timedelta(days=30 * duration_months)).isoformat()
        c.execute("""
            UPDATE subscriptions SET status='approved', start_date=?, end_date=? WHERE id=?
        """, (now.isoformat(), end_date, sub_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"[ERROR] Subscription tasdiqlashda xatolik: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def _reject_subscription_sync(sub_id):
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        c = conn.cursor()
        c.execute("UPDATE subscriptions SET status='rejected' WHERE id=?", (sub_id,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"[ERROR] Subscription rad etishda xatolik: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def _mark_expired_sync(sub_id):
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        c = conn.cursor()
        c.execute("UPDATE subscriptions SET status='expired' WHERE id=?", (sub_id,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"[ERROR] Expired belgilashda xatolik: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def _get_expired_subscriptions_sync():
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute("""
            SELECT * FROM subscriptions
            WHERE status='approved' AND end_date < ? AND duration_months != 0
        """, (now,))
        rows = c.fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as e:
        print(f"[ERROR] Muddati tugaganlarni olishda xatolik: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def _save_admin_id_sync(chat_id):
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO admins (id, chat_id) VALUES (?, ?)", (chat_id, chat_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"[ERROR] Admin ID saqlashda xatolik: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def _get_admin_ids_sync():
    ids = list(ADMIN_IDS)
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        c = conn.cursor()
        c.execute("SELECT chat_id FROM admins")
        rows = c.fetchall()
        for row in rows:
            if row[0] not in ids:
                ids.append(row[0])
    except sqlite3.Error as e:
        print(f"[ERROR] Admin IDlarni olishda xatolik: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
    return ids

# --- Screener obuna ---
def _save_screener_sub_sync(user_id, username, full_name, section):
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        c = conn.cursor()
        c.execute("""
            INSERT INTO screener_subscriptions (user_id, username, full_name, section)
            VALUES (?, ?, ?, ?)
        """, (user_id, username or "", full_name or "Noma'lum", section))
        sub_id = c.lastrowid
        conn.commit()
        return sub_id
    except sqlite3.Error as e:
        print(f"[ERROR] Screener sub saqlashda xatolik: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def _get_screener_sub_sync(sub_id):
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM screener_subscriptions WHERE id=?", (sub_id,))
        row = c.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"[ERROR] Screener sub olishda xatolik: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def _approve_screener_sub_sync(sub_id):
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        c = conn.cursor()
        now = datetime.now()
        end_date = (now + timedelta(days=365)).isoformat()
        c.execute("""
            UPDATE screener_subscriptions SET status='approved', start_date=?, end_date=? WHERE id=?
        """, (now.isoformat(), end_date, sub_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"[ERROR] Screener sub tasdiqlashda xatolik: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def _reject_screener_sub_sync(sub_id):
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        c = conn.cursor()
        c.execute("UPDATE screener_subscriptions SET status='rejected' WHERE id=?", (sub_id,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"[ERROR] Screener sub rad etishda xatolik: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def _check_screener_access_sync(user_id, section):
    """Foydalanuvchining screener obunasi faolmi?"""
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute("""
            SELECT * FROM screener_subscriptions
            WHERE user_id=? AND section=? AND status='approved' AND end_date > ?
        """, (user_id, section, now))
        row = c.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"[ERROR] Screener access tekshirishda xatolik: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def _get_expired_screener_subs_sync():
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute("""
            SELECT * FROM screener_subscriptions
            WHERE status='approved' AND end_date < ?
        """, (now,))
        rows = c.fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as e:
        print(f"[ERROR] Muddati tugagan screener sublarni olishda xatolik: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def _mark_screener_expired_sync(sub_id):
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        c = conn.cursor()
        c.execute("UPDATE screener_subscriptions SET status='expired' WHERE id=?", (sub_id,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"[ERROR] Screener expired belgilashda xatolik: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

# ===================== DATABASE ASYNC =====================
async def init_db():
    await asyncio.to_thread(_init_db_sync)

async def save_subscription(user_id, username, full_name, section, duration):
    return await asyncio.to_thread(_save_subscription_sync, user_id, username, full_name, section, duration)

async def get_subscription(sub_id):
    return await asyncio.to_thread(_get_subscription_sync, sub_id)

async def approve_subscription(sub_id, duration_months):
    await asyncio.to_thread(_approve_subscription_sync, sub_id, duration_months)

async def reject_subscription(sub_id):
    await asyncio.to_thread(_reject_subscription_sync, sub_id)

async def mark_expired(sub_id):
    await asyncio.to_thread(_mark_expired_sync, sub_id)

async def get_expired_subscriptions():
    return await asyncio.to_thread(_get_expired_subscriptions_sync)

async def save_admin_id(chat_id):
    await asyncio.to_thread(_save_admin_id_sync, chat_id)

async def get_admin_ids():
    return await asyncio.to_thread(_get_admin_ids_sync)

async def save_screener_sub(user_id, username, full_name, section):
    return await asyncio.to_thread(_save_screener_sub_sync, user_id, username, full_name, section)

async def get_screener_sub(sub_id):
    return await asyncio.to_thread(_get_screener_sub_sync, sub_id)

async def approve_screener_sub(sub_id):
    await asyncio.to_thread(_approve_screener_sub_sync, sub_id)

async def reject_screener_sub(sub_id):
    await asyncio.to_thread(_reject_screener_sub_sync, sub_id)

async def check_screener_access(user_id, section):
    return await asyncio.to_thread(_check_screener_access_sync, user_id, section)

async def get_expired_screener_subs():
    return await asyncio.to_thread(_get_expired_screener_subs_sync)

async def mark_screener_expired(sub_id):
    await asyncio.to_thread(_mark_screener_expired_sync, sub_id)

# ===================== SCREENER FUNKSIYALARI =====================
def get_stock_data(ticker: str) -> str:
    """Yahoo Finance dan aksiya ma'lumotlarini oladi."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        if not info or info.get('regularMarketPrice') is None:
            return None

        name            = info.get('longName', ticker)
        price           = info.get('regularMarketPrice', 0)
        change_pct      = info.get('regularMarketChangePercent', 0)
        market_cap      = info.get('marketCap', 0)
        week52_high     = info.get('fiftyTwoWeekHigh', 0)
        week52_low      = info.get('fiftyTwoWeekLow', 0)
        sector          = info.get('sector', 'Noma\'lum')
        exchange        = info.get('exchange', '')

        # Fundamental
        pe_ratio        = info.get('trailingPE', 0)
        pb_ratio        = info.get('priceToBook', 0)
        ps_ratio        = info.get('priceToSalesTrailing12Months', 0)
        ev_ebitda       = info.get('enterpriseToEbitda', 0)
        eps             = info.get('trailingEps', 0)
        eps_growth      = info.get('earningsGrowth', 0)
        revenue         = info.get('totalRevenue', 0)
        net_income      = info.get('netIncomeToCommon', 0)
        gross_margin    = info.get('grossMargins', 0)
        net_margin      = info.get('profitMargins', 0)
        roe             = info.get('returnOnEquity', 0)
        roa             = info.get('returnOnAssets', 0)
        debt_equity     = info.get('debtToEquity', 0)
        free_cash_flow  = info.get('freeCashflow', 0)
        dividend        = info.get('dividendRate', 0)
        div_yield       = info.get('dividendYield', 0)

        # Texnik
        beta            = info.get('beta', 0)
        ma50            = info.get('fiftyDayAverage', 0)
        ma200           = info.get('twoHundredDayAverage', 0)
        rsi             = info.get('rsi', None)

        # Analyst
        rec             = info.get('recommendationKey', 'N/A').upper()
        target_price    = info.get('targetMeanPrice', 0)
        analyst_buy     = info.get('numberOfAnalystOpinions', 0)

        # Institutional
        inst_hold       = info.get('institutionPercentHeld', 0)
        insider_hold    = info.get('insiderPercentHeld', 0)

        # Insider tranzaksiyalar
        try:
            insider_df = stock.insider_transactions
            insider_txt = ""
            if insider_df is not None and not insider_df.empty:
                for _, row in insider_df.head(3).iterrows():
                    insider_name  = row.get('Name', 'Noma\'lum')
                    insider_shares= row.get('Shares', 0)
                    insider_val   = row.get('Value', 0)
                    insider_date  = str(row.get('Start Date', ''))[:10]
                    insider_type  = "SOTDI ⚠️" if insider_shares < 0 else "OLDI ✅"
                    insider_txt += (
                        f"• {insider_name}: "
                        f"{abs(insider_shares):,} aksiya {insider_type}\n"
                        f"  ${abs(insider_val):,.0f} | {insider_date}\n"
                    )
            else:
                insider_txt = "• Ma'lumot topilmadi\n"
        except:
            insider_txt = "• Ma'lumot topilmadi\n"

        # Choraklik hisobotlar
        try:
            earnings_df = stock.earnings_dates
            earnings_txt = ""
            if earnings_df is not None and not earnings_df.empty:
                for idx, row in earnings_df.head(4).iterrows():
                    date_str    = str(idx)[:10]
                    eps_est     = row.get('EPS Estimate', 0)
                    eps_act     = row.get('Reported EPS', 0)
                    if eps_est and eps_act:
                        diff_pct = ((eps_act - eps_est) / abs(eps_est)) * 100 if eps_est != 0 else 0
                        icon = "✅" if diff_pct >= 0 else "❌"
                        earnings_txt += (
                            f"• {date_str}: ${eps_act:.2f} "
                            f"(kutilgan ${eps_est:.2f}) "
                            f"{diff_pct:+.1f}% {icon}\n"
                        )
            if not earnings_txt:
                earnings_txt = "• Ma'lumot topilmadi\n"
        except:
            earnings_txt = "• Ma'lumot topilmadi\n"

        # Yangiliklar
        try:
            news_list = stock.news
            news_txt = ""
            for n in (news_list or [])[:3]:
                title     = n.get('title', '')[:60]
                source    = n.get('publisher', '')
                link      = n.get('link', '')
                news_txt += f"• <a href='{link}'>{title}</a> | {source}\n"
            if not news_txt:
                news_txt = "• Yangilik topilmadi\n"
        except:
            news_txt = "• Yangilik topilmadi\n"

        # RSI hisoblash (14 kunlik)
        try:
            hist = stock.history(period="1mo")
            if hist is not None and len(hist) >= 14:
                delta   = hist['Close'].diff()
                gain    = delta.where(delta > 0, 0).rolling(14).mean()
                loss    = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs      = gain / loss
                rsi_val = 100 - (100 / (1 + rs.iloc[-1]))
                if rsi_val < 30:
                    rsi_txt = f"{rsi_val:.0f} (Oversold 🟢)"
                elif rsi_val > 70:
                    rsi_txt = f"{rsi_val:.0f} (Overbought 🔴)"
                else:
                    rsi_txt = f"{rsi_val:.0f} (Neytral ⚪)"
            else:
                rsi_txt = "N/A"
        except:
            rsi_txt = "N/A"

        # MA taqqoslash
        ma50_txt  = f"${ma50:,.2f} {'✅' if price > ma50 else '❌'}"  if ma50 else "N/A"
        ma200_txt = f"${ma200:,.2f} {'✅' if price > ma200 else '❌'}" if ma200 else "N/A"

        # Sonlarni formatlash
        def fmt_big(n):
            if not n: return "N/A"
            if abs(n) >= 1e12: return f"${n/1e12:.2f}T"
            if abs(n) >= 1e9:  return f"${n/1e9:.2f}B"
            if abs(n) >= 1e6:  return f"${n/1e6:.2f}M"
            return f"${n:,.0f}"

        change_icon = "📈" if change_pct >= 0 else "📉"
        change_sign = "+" if change_pct >= 0 else ""

        result = (
            f"🔎 <b>{ticker.upper()} — {name}</b>\n"
            f"📍 {sector} | {exchange}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"

            f"💰 <b>ASOSIY:</b>\n"
            f"• Narx: <b>${price:,.2f}</b> ({change_sign}{change_pct:.2f}% {change_icon})\n"
            f"• Bozor kap: {fmt_big(market_cap)}\n"
            f"• 52 hafta: ${week52_low:,.2f} — ${week52_high:,.2f}\n\n"

            f"📊 <b>FUNDAMENTAL:</b>\n"
            f"• P/E: {pe_ratio:.1f}\n"
            f"• P/B: {pb_ratio:.1f}\n"
            f"• P/S: {ps_ratio:.1f}\n"
            f"• EV/EBITDA: {ev_ebitda:.1f}\n"
            f"• EPS: ${eps:.2f} ({'+' if eps_growth >= 0 else ''}{eps_growth*100:.1f}%)\n"
            f"• Daromad: {fmt_big(revenue)}\n"
            f"• Sof foyda: {fmt_big(net_income)}\n"
            f"• Gross Margin: {gross_margin*100:.1f}%\n"
            f"• Net Margin: {net_margin*100:.1f}%\n"
            f"• ROE: {roe*100:.1f}%\n"
            f"• ROA: {roa*100:.1f}%\n"
            f"• Qarz/Kapital: {debt_equity:.2f}\n"
            f"• Free Cash Flow: {fmt_big(free_cash_flow)}\n"
            f"• Dividend: ${dividend:.2f} ({div_yield*100:.1f}%)\n\n"

            f"📈 <b>TEXNIK:</b>\n"
            f"• RSI: {rsi_txt}\n"
            f"• MA50: {ma50_txt}\n"
            f"• MA200: {ma200_txt}\n"
            f"• Beta: {beta:.2f}\n\n"

            f"🏦 <b>ANALYST REYTINGI:</b>\n"
            f"• Xulosa: <b>{rec}</b>\n"
            f"• Maqsad narx: ${target_price:,.2f}\n"
            f"• Analitiklar soni: {analyst_buy}\n\n"

            f"🏛 <b>INSTITUTIONAL:</b>\n"
            f"• Fondlar ulushi: {inst_hold*100:.1f}%\n"
            f"• Insider ulushi: {insider_hold*100:.1f}%\n\n"

            f"👤 <b>INSIDER TRANZAKSIYALAR:</b>\n"
            f"{insider_txt}\n"

            f"📋 <b>CHORAKLIK HISOBOTLAR:</b>\n"
            f"{earnings_txt}\n"

            f"📰 <b>YANGILIKLAR:</b>\n"
            f"{news_txt}\n"

            f"🕌 <b>ISLOMIY MUVOFIQLIK:</b>\n"
            f"• Tez kunda qo'shiladi ⏳\n\n"

            f"🤖 <b>AI TAHLILI:</b>\n"
            f"• Tez kunda qo'shiladi ⏳\n\n"

            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ Bu tahlil faqat ma'lumot uchun.\n"
            f"Investitsiya qarori faqat sizga bog'liq.\n"
            f"Azia Invest javobgar emas."
        )
        return result

    except Exception as e:
        print(f"[ERROR] Stock data olishda xatolik ({ticker}): {e}")
        return None


def get_crypto_data(coin_id: str) -> str:
    """CoinGecko va DefiLlama dan crypto ma'lumotlarini oladi."""
    try:
        # CoinGecko API
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id.lower()}"
        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "false",
            "developer_data": "false",
        }
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return None

        data   = resp.json()
        md     = data.get("market_data", {})
        name   = data.get("name", coin_id)
        symbol = data.get("symbol", "").upper()

        price        = md.get("current_price", {}).get("usd", 0)
        change_24h   = md.get("price_change_percentage_24h", 0)
        market_cap   = md.get("market_cap", {}).get("usd", 0)
        volume_24h   = md.get("total_volume", {}).get("usd", 0)
        circ_supply  = md.get("circulating_supply", 0)
        max_supply   = md.get("max_supply", None)
        fdv          = md.get("fully_diluted_valuation", {}).get("usd", 0)
        ath          = md.get("ath", {}).get("usd", 0)
        atl          = md.get("atl", {}).get("usd", 0)
        ath_change   = md.get("ath_change_percentage", {}).get("usd", 0)

        # Qazilgan foiz
        if max_supply and circ_supply:
            mined_pct = (circ_supply / max_supply) * 100
            mined_txt = f"{mined_pct:.1f}%"
        else:
            mined_txt = "Cheksiz (Max Supply yo'q)"

        # Fear & Greed Index
        try:
            fg_resp = requests.get("https://api.alternative.me/fng/", timeout=10)
            fg_data = fg_resp.json()
            fg_val  = fg_data['data'][0]['value']
            fg_cls  = fg_data['data'][0]['value_classification']
            if int(fg_val) >= 75:
                fg_icon = "🔴"
            elif int(fg_val) >= 50:
                fg_icon = "🟡"
            elif int(fg_val) >= 25:
                fg_icon = "🟠"
            else:
                fg_icon = "🟢"
            fg_txt = f"{fg_val}/100 — {fg_cls} {fg_icon}"
        except:
            fg_txt = "N/A"

        # RSI hisoblash (14 kunlik, CoinGecko OHLC)
        try:
            ohlc_url  = f"https://api.coingecko.com/api/v3/coins/{coin_id.lower()}/ohlc"
            ohlc_resp = requests.get(ohlc_url, params={"vs_currency": "usd", "days": "30"}, timeout=10)
            if ohlc_resp.status_code == 200:
                ohlc_data = ohlc_resp.json()
                closes    = [c[4] for c in ohlc_data]
                if len(closes) >= 14:
                    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
                    gains  = [d if d > 0 else 0 for d in deltas]
                    losses = [-d if d < 0 else 0 for d in deltas]
                    avg_g  = sum(gains[-14:]) / 14
                    avg_l  = sum(losses[-14:]) / 14
                    if avg_l == 0:
                        rsi_v = 100
                    else:
                        rs    = avg_g / avg_l
                        rsi_v = 100 - (100 / (1 + rs))
                    if rsi_v < 30:
                        rsi_txt = f"{rsi_v:.0f} (Oversold 🟢)"
                    elif rsi_v > 70:
                        rsi_txt = f"{rsi_v:.0f} (Overbought 🔴)"
                    else:
                        rsi_txt = f"{rsi_v:.0f} (Neytral ⚪)"
                else:
                    rsi_txt = "N/A"
            else:
                rsi_txt = "N/A"
        except:
            rsi_txt = "N/A"

        # MA50 va MA200
        try:
            hist_url  = f"https://api.coingecko.com/api/v3/coins/{coin_id.lower()}/market_chart"
            hist_resp = requests.get(hist_url, params={"vs_currency": "usd", "days": "200"}, timeout=10)
            if hist_resp.status_code == 200:
                hist_data = hist_resp.json()
                prices    = [p[1] for p in hist_data.get("prices", [])]
                ma50_v    = sum(prices[-50:]) / 50 if len(prices) >= 50 else None
                ma200_v   = sum(prices[-200:]) / 200 if len(prices) >= 200 else None
                ma50_txt  = f"${ma50_v:,.2f} {'✅' if price > ma50_v else '❌'}" if ma50_v else "N/A"
                ma200_txt = f"${ma200_v:,.2f} {'✅' if price > ma200_v else '❌'}" if ma200_v else "N/A"
            else:
                ma50_txt = ma200_txt = "N/A"
        except:
            ma50_txt = ma200_txt = "N/A"

        # Token Unlock (DefiLlama)
        try:
            unlock_url  = f"https://coins.llama.fi/chart/coingecko:{coin_id.lower()}"
            unlock_resp = requests.get(f"https://api.llama.fi/emission/{coin_id.lower()}", timeout=10)
            if unlock_resp.status_code == 200:
                unlock_data = unlock_resp.json()
                events      = unlock_data.get("events", [])
                unlock_txt  = ""
                now_ts      = datetime.now().timestamp()
                future      = [e for e in events if e.get("timestamp", 0) > now_ts]
                for ev in future[:3]:
                    ev_date   = datetime.fromtimestamp(ev["timestamp"]).strftime("%d-%b %Y")
                    ev_amount = ev.get("noOfTokens", [0])
                    ev_amount = ev_amount[0] if isinstance(ev_amount, list) else ev_amount
                    ev_desc   = ev.get("description", "")
                    days_left = int((ev["timestamp"] - now_ts) / 86400)
                    unlock_txt += f"• {ev_date}: {ev_amount:,.0f} token ({days_left} kun)\n  {ev_desc}\n"
                if not unlock_txt:
                    unlock_txt = "• Unlock ma'lumoti topilmadi\n"
            else:
                unlock_txt = "• Ma'lumot topilmadi\n"
        except:
            unlock_txt = "• Ma'lumot topilmadi\n"

        # Yangiliklar (CoinGecko)
        try:
            news_url  = f"https://api.coingecko.com/api/v3/news"
            news_resp = requests.get(news_url, timeout=10)
            news_txt  = ""
            if news_resp.status_code == 200:
                news_data = news_resp.json().get("data", [])
                count = 0
                for n in news_data:
                    if count >= 3:
                        break
                    title = n.get("title", "")[:60]
                    url_n = n.get("url", "")
                    src   = n.get("news_site", "")
                    if symbol.lower() in title.lower() or name.lower() in title.lower():
                        news_txt += f"• <a href='{url_n}'>{title}</a> | {src}\n"
                        count += 1
            if not news_txt:
                news_txt = "• Yangilik topilmadi\n"
        except:
            news_txt = "• Yangilik topilmadi\n"

        def fmt_big(n):
            if not n: return "N/A"
            if abs(n) >= 1e12: return f"${n/1e12:.2f}T"
            if abs(n) >= 1e9:  return f"${n/1e9:.2f}B"
            if abs(n) >= 1e6:  return f"${n/1e6:.2f}M"
            return f"${n:,.2f}"

        change_icon = "📈" if change_24h >= 0 else "📉"
        change_sign = "+" if change_24h >= 0 else ""

        result = (
            f"🔍 <b>{symbol} — {name}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"

            f"💰 <b>ASOSIY:</b>\n"
            f"• Narx: <b>${price:,.4f}</b> ({change_sign}{change_24h:.2f}% {change_icon})\n"
            f"• Bozor kap: {fmt_big(market_cap)}\n"
            f"• Hajm (24s): {fmt_big(volume_24h)}\n\n"

            f"📦 <b>TA'MINOT:</b>\n"
            f"• Muomaladagi: {circ_supply:,.0f} {symbol}\n"
            f"• Max Supply: {f'{max_supply:,.0f}' if max_supply else 'Cheksiz'} {symbol}\n"
            f"• Qazilgan: {mined_txt}\n"
            f"• FDV: {fmt_big(fdv)}\n\n"

            f"📈 <b>TEXNIK:</b>\n"
            f"• RSI: {rsi_txt}\n"
            f"• MA50: {ma50_txt}\n"
            f"• MA200: {ma200_txt}\n"
            f"• ATH: ${ath:,.4f} ({ath_change:.1f}%)\n"
            f"• ATL: ${atl:,.4f}\n\n"

            f"🔓 <b>TOKEN UNLOCK:</b>\n"
            f"{unlock_txt}\n"

            f"😨 <b>FEAR & GREED:</b>\n"
            f"• {fg_txt}\n\n"

            f"🐋 <b>WHALE TRACKER:</b>\n"
            f"• Tez kunda qo'shiladi ⏳\n\n"

            f"📊 <b>FUNDING RATE:</b>\n"
            f"• Tez kunda qo'shiladi ⏳\n\n"

            f"💥 <b>LIKVIDATSIYALAR:</b>\n"
            f"• Tez kunda qo'shiladi ⏳\n\n"

            f"📰 <b>YANGILIKLAR:</b>\n"
            f"{news_txt}\n"

            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ Bu ma'lumot faqat tahlil uchun.\n"
            f"Investitsiya qarori faqat sizga bog'liq.\n"
            f"Azia Invest javobgar emas."
        )
        return result

    except Exception as e:
        print(f"[ERROR] Crypto data olishda xatolik ({coin_id}): {e}")
        return None


# ===================== KLAVIATURALAR =====================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Crypto va Aksiya Signallar", callback_data="sec_signals")],
        [InlineKeyboardButton("🔗 Onchain Trading",            callback_data="sec_onchain")],
        [InlineKeyboardButton("📚 Crypto Darslar",             callback_data="sec_crypto_edu")],
        [InlineKeyboardButton("📈 Fond Bozori Darslar",        callback_data="sec_stock_edu")],
        [InlineKeyboardButton("🤖 Quant Trading",              callback_data="sec_quant")],
        [InlineKeyboardButton("🔍 Crypto Screener",            callback_data="sec_crypto_scr")],
        [InlineKeyboardButton("🔎 Aksiya Screener",            callback_data="sec_aksiya_scr")],
        [InlineKeyboardButton("💬 Admin bilan aloqa",          callback_data="sec_admin")],
    ])

def duration_menu(section):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗓 3 oylik — $50",  callback_data=f"dur_{section}_3")],
        [InlineKeyboardButton("🗓 6 oylik — $100", callback_data=f"dur_{section}_6")],
        [InlineKeyboardButton("♾ Doimiy — $300",  callback_data=f"dur_{section}_0")],
        [InlineKeyboardButton("⬅️ Ortga",          callback_data="back")],
    ])

def screener_buy_menu(section):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Yillik obuna — $" + str(SCREENER_PRICES[section]),
                              callback_data=f"scr_buy_{section}")],
        [InlineKeyboardButton("⬅️ Ortga", callback_data="back")],
    ])

def back_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Ortga", callback_data="back")]])

def home_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Bosh menyu", callback_data="back")]])

def admin_menu(sub_id):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{sub_id}"),
        InlineKeyboardButton("❌ Rad etish",  callback_data=f"reject_{sub_id}"),
    ]])

def admin_screener_menu(sub_id):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"scr_approve_{sub_id}"),
        InlineKeyboardButton("❌ Rad etish",  callback_data=f"scr_reject_{sub_id}"),
    ]])

def screener_action_menu(section):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Ticker kiriting", callback_data=f"scr_use_{section}")],
        [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back")],
    ])

# ===================== WELCOME MATNI =====================
WELCOME = """🌟 <b>Assalomu alaykum!</b>

Azia Invest Quant botiga xush kelibsiz! 🤝

━━━━━━━━━━━━━━━━━━━━

🤖 <b>Bot haqida:</b>

Bu bot murakkab AI algoritmlari asosida
tuzilgan bo'lib foydalanuvchilarga:

📊 Moliyaviy bozorlar tahlili
📈 Aksiya va Crypto signallari
🔍 Professional Screener xizmati
📚 Moliyaviy ta'lim materiallari
📋 Moliyaviy hisobotlar

...kabi xizmatlarni taqdim etadi.

━━━━━━━━━━━━━━━━━━━━

⚡ <b>Azia Quant Bot</b> — bu shunchaki
ma'lumotlar bazasi emas, balki kuchli
Kvant algoritmlari asosida Moliyaviy
bozorlarni tahlil qilish uchun
yaratilgan professional platforma.

━━━━━━━━━━━━━━━━━━━━

⚠️ <b>Risk haqida ogohlantirish!</b>

Botning har qanday funksiyasidan
foydalanganingizda:

🛡 Savdo intizomiga amal qiling
📉 Risk menejmentni unutmang
💡 Har bir qarorni mustaqil tahlil qiling
🚫 Hech qachon 100% kapitalingizni
   bitta aktivga riskga qo'ymang!

━━━━━━━━━━━━━━━━━━━━

👇 Bo'limlardan birini tanlang:"""


# ===================== HANDLERLAR =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.username == ADMIN_USERNAME:
        await save_admin_id(user.id)
        await update.message.reply_text("✅ Admin sifatida ro'yxatdan o'tdingiz.")
    await update.message.reply_text(WELCOME, parse_mode="HTML", reply_markup=main_menu())


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    await q.answer()
    data = q.data
    user = q.from_user

    if user.username == ADMIN_USERNAME:
        await save_admin_id(user.id)

    # ── Bosh menyu ──
    if data == "back":
        context.user_data.clear()
        await q.edit_message_text(WELCOME, parse_mode="HTML", reply_markup=main_menu())

    # ── Signals ──
    elif data == "sec_signals":
        txt = (
            "📊 <b>Crypto va Aksiya Signallar</b>\n\n"
            "Quant Trading va Onchain tahlil metodlaridan foydalanib "
            "tayyorlangan professional savdo signallari.\n\n"
            "💰 <b>Obuna narxlari:</b>\n"
            "• 3 oylik — $50\n"
            "• 6 oylik — $100\n"
            "• ♾ Doimiy — $300\n\n"
            "Muddatni tanlang:"
        )
        await q.edit_message_text(txt, parse_mode="HTML", reply_markup=duration_menu("signals"))

    # ── Onchain ──
    elif data == "sec_onchain":
        txt = (
            "🔗 <b>Onchain Trading</b>\n\n"
            "Blockchain ma'lumotlari va Onchain ko'rsatkichlar asosida "
            "savdo signallari va chuqur tahlillar.\n\n"
            "💰 <b>Obuna narxlari:</b>\n"
            "• 3 oylik — $50\n"
            "• 6 oylik — $100\n"
            "• ♾ Doimiy — $300\n\n"
            "Muddatni tanlang:"
        )
        await q.edit_message_text(txt, parse_mode="HTML", reply_markup=duration_menu("onchain"))

    # ── Crypto Darslar ──
    elif data == "sec_crypto_edu":
        txt = (
            "📚 <b>Crypto Darslar</b>\n\n"
            "Crypto bozori haqida to'liq bilim.\n"
            "Boshlang'ichdan professionalga qadar.\n\n"
            "💰 <b>Yillik obuna: $100</b>\n\n"
            "Obuna sotib olish uchun tugmani bosing:"
        )
        await q.edit_message_text(
            txt, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Yillik obuna — $100", callback_data="dur_crypto_edu_12")],
                [InlineKeyboardButton("⬅️ Ortga", callback_data="back")],
            ])
        )

    # ── Fond Bozori Darslar (faol emas) ──
    elif data == "sec_stock_edu":
        await q.edit_message_text(
            "⏳ <b>Fond Bozori Darslar hali faol emas</b>\n\nTez kunda ishga tushiriladi. 🚀",
            parse_mode="HTML",
            reply_markup=back_menu()
        )

    # ── Quant Trading (faol emas) ──
    elif data == "sec_quant":
        await q.edit_message_text(
            "⏳ <b>Quant Trading hali faol emas</b>\n\nTez kunda ishga tushiriladi. 🚀",
            parse_mode="HTML",
            reply_markup=back_menu()
        )

    # ── Crypto Screener ──
    elif data == "sec_crypto_scr":
        access = await check_screener_access(user.id, "crypto_scr")
        if access:
            await q.edit_message_text(
                "🔍 <b>Crypto Screener</b>\n\n"
                "Coin ticker yoki nomini yuboring.\n"
                "Masalan: <code>bitcoin</code>, <code>ethereum</code>, <code>solana</code>\n\n"
                "CoinGecko ID sini kiriting:",
                parse_mode="HTML",
                reply_markup=back_menu()
            )
            context.user_data['screener_mode'] = 'crypto'
        else:
            await q.edit_message_text(
                "🔍 <b>Crypto Screener</b>\n\n"
                "Barcha coinlar haqida to'liq ma'lumot:\n"
                "• Narx, bozor kap, volume\n"
                "• Max Supply, Token Unlock\n"
                "• RSI, MA50, MA200\n"
                "• Fear & Greed Index\n"
                "• Yangiliklar + havola\n\n"
                "💰 <b>Yillik obuna: $50</b>\n\n"
                "Obuna sotib olish uchun tugmani bosing:",
                parse_mode="HTML",
                reply_markup=screener_buy_menu("crypto_scr")
            )

    # ── Aksiya Screener ──
    elif data == "sec_aksiya_scr":
        access = await check_screener_access(user.id, "aksiya_scr")
        if access:
            await q.edit_message_text(
                "🔎 <b>Aksiya Screener</b>\n\n"
                "Aksiya ticker yuboring.\n"
                "Masalan: <code>AAPL</code>, <code>TSLA</code>, <code>MSFT</code>\n\n"
                "Ticker kiriting:",
                parse_mode="HTML",
                reply_markup=back_menu()
            )
            context.user_data['screener_mode'] = 'stock'
        else:
            await q.edit_message_text(
                "🔎 <b>Aksiya Screener</b>\n\n"
                "Barcha aksiyalar haqida to'liq tahlil:\n"
                "• Fundamental ko'rsatkichlar\n"
                "• Texnik tahlil (RSI, MA)\n"
                "• Analyst reytinglari\n"
                "• Institutional Ownership\n"
                "• Insider tranzaksiyalar\n"
                "• Choraklik hisobotlar\n"
                "• Yangiliklar + havola\n"
                "• Islomiy muvofiqlik (tez kunda)\n"
                "• AI tahlili (tez kunda)\n\n"
                "💰 <b>Yillik obuna: $100</b>\n\n"
                "Obuna sotib olish uchun tugmani bosing:",
                parse_mode="HTML",
                reply_markup=screener_buy_menu("aksiya_scr")
            )

    # ── Screener obuna sotib olish ──
    elif data.startswith("scr_buy_"):
        section      = data.replace("scr_buy_", "")
        price        = SCREENER_PRICES[section]
        section_name = SECTION_NAMES[section]

        sub_id = await save_screener_sub(user.id, user.username, user.full_name, section)
        context.user_data['scr_sub_id']       = sub_id
        context.user_data['waiting_scr_payment'] = True

        txt = (
            f"💳 <b>To'lov ma'lumotlari</b>\n\n"
            f"📦 Bo'lim: <b>{section_name}</b>\n"
            f"⏱ Muddat: <b>1 yil</b>\n"
            f"💰 Summa: <b>${price}</b>\n\n"
            f"🏦 <b>Karta raqami:</b>\n<code>{CARD_NUMBER}</code>\n"
            f"👤 <b>Karta egasi:</b> {CARD_OWNER}\n\n"
            f"To'lovni amalga oshirgach, <b>to'lov cheki rasmini</b> shu chatga yuboring. 👇"
        )
        await q.edit_message_text(txt, parse_mode="HTML", reply_markup=back_menu())

    # ── Admin aloqa ──
    elif data == "sec_admin":
        await q.edit_message_text(
            f"💬 <b>Admin bilan aloqa</b>\n\nSavol va murojaat uchun:\n👤 @{ADMIN_USERNAME}",
            parse_mode="HTML",
            reply_markup=back_menu()
        )

    # ── Kanal bo'limlari: muddat tanlash ──
    elif data.startswith("dur_"):
        parts    = data.split("_")
        section  = "_".join(parts[1:-1])
        duration = int(parts[-1])

        if section in SCREENER_SECTIONS:
            return

        # Crypto Darslar yillik obuna
        if section == "crypto_edu" and duration == 12:
            price        = YEARLY_PRICES["crypto_edu"]
            section_name = SECTION_NAMES.get(section, section)

            sub_id = await save_subscription(user.id, user.username, user.full_name, section, 12)
            context.user_data['sub_id']          = sub_id
            context.user_data['waiting_payment'] = True

            txt = (
                f"💳 <b>To'lov ma'lumotlari</b>\n\n"
                f"📦 Bo'lim: <b>{section_name}</b>\n"
                f"⏱ Muddat: <b>1 yil</b>\n"
                f"💰 Summa: <b>${price}</b>\n\n"
                f"🏦 <b>Karta raqami:</b>\n<code>{CARD_NUMBER}</code>\n"
                f"👤 <b>Karta egasi:</b> {CARD_OWNER}\n\n"
                f"To'lovni amalga oshirgach, <b>to'lov cheki rasmini</b> shu chatga yuboring. 👇"
            )
            await q.edit_message_text(txt, parse_mode="HTML", reply_markup=back_menu())
            return

        price        = PRICES[duration]
        section_name = SECTION_NAMES.get(section, section)
        duration_label = "♾ Doimiy" if duration == 0 else f"{duration} oy"

        sub_id = await save_subscription(user.id, user.username, user.full_name, section, duration)
        context.user_data['sub_id']          = sub_id
        context.user_data['waiting_payment'] = True

        txt = (
            f"💳 <b>To'lov ma'lumotlari</b>\n\n"
            f"📦 Bo'lim: <b>{section_name}</b>\n"
            f"⏱ Muddat: <b>{duration_label}</b>\n"
            f"💰 Summa: <b>${price}</b>\n\n"
            f"🏦 <b>Karta raqami:</b>\n<code>{CARD_NUMBER}</code>\n"
            f"👤 <b>Karta egasi:</b> {CARD_OWNER}\n\n"
            f"To'lovni amalga oshirgach, <b>to'lov cheki rasmini</b> shu chatga yuboring. 👇"
        )
        await q.edit_message_text(txt, parse_mode="HTML", reply_markup=back_menu())

    # ── Admin: Kanal obunani tasdiqlash ──
    elif data.startswith("approve_"):
        sub_id = int(data.split("_")[1])
        sub    = await get_subscription(sub_id)
        if not sub:
            await q.answer("Obuna topilmadi!", show_alert=True)
            return
        if sub['status'] != 'pending':
            await q.answer("Allaqachon qayta ishlangan!", show_alert=True)
            await q.edit_message_reply_markup(reply_markup=None)
            return

        channel_id = CHANNEL_IDS.get(sub['section'])
        if not channel_id:
            await q.answer("Kanal ID topilmadi!", show_alert=True)
            return

        duration       = sub['duration_months']
        duration_label = "1 yil" if duration == 12 else ("♾ Doimiy" if duration == 0 else f"{duration} oy")
        section_name   = SECTION_NAMES.get(sub['section'], sub['section'])

        try:
            link_expire = datetime.now() + timedelta(hours=24)
            if duration == 0:
                link_obj = await context.bot.create_chat_invite_link(
                    chat_id=channel_id, member_limit=1)
            else:
                link_obj = await context.bot.create_chat_invite_link(
                    chat_id=channel_id, member_limit=1, expire_date=link_expire)

            await approve_subscription(sub_id, duration)
            await context.bot.send_message(
                chat_id=sub['user_id'],
                text=(
                    f"✅ <b>To'lovingiz tasdiqlandi!</b>\n\n"
                    f"📦 <b>Bo'lim:</b> {section_name}\n"
                    f"⏱ <b>Muddat:</b> {duration_label}\n\n"
                    f"🔗 <b>Kanal havolasi:</b>\n{link_obj.invite_link}\n\n"
                    f"⚠️ Havola <b>bir martalik</b> — faqat siz uchun."
                ),
                parse_mode="HTML",
                reply_markup=home_menu()
            )
            await q.edit_message_reply_markup(reply_markup=None)
            await context.bot.send_message(
                chat_id=q.message.chat_id,
                text=f"✅ <b>#{sub_id} — TASDIQLANDI.</b> Havola yuborildi.",
                parse_mode="HTML"
            )
        except TelegramError as e:
            await q.answer(f"Xato: {e}", show_alert=True)

    # ── Admin: Kanal obunani rad etish ──
    elif data.startswith("reject_"):
        sub_id = int(data.split("_")[1])
        sub    = await get_subscription(sub_id)
        if not sub:
            await q.answer("Obuna topilmadi!", show_alert=True)
            return
        if sub['status'] != 'pending':
            await q.answer("Allaqachon qayta ishlangan!", show_alert=True)
            await q.edit_message_reply_markup(reply_markup=None)
            return

        await reject_subscription(sub_id)
        await context.bot.send_message(
            chat_id=sub['user_id'],
            text=(
                "❌ <b>To'lovingiz tasdiqlanmadi.</b>\n\n"
                f"Murojaat uchun: @{ADMIN_USERNAME}"
            ),
            parse_mode="HTML",
            reply_markup=home_menu()
        )
        await q.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(
            chat_id=q.message.chat_id,
            text=f"❌ <b>#{sub_id} — RAD ETILDI.</b>",
            parse_mode="HTML"
        )

    # ── Admin: Screener obunani tasdiqlash ──
    elif data.startswith("scr_approve_"):
        sub_id = int(data.split("_")[2])
        sub    = await get_screener_sub(sub_id)
        if not sub:
            await q.answer("Obuna topilmadi!", show_alert=True)
            return
        if sub['status'] != 'pending':
            await q.answer("Allaqachon qayta ishlangan!", show_alert=True)
            await q.edit_message_reply_markup(reply_markup=None)
            return

        await approve_screener_sub(sub_id)
        section_name = SECTION_NAMES.get(sub['section'], sub['section'])
        await context.bot.send_message(
            chat_id=sub['user_id'],
            text=(
                f"✅ <b>To'lovingiz tasdiqlandi!</b>\n\n"
                f"📦 <b>Bo'lim:</b> {section_name}\n"
                f"⏱ <b>Muddat:</b> 1 yil\n\n"
                f"🎉 Endi screenerdan foydalanishingiz mumkin!\n"
                f"Boshlash uchun /start bosing."
            ),
            parse_mode="HTML",
            reply_markup=home_menu()
        )
        await q.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(
            chat_id=q.message.chat_id,
            text=f"✅ <b>Screener #{sub_id} — TASDIQLANDI.</b>",
            parse_mode="HTML"
        )

    # ── Admin: Screener obunani rad etish ──
    elif data.startswith("scr_reject_"):
        sub_id = int(data.split("_")[2])
        sub    = await get_screener_sub(sub_id)
        if not sub:
            await q.answer("Obuna topilmadi!", show_alert=True)
            return
        if sub['status'] != 'pending':
            await q.answer("Allaqachon qayta ishlangan!", show_alert=True)
            await q.edit_message_reply_markup(reply_markup=None)
            return

        await reject_screener_sub(sub_id)
        await context.bot.send_message(
            chat_id=sub['user_id'],
            text=(
                "❌ <b>To'lovingiz tasdiqlanmadi.</b>\n\n"
                f"Murojaat uchun: @{ADMIN_USERNAME}"
            ),
            parse_mode="HTML",
            reply_markup=home_menu()
        )
        await q.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(
            chat_id=q.message.chat_id,
            text=f"❌ <b>Screener #{sub_id} — RAD ETILDI.</b>",
            parse_mode="HTML"
        )


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Screener ticker qabul qilish."""
    mode = context.user_data.get('screener_mode')
    if not mode:
        return

    ticker = update.message.text.strip()
    user   = update.effective_user

    if mode == 'stock':
        access = await check_screener_access(user.id, "aksiya_scr")
        if not access:
            context.user_data.pop('screener_mode', None)
            return
        await update.message.reply_text(
            f"⏳ <b>{ticker.upper()}</b> tahlil qilinmoqda...",
            parse_mode="HTML"
        )
        result = await asyncio.to_thread(get_stock_data, ticker.upper())
        if result:
            await update.message.reply_text(
                result,
                parse_mode="HTML",
                reply_markup=home_menu(),
                disable_web_page_preview=True
            )
        else:
            await update.message.reply_text(
                f"❌ <b>{ticker.upper()}</b> topilmadi.\n\n"
                "Ticker to'g'ri ekanligini tekshiring.\nMasalan: AAPL, TSLA, MSFT",
                parse_mode="HTML",
                reply_markup=back_menu()
            )

    elif mode == 'crypto':
        access = await check_screener_access(user.id, "crypto_scr")
        if not access:
            context.user_data.pop('screener_mode', None)
            return
        await update.message.reply_text(
            f"⏳ <b>{ticker}</b> tahlil qilinmoqda...",
            parse_mode="HTML"
        )
        result = await asyncio.to_thread(get_crypto_data, ticker.lower())
        if result:
            await update.message.reply_text(
                result,
                parse_mode="HTML",
                reply_markup=home_menu(),
                disable_web_page_preview=True
            )
        else:
            await update.message.reply_text(
                f"❌ <b>{ticker}</b> topilmadi.\n\n"
                "CoinGecko ID ni kiriting.\nMasalan: bitcoin, ethereum, solana",
                parse_mode="HTML",
                reply_markup=back_menu()
            )


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """To'lov cheki qabul qilish."""
    # Kanal obuna to'lovi
    if context.user_data.get('waiting_payment'):
        sub_id = context.user_data.get('sub_id')
        if not sub_id:
            return

        sub = await get_subscription(sub_id)
        if not sub or sub['status'] != 'pending':
            return

        admin_ids = await get_admin_ids()
        if not admin_ids:
            await update.message.reply_text(
                "❌ <b>Administrator topilmadi.</b>\n\nKeyinroq qayta urinib ko'ring.",
                parse_mode="HTML"
            )
            return

        context.user_data['waiting_payment'] = False
        context.user_data['sub_id']          = None

        await update.message.reply_text(
            "✅ <b>Chekingiz qabul qilindi!</b>\n\n"
            "Admin tekshirgandan so'ng sizga havola yuboriladi.\n"
            "Odatda <b>5–30 daqiqa</b> ichida.",
            parse_mode="HTML"
        )

        section_name   = SECTION_NAMES.get(sub['section'], sub['section'])
        username_display = f"@{sub['username']}" if sub.get('username') else "yo'q"
        duration_label = "♾ Doimiy" if sub['duration_months'] == 0 else f"{sub['duration_months']} oy"
        caption = (
            f"💳 <b>Yangi to'lov so'rovi #{sub_id}</b>\n\n"
            f"👤 Ism: {sub['full_name']}\n"
            f"🔖 Username: {username_display}\n"
            f"🆔 ID: <code>{sub['user_id']}</code>\n"
            f"📦 Bo'lim: {section_name}\n"
            f"⏱ Muddat: {duration_label}\n"
            f"💰 Summa: ${PRICES[sub['duration_months']]}"
        )
        photo = update.message.photo[-1].file_id
        success_count = 0
        for admin_id in admin_ids:
            try:
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=photo,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=admin_menu(sub_id)
                )
                success_count += 1
            except TelegramError as e:
                print(f"[WARNING] Adminga chek yuborishda xatolik ({admin_id}): {e}")

        if success_count == 0:
            await update.message.reply_text(
                "❌ <b>Administratorga yuborishda xatolik.</b>\n\nQayta urinib ko'ring.",
                parse_mode="HTML"
            )
            context.user_data['waiting_payment'] = True
            context.user_data['sub_id']          = sub_id

    # Screener obuna to'lovi
    elif context.user_data.get('waiting_scr_payment'):
        sub_id = context.user_data.get('scr_sub_id')
        if not sub_id:
            return

        sub = await get_screener_sub(sub_id)
        if not sub or sub['status'] != 'pending':
            return

        admin_ids = await get_admin_ids()
        if not admin_ids:
            await update.message.reply_text(
                "❌ <b>Administrator topilmadi.</b>\n\nKeyinroq qayta urinib ko'ring.",
                parse_mode="HTML"
            )
            return

        context.user_data['waiting_scr_payment'] = False
        context.user_data['scr_sub_id']          = None

        await update.message.reply_text(
            "✅ <b>Chekingiz qabul qilindi!</b>\n\n"
            "Admin tekshirgandan so'ng screener faollashtiriladi.\n"
            "Odatda <b>5–30 daqiqa</b> ichida.",
            parse_mode="HTML"
        )

        section_name     = SECTION_NAMES.get(sub['section'], sub['section'])
        username_display = f"@{sub['username']}" if sub.get('username') else "yo'q"
        price            = SCREENER_PRICES[sub['section']]
        caption = (
            f"🔍 <b>Screener to'lov so'rovi #{sub_id}</b>\n\n"
            f"👤 Ism: {sub['full_name']}\n"
            f"🔖 Username: {username_display}\n"
            f"🆔 ID: <code>{sub['user_id']}</code>\n"
            f"📦 Bo'lim: {section_name}\n"
            f"⏱ Muddat: 1 yil\n"
            f"💰 Summa: ${price}"
        )
        photo = update.message.photo[-1].file_id
        success_count = 0
        for admin_id in admin_ids:
            try:
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=photo,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=admin_screener_menu(sub_id)
                )
                success_count += 1
            except TelegramError as e:
                print(f"[WARNING] Adminga screener chek yuborishda xatolik ({admin_id}): {e}")

        if success_count == 0:
            await update.message.reply_text(
                "❌ <b>Administratorga yuborishda xatolik.</b>\n\nQayta urinib ko'ring.",
                parse_mode="HTML"
            )
            context.user_data['waiting_scr_payment'] = True
            context.user_data['scr_sub_id']          = sub_id


async def check_expired(context: ContextTypes.DEFAULT_TYPE):
    """Har soatda obuna muddati tugaganlarni tekshiradi."""
    # Kanal obunalar
    expired = await get_expired_subscriptions()
    for sub in expired:
        channel_id = CHANNEL_IDS.get(sub['section'])
        if not channel_id:
            await mark_expired(sub['id'])
            continue
        try:
            await context.bot.ban_chat_member(channel_id, sub['user_id'])
            await context.bot.unban_chat_member(channel_id, sub['user_id'])
            await context.bot.send_message(
                chat_id=sub['user_id'],
                text=(
                    "⏰ <b>Obuna muddatingiz tugadi.</b>\n\n"
                    "Davom ettirish uchun /start yuboring."
                ),
                parse_mode="HTML",
                reply_markup=home_menu()
            )
            await mark_expired(sub['id'])
        except TelegramError as e:
            print(f"[WARNING] Kanaldan chiqarishda xatolik (User: {sub['user_id']}): {e}")

    # Screener obunalar
    expired_scr = await get_expired_screener_subs()
    for sub in expired_scr:
        try:
            section_name = SECTION_NAMES.get(sub['section'], sub['section'])
            await context.bot.send_message(
                chat_id=sub['user_id'],
                text=(
                    f"⏰ <b>{section_name} obunangiz tugadi.</b>\n\n"
                    "Yangilash uchun /start yuboring."
                ),
                parse_mode="HTML",
                reply_markup=home_menu()
            )
            await mark_screener_expired(sub['id'])
        except TelegramError as e:
            print(f"[WARNING] Screener expired xabar yuborishda xatolik (User: {sub['user_id']}): {e}")


# ===================== MAIN =====================
def main():
    _init_db_sync()

    persistence = PicklePersistence(filepath="bot_persistence.pickle")
    app = Application.builder().token(BOT_TOKEN).persistence(persistence).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    if app.job_queue:
        app.job_queue.run_repeating(check_expired, interval=3600, first=60)

    print("[SUCCESS] Azia Quant Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
