#!/usr/bin/env python3
"""
Azia Quant Bot — Database Module
PostgreSQL + Caching (in-memory)
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timezone, date
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# ===================== DB CONNECTION =====================
try:
    import psycopg2
    import psycopg2.extras
    USE_POSTGRES = bool(os.environ.get("DATABASE_URL"))
except ImportError:
    USE_POSTGRES = False

def get_conn():
    """Database ulanish"""
    if USE_POSTGRES:
        conn = psycopg2.connect(
            os.environ["DATABASE_URL"],
            sslmode="require",
            cursor_factory=psycopg2.extras.RealDictCursor
        )
        conn.autocommit = False
        return conn
    else:
        import sqlite3
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "azia_quant.db")
        conn = sqlite3.connect(db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

# ===================== IN-MEMORY CACHE =====================
_cache: Dict[str, Any] = {}
_cache_ttl: Dict[str, float] = {}

def cache_set(key: str, value: Any, ttl: int = 300):
    """Cache ga saqlash (ttl - sekund)"""
    import time
    _cache[key] = value
    _cache_ttl[key] = time.time() + ttl

def cache_get(key: str) -> Optional[Any]:
    """Cache dan olish"""
    import time
    if key not in _cache:
        return None
    if time.time() > _cache_ttl.get(key, 0):
        del _cache[key]
        return None
    return _cache[key]

def cache_delete(key: str):
    """Cache dan o'chirish"""
    _cache.pop(key, None)
    _cache_ttl.pop(key, None)

# ===================== JADVALLAR =====================
def init_db():
    """Jadvallar yaratish"""
    conn = get_conn()
    c = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"

    if USE_POSTGRES:
        # Users
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id    BIGINT PRIMARY KEY,
                username   TEXT DEFAULT '',
                full_name  TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        # Subscriptions
        c.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id         SERIAL PRIMARY KEY,
                user_id    BIGINT NOT NULL,
                sub_type   TEXT NOT NULL,
                duration   INT DEFAULT 0,
                price      INT DEFAULT 0,
                status     TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW(),
                expires_at TIMESTAMP
            )
        """)
        # Screener subscriptions
        c.execute("""
            CREATE TABLE IF NOT EXISTS screener_subs (
                id         SERIAL PRIMARY KEY,
                user_id    BIGINT NOT NULL,
                duration   INT DEFAULT 0,
                price      INT DEFAULT 0,
                status     TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW(),
                expires_at TIMESTAMP
            )
        """)
        # Premium subscriptions
        c.execute("""
            CREATE TABLE IF NOT EXISTS premium_subs (
                id         SERIAL PRIMARY KEY,
                user_id    BIGINT NOT NULL,
                duration   INT DEFAULT 0,
                price      INT DEFAULT 0,
                status     TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW(),
                expires_at TIMESTAMP
            )
        """)
        # Portfolio
        c.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id          SERIAL PRIMARY KEY,
                user_id     BIGINT NOT NULL,
                ticker      TEXT NOT NULL,
                ticker_type TEXT DEFAULT 'crypto',
                quantity    FLOAT DEFAULT 0,
                buy_price   FLOAT DEFAULT 0,
                added_at    TIMESTAMP DEFAULT NOW()
            )
        """)
        # Daily limits
        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_limits (
                user_id        BIGINT NOT NULL,
                limit_date     DATE NOT NULL,
                screener_count INT DEFAULT 0,
                ai_count       INT DEFAULT 0,
                PRIMARY KEY (user_id, limit_date)
            )
        """)
        # Promo codes
        c.execute("""
            CREATE TABLE IF NOT EXISTS promo_codes (
                id         SERIAL PRIMARY KEY,
                code       TEXT UNIQUE NOT NULL,
                discount   INT DEFAULT 0,
                max_uses   INT DEFAULT 100,
                used_count INT DEFAULT 0,
                is_active  BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        # Promo usage
        c.execute("""
            CREATE TABLE IF NOT EXISTS promo_usage (
                user_id    BIGINT NOT NULL,
                code       TEXT NOT NULL,
                used_at    TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (user_id, code)
            )
        """)
        # Referrals
        c.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id            SERIAL PRIMARY KEY,
                referrer_id   BIGINT NOT NULL,
                referred_id   BIGINT NOT NULL,
                reward_amount INT DEFAULT 0,
                created_at    TIMESTAMP DEFAULT NOW()
            )
        """)
        # Alerts
        c.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id          SERIAL PRIMARY KEY,
                user_id     BIGINT NOT NULL,
                ticker      TEXT NOT NULL,
                ticker_type TEXT DEFAULT 'crypto',
                alert_type  TEXT NOT NULL,
                condition   TEXT NOT NULL,
                value       FLOAT NOT NULL,
                is_active   BOOLEAN DEFAULT TRUE,
                created_at  TIMESTAMP DEFAULT NOW()
            )
        """)
        # Affiliates
        c.execute("""
            CREATE TABLE IF NOT EXISTS affiliates (
                user_id    BIGINT PRIMARY KEY,
                username   TEXT DEFAULT '',
                status     TEXT DEFAULT 'pending',
                percent    INT DEFAULT 20,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
    else:
        # SQLite
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id    INTEGER PRIMARY KEY,
                username   TEXT DEFAULT '',
                full_name  TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                sub_type   TEXT NOT NULL,
                duration   INTEGER DEFAULT 0,
                price      INTEGER DEFAULT 0,
                status     TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')),
                expires_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS screener_subs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                duration   INTEGER DEFAULT 0,
                price      INTEGER DEFAULT 0,
                status     TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')),
                expires_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS premium_subs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                duration   INTEGER DEFAULT 0,
                price      INTEGER DEFAULT 0,
                status     TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')),
                expires_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                ticker      TEXT NOT NULL,
                ticker_type TEXT DEFAULT 'crypto',
                quantity    REAL DEFAULT 0,
                buy_price   REAL DEFAULT 0,
                added_at    TEXT DEFAULT (datetime('now'))
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_limits (
                user_id        INTEGER NOT NULL,
                limit_date     TEXT NOT NULL,
                screener_count INTEGER DEFAULT 0,
                ai_count       INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, limit_date)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS promo_codes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                code       TEXT UNIQUE NOT NULL,
                discount   INTEGER DEFAULT 0,
                max_uses   INTEGER DEFAULT 100,
                used_count INTEGER DEFAULT 0,
                is_active  INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS promo_usage (
                user_id INTEGER NOT NULL,
                code    TEXT NOT NULL,
                used_at TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (user_id, code)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id   INTEGER NOT NULL,
                referred_id   INTEGER NOT NULL,
                reward_amount INTEGER DEFAULT 0,
                created_at    TEXT DEFAULT (datetime('now'))
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                ticker      TEXT NOT NULL,
                ticker_type TEXT DEFAULT 'crypto',
                alert_type  TEXT NOT NULL,
                condition   TEXT NOT NULL,
                value       REAL NOT NULL,
                is_active   INTEGER DEFAULT 1,
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS affiliates (
                user_id    INTEGER PRIMARY KEY,
                username   TEXT DEFAULT '',
                status     TEXT DEFAULT 'pending',
                percent    INTEGER DEFAULT 20,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

    conn.commit()
    conn.close()
    logger.info("[DB] Jadvallar muvaffaqiyatli yaratildi!")

# ===================== ASYNC WRAPPER =====================
async def run_in_executor(func, *args):
    """Sync funksiyani async da ishlatish"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args)

# ===================== USER =====================
def _save_user_sync(user_id: int, username: str, full_name: str):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""
            INSERT INTO users (user_id, username, full_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
            username=EXCLUDED.username, full_name=EXCLUDED.full_name
        """, (user_id, username or "", full_name or ""))
    else:
        c.execute("SELECT created_at FROM users WHERE user_id=?", (user_id,))
        if c.fetchone():
            c.execute("UPDATE users SET username=?, full_name=? WHERE user_id=?",
                     (username or "", full_name or "", user_id))
        else:
            c.execute("INSERT INTO users (user_id, username, full_name) VALUES (?,?,?)",
                     (user_id, username or "", full_name or ""))
    conn.commit()
    conn.close()

async def save_user(user_id: int, username: str, full_name: str):
    await run_in_executor(_save_user_sync, user_id, username, full_name)

def _get_all_users_sync() -> List[Dict]:
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("SELECT user_id, username, full_name, created_at FROM users ORDER BY created_at DESC")
    else:
        c.execute("SELECT user_id, username, full_name, created_at FROM users ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

async def get_all_users() -> List[Dict]:
    return await run_in_executor(_get_all_users_sync)

async def get_all_bot_users() -> List[Dict]:
    return await get_all_users()

# ===================== DAILY LIMITS =====================
def _get_daily_limit_sync(user_id: int) -> Dict:
    today = str(date.today())
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("SELECT * FROM daily_limits WHERE user_id=%s AND limit_date=%s", (user_id, today))
    else:
        c.execute("SELECT * FROM daily_limits WHERE user_id=? AND limit_date=?", (user_id, today))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"user_id": user_id, "limit_date": today, "screener_count": 0, "ai_count": 0}

async def get_daily_limit(user_id: int) -> Dict:
    return await run_in_executor(_get_daily_limit_sync, user_id)

def _increment_daily_limit_sync(user_id: int, limit_type: str):
    """limit_type: 'screener' yoki 'ai'"""
    today = str(date.today())
    conn = get_conn()
    c = conn.cursor()
    col = "screener_count" if limit_type == "screener" else "ai_count"
    if USE_POSTGRES:
        c.execute(f"""
            INSERT INTO daily_limits (user_id, limit_date, {col})
            VALUES (%s, %s, 1)
            ON CONFLICT (user_id, limit_date) DO UPDATE SET
            {col} = daily_limits.{col} + 1
        """, (user_id, today))
    else:
        existing = _get_daily_limit_sync(user_id)
        if existing.get("screener_count") == 0 and existing.get("ai_count") == 0:
            c.execute(f"INSERT OR IGNORE INTO daily_limits (user_id, limit_date) VALUES (?,?)",
                     (user_id, today))
        c.execute(f"UPDATE daily_limits SET {col}={col}+1 WHERE user_id=? AND limit_date=?",
                 (user_id, today))
    conn.commit()
    conn.close()

async def increment_daily_limit(user_id: int, limit_type: str):
    await run_in_executor(_increment_daily_limit_sync, user_id, limit_type)

async def check_daily_limit(user_id: int, limit_type: str, max_count: int) -> bool:
    """True = limit oshib ketmagan (ishlatsa bo'ladi)"""
    limits = await get_daily_limit(user_id)
    col = "screener_count" if limit_type == "screener" else "ai_count"
    return limits.get(col, 0) < max_count

# ===================== SUBSCRIPTIONS =====================
def _save_subscription_sync(user_id, username, full_name, sub_type, duration) -> int:
    from config import SIGNAL_PRICES, SCREENER_PRICES, CRYPTO_EDU_PRICE, STOCK_EDU_PRICE, PREMIUM_PRICE
    price_map = {
        "signals": SIGNAL_PRICES.get(duration, 0),
        "onchain_screener": SCREENER_PRICES.get(duration, 0),
        "crypto_edu": CRYPTO_EDU_PRICE,
        "stock_edu": STOCK_EDU_PRICE,
        "premium": PREMIUM_PRICE,
    }
    price = price_map.get(sub_type, 0)
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""
            INSERT INTO subscriptions (user_id, sub_type, duration, price)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (user_id, sub_type, duration, price))
        sub_id = c.fetchone()[0]
    else:
        c.execute("""
            INSERT INTO subscriptions (user_id, sub_type, duration, price)
            VALUES (?,?,?,?)
        """, (user_id, sub_type, duration, price))
        sub_id = c.lastrowid
    conn.commit()
    conn.close()
    return sub_id

async def save_subscription(user_id, username, full_name, sub_type, duration) -> int:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _save_subscription_sync,
                                       user_id, username, full_name, sub_type, duration)

def _approve_subscription_sync(sub_id: int, months: int):
    from datetime import timedelta
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now(timezone.utc)
    if months == 0:
        expires = None
    else:
        expires = now + timedelta(days=30 * months)

    if USE_POSTGRES:
        c.execute("""
            UPDATE subscriptions SET status='active', expires_at=%s WHERE id=%s
        """, (expires, sub_id))
    else:
        exp_str = expires.isoformat() if expires else None
        c.execute("UPDATE subscriptions SET status='active', expires_at=? WHERE id=?",
                 (exp_str, sub_id))
    conn.commit()
    conn.close()

async def approve_subscription(sub_id: int, months: int):
    await run_in_executor(_approve_subscription_sync, sub_id, months)

def _check_channel_access_sync(user_id: int, sub_type: str) -> bool:
    cache_key = f"access_{user_id}_{sub_type}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    conn = get_conn()
    c = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    if USE_POSTGRES:
        c.execute("""
            SELECT id FROM subscriptions
            WHERE user_id=%s AND sub_type=%s AND status='active'
            AND (expires_at IS NULL OR expires_at > NOW())
        """, (user_id, sub_type))
    else:
        c.execute("""
            SELECT id FROM subscriptions
            WHERE user_id=? AND sub_type=? AND status='active'
            AND (expires_at IS NULL OR expires_at > ?)
        """, (user_id, sub_type, now))
    result = bool(c.fetchone())
    conn.close()
    cache_set(cache_key, result, ttl=60)
    return result

async def check_channel_access(user_id: int, sub_type: str) -> bool:
    return await run_in_executor(_check_channel_access_sync, user_id, sub_type)

# ===================== SCREENER SUBS =====================
def _save_screener_sub_sync(user_id, username, full_name, duration) -> int:
    from config import SCREENER_PRICES
    price = SCREENER_PRICES.get(duration, 0)
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""
            INSERT INTO screener_subs (user_id, duration, price)
            VALUES (%s, %s, %s) RETURNING id
        """, (user_id, duration, price))
        sub_id = c.fetchone()[0]
    else:
        c.execute("INSERT INTO screener_subs (user_id, duration, price) VALUES (?,?,?)",
                 (user_id, duration, price))
        sub_id = c.lastrowid
    conn.commit()
    conn.close()
    return sub_id

async def save_screener_sub(user_id, username, full_name, duration) -> int:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _save_screener_sub_sync,
                                       user_id, username, full_name, duration)

def _check_screener_access_sync(user_id: int) -> bool:
    cache_key = f"screener_{user_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    conn = get_conn()
    c = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    if USE_POSTGRES:
        c.execute("""
            SELECT id FROM screener_subs
            WHERE user_id=%s AND status='active'
            AND (expires_at IS NULL OR expires_at > NOW())
        """, (user_id,))
    else:
        c.execute("""
            SELECT id FROM screener_subs
            WHERE user_id=? AND status='active'
            AND (expires_at IS NULL OR expires_at > ?)
        """, (user_id, now))
    result = bool(c.fetchone())
    conn.close()
    cache_set(cache_key, result, ttl=60)
    return result

async def check_screener_access(user_id: int) -> bool:
    return await run_in_executor(_check_screener_access_sync, user_id)

def _approve_screener_sub_sync(sub_id: int, months: int):
    from datetime import timedelta
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now(timezone.utc)
    expires = None if months == 0 else now + timedelta(days=30 * months)
    if USE_POSTGRES:
        c.execute("UPDATE screener_subs SET status='active', expires_at=%s WHERE id=%s",
                 (expires, sub_id))
    else:
        c.execute("UPDATE screener_subs SET status='active', expires_at=? WHERE id=?",
                 (expires.isoformat() if expires else None, sub_id))
    conn.commit()
    conn.close()

async def approve_screener_sub(sub_id: int, months: int):
    await run_in_executor(_approve_screener_sub_sync, sub_id, months)

def _reject_screener_sub_sync(sub_id: int):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("UPDATE screener_subs SET status='rejected' WHERE id=%s", (sub_id,))
    else:
        c.execute("UPDATE screener_subs SET status='rejected' WHERE id=?", (sub_id,))
    conn.commit()
    conn.close()

async def reject_screener_sub(sub_id: int):
    await run_in_executor(_reject_screener_sub_sync, sub_id)

# ===================== PREMIUM SUBS =====================
def _save_premium_sub_sync(user_id, username, full_name) -> int:
    from config import PREMIUM_PRICE
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""
            INSERT INTO premium_subs (user_id, duration, price)
            VALUES (%s, 0, %s) RETURNING id
        """, (user_id, PREMIUM_PRICE))
        sub_id = c.fetchone()[0]
    else:
        c.execute("INSERT INTO premium_subs (user_id, duration, price) VALUES (?,0,?)",
                 (user_id, PREMIUM_PRICE))
        sub_id = c.lastrowid
    conn.commit()
    conn.close()
    return sub_id

async def save_premium_sub(user_id, username, full_name) -> int:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _save_premium_sub_sync, user_id, username, full_name)

def _check_premium_access_sync(user_id: int) -> bool:
    cache_key = f"premium_{user_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    conn = get_conn()
    c = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    if USE_POSTGRES:
        c.execute("""
            SELECT id FROM premium_subs
            WHERE user_id=%s AND status='active'
            AND (expires_at IS NULL OR expires_at > NOW())
        """, (user_id,))
    else:
        c.execute("""
            SELECT id FROM premium_subs
            WHERE user_id=? AND status='active'
            AND (expires_at IS NULL OR expires_at > ?)
        """, (user_id, now))
    result = bool(c.fetchone())
    conn.close()
    cache_set(cache_key, result, ttl=60)
    return result

async def check_premium_access(user_id: int) -> bool:
    return await run_in_executor(_check_premium_access_sync, user_id)

def _approve_premium_sub_sync(sub_id: int):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("UPDATE premium_subs SET status='active' WHERE id=%s", (sub_id,))
    else:
        c.execute("UPDATE premium_subs SET status='active' WHERE id=?", (sub_id,))
    conn.commit()
    conn.close()

async def approve_premium_sub(sub_id: int):
    await run_in_executor(_approve_premium_sub_sync, sub_id)

def _reject_premium_sub_sync(sub_id: int):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("UPDATE premium_subs SET status='rejected' WHERE id=%s", (sub_id,))
    else:
        c.execute("UPDATE premium_subs SET status='rejected' WHERE id=?", (sub_id,))
    conn.commit()
    conn.close()

async def reject_premium_sub(sub_id: int):
    await run_in_executor(_reject_premium_sub_sync, sub_id)

# ===================== PORTFOLIO =====================
def _get_portfolio_sync(user_id: int) -> List[Dict]:
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("SELECT * FROM portfolio WHERE user_id=%s ORDER BY added_at DESC", (user_id,))
    else:
        c.execute("SELECT * FROM portfolio WHERE user_id=? ORDER BY added_at DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

async def get_portfolio(user_id: int) -> List[Dict]:
    return await run_in_executor(_get_portfolio_sync, user_id)

def _add_portfolio_sync(user_id, ticker, ticker_type, quantity, buy_price):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""
            INSERT INTO portfolio (user_id, ticker, ticker_type, quantity, buy_price)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, ticker.upper(), ticker_type, quantity, buy_price))
    else:
        c.execute("""
            INSERT INTO portfolio (user_id, ticker, ticker_type, quantity, buy_price)
            VALUES (?,?,?,?,?)
        """, (user_id, ticker.upper(), ticker_type, quantity, buy_price))
    conn.commit()
    conn.close()

async def add_portfolio(user_id, ticker, ticker_type, quantity, buy_price):
    await run_in_executor(_add_portfolio_sync, user_id, ticker, ticker_type, quantity, buy_price)

def _delete_portfolio_sync(item_id: int, user_id: int):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("DELETE FROM portfolio WHERE id=%s AND user_id=%s", (item_id, user_id))
    else:
        c.execute("DELETE FROM portfolio WHERE id=? AND user_id=?", (item_id, user_id))
    conn.commit()
    conn.close()

async def delete_portfolio(item_id: int, user_id: int):
    await run_in_executor(_delete_portfolio_sync, item_id, user_id)

# ===================== ALERTS =====================
def _get_user_alerts_sync(user_id: int) -> List[Dict]:
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("SELECT * FROM alerts WHERE user_id=%s AND is_active=TRUE", (user_id,))
    else:
        c.execute("SELECT * FROM alerts WHERE user_id=? AND is_active=1", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

async def get_user_alerts(user_id: int) -> List[Dict]:
    return await run_in_executor(_get_user_alerts_sync, user_id)

def _save_alert_sync(user_id, ticker, ticker_type, alert_type, condition, value) -> int:
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""
            INSERT INTO alerts (user_id, ticker, ticker_type, alert_type, condition, value)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (user_id, ticker, ticker_type, alert_type, condition, value))
        alert_id = c.fetchone()[0]
    else:
        c.execute("""
            INSERT INTO alerts (user_id, ticker, ticker_type, alert_type, condition, value)
            VALUES (?,?,?,?,?,?)
        """, (user_id, ticker, ticker_type, alert_type, condition, value))
        alert_id = c.lastrowid
    conn.commit()
    conn.close()
    return alert_id

async def save_alert(user_id, ticker, ticker_type, alert_type, condition, value) -> int:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _save_alert_sync,
                                       user_id, ticker, ticker_type, alert_type, condition, value)

def _delete_alert_sync(alert_id: int, user_id: int):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("UPDATE alerts SET is_active=FALSE WHERE id=%s AND user_id=%s", (alert_id, user_id))
    else:
        c.execute("UPDATE alerts SET is_active=0 WHERE id=? AND user_id=?", (alert_id, user_id))
    conn.commit()
    conn.close()

async def delete_alert(alert_id: int, user_id: int):
    await run_in_executor(_delete_alert_sync, alert_id, user_id)

def _get_all_active_alerts_sync() -> List[Dict]:
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("SELECT * FROM alerts WHERE is_active=TRUE")
    else:
        c.execute("SELECT * FROM alerts WHERE is_active=1")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

async def get_all_active_alerts() -> List[Dict]:
    return await run_in_executor(_get_all_active_alerts_sync)

# ===================== PROMO CODES =====================
def _check_promo_sync(code: str, user_id: int) -> Optional[Dict]:
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""
            SELECT * FROM promo_codes
            WHERE code=%s AND is_active=TRUE AND used_count < max_uses
        """, (code.upper(),))
    else:
        c.execute("""
            SELECT * FROM promo_codes
            WHERE code=? AND is_active=1 AND used_count < max_uses
        """, (code.upper(),))
    promo = c.fetchone()
    if not promo:
        conn.close()
        return None
    promo = dict(promo)
    if USE_POSTGRES:
        c.execute("SELECT 1 FROM promo_usage WHERE user_id=%s AND code=%s", (user_id, code.upper()))
    else:
        c.execute("SELECT 1 FROM promo_usage WHERE user_id=? AND code=?", (user_id, code.upper()))
    if c.fetchone():
        conn.close()
        return None
    conn.close()
    return promo

async def check_promo(code: str, user_id: int) -> Optional[Dict]:
    return await run_in_executor(_check_promo_sync, code, user_id)

def _use_promo_sync(code: str, user_id: int):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("UPDATE promo_codes SET used_count=used_count+1 WHERE code=%s", (code.upper(),))
        c.execute("INSERT INTO promo_usage (user_id, code) VALUES (%s, %s)", (user_id, code.upper()))
    else:
        c.execute("UPDATE promo_codes SET used_count=used_count+1 WHERE code=?", (code.upper(),))
        c.execute("INSERT INTO promo_usage (user_id, code) VALUES (?,?)", (user_id, code.upper()))
    conn.commit()
    conn.close()

async def use_promo(code: str, user_id: int):
    await run_in_executor(_use_promo_sync, code, user_id)

def _create_promo_sync(code: str, discount: int, max_uses: int):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""
            INSERT INTO promo_codes (code, discount, max_uses)
            VALUES (%s, %s, %s) ON CONFLICT (code) DO NOTHING
        """, (code.upper(), discount, max_uses))
    else:
        c.execute("""
            INSERT OR IGNORE INTO promo_codes (code, discount, max_uses)
            VALUES (?,?,?)
        """, (code.upper(), discount, max_uses))
    conn.commit()
    conn.close()

async def create_promo(code: str, discount: int, max_uses: int):
    await run_in_executor(_create_promo_sync, code, discount, max_uses)

def _get_all_promos_sync() -> List[Dict]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM promo_codes ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

async def get_all_promos() -> List[Dict]:
    return await run_in_executor(_get_all_promos_sync)

# ===================== REFERRALS =====================
def _save_referral_sync(referrer_id: int, referred_id: int):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""
            INSERT INTO referrals (referrer_id, referred_id)
            VALUES (%s, %s) ON CONFLICT DO NOTHING
        """, (referrer_id, referred_id))
    else:
        c.execute("""
            INSERT OR IGNORE INTO referrals (referrer_id, referred_id)
            VALUES (?,?)
        """, (referrer_id, referred_id))
    conn.commit()
    conn.close()

async def save_referral(referrer_id: int, referred_id: int):
    await run_in_executor(_save_referral_sync, referrer_id, referred_id)

def _get_referral_stats_sync(user_id: int) -> Dict:
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id=%s", (user_id,))
    else:
        c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (user_id,))
    count = c.fetchone()[0]
    if USE_POSTGRES:
        c.execute("SELECT COALESCE(SUM(reward_amount),0) FROM referrals WHERE referrer_id=%s", (user_id,))
    else:
        c.execute("SELECT COALESCE(SUM(reward_amount),0) FROM referrals WHERE referrer_id=?", (user_id,))
    total = c.fetchone()[0]
    conn.close()
    return {"count": count, "total_reward": total}

async def get_referral_stats(user_id: int) -> Dict:
    return await run_in_executor(_get_referral_stats_sync, user_id)

async def update_referral_reward(referrer_id: int, referred_id: int, amount: int):
    def _sync():
        conn = get_conn()
        c = conn.cursor()
        if USE_POSTGRES:
            c.execute("""
                UPDATE referrals SET reward_amount=%s
                WHERE referrer_id=%s AND referred_id=%s
            """, (amount, referrer_id, referred_id))
        else:
            c.execute("""
                UPDATE referrals SET reward_amount=?
                WHERE referrer_id=? AND referred_id=?
            """, (amount, referrer_id, referred_id))
        conn.commit()
        conn.close()
    await run_in_executor(_sync)

# ===================== AFFILIATES =====================
def _save_affiliate_sync(user_id: int, username: str):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""
            INSERT INTO affiliates (user_id, username)
            VALUES (%s, %s) ON CONFLICT (user_id) DO NOTHING
        """, (user_id, username or ""))
    else:
        c.execute("""
            INSERT OR IGNORE INTO affiliates (user_id, username)
            VALUES (?,?)
        """, (user_id, username or ""))
    conn.commit()
    conn.close()

async def save_affiliate(user_id: int, username: str):
    await run_in_executor(_save_affiliate_sync, user_id, username)

def _get_pending_affiliates_sync() -> List[Dict]:
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("SELECT * FROM affiliates WHERE status='pending'")
    else:
        c.execute("SELECT * FROM affiliates WHERE status='pending'")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

async def get_pending_affiliates() -> List[Dict]:
    return await run_in_executor(_get_pending_affiliates_sync)

def _approve_affiliate_sync(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("UPDATE affiliates SET status='active' WHERE user_id=%s", (user_id,))
    else:
        c.execute("UPDATE affiliates SET status='active' WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

async def approve_affiliate(user_id: int):
    await run_in_executor(_approve_affiliate_sync, user_id)

# ===================== STATISTICS =====================
def _get_stats_sync() -> Dict:
    conn = get_conn()
    c = conn.cursor()
    stats = {}
    tables = ["users", "subscriptions", "screener_subs", "premium_subs"]
    for table in tables:
        c.execute(f"SELECT COUNT(*) FROM {table}")
        stats[f"total_{table}"] = c.fetchone()[0]
    if USE_POSTGRES:
        c.execute("SELECT COUNT(*) FROM subscriptions WHERE status='active'")
    else:
        c.execute("SELECT COUNT(*) FROM subscriptions WHERE status='active'")
    stats["active_subs"] = c.fetchone()[0]
    conn.close()
    return stats

async def get_stats() -> Dict:
    return await run_in_executor(_get_stats_sync)

def _get_non_subscribers_sync() -> List[Dict]:
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""
            SELECT u.* FROM users u
            WHERE NOT EXISTS (
                SELECT 1 FROM subscriptions s
                WHERE s.user_id = u.user_id AND s.status = 'active'
            )
            AND NOT EXISTS (
                SELECT 1 FROM screener_subs s
                WHERE s.user_id = u.user_id AND s.status = 'active'
            )
            AND NOT EXISTS (
                SELECT 1 FROM premium_subs s
                WHERE s.user_id = u.user_id AND s.status = 'active'
            )
        """)
    else:
        c.execute("""
            SELECT u.* FROM users u
            WHERE NOT EXISTS (
                SELECT 1 FROM subscriptions s
                WHERE s.user_id = u.user_id AND s.status = 'active'
            )
            AND NOT EXISTS (
                SELECT 1 FROM screener_subs s
                WHERE s.user_id = u.user_id AND s.status = 'active'
            )
            AND NOT EXISTS (
                SELECT 1 FROM premium_subs s
                WHERE s.user_id = u.user_id AND s.status = 'active'
            )
        """)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

async def get_non_subscribers() -> List[Dict]:
    return await run_in_executor(_get_non_subscribers_sync)

def _cancel_user_subscription_sync(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    if USE_POSTGRES:
        c.execute("UPDATE subscriptions SET status='cancelled', expires_at=NOW() WHERE user_id=%s", (user_id,))
        c.execute("UPDATE screener_subs SET status='cancelled', expires_at=NOW() WHERE user_id=%s", (user_id,))
        c.execute("UPDATE premium_subs SET status='cancelled', expires_at=NOW() WHERE user_id=%s", (user_id,))
    else:
        c.execute("UPDATE subscriptions SET status='cancelled', expires_at=? WHERE user_id=?", (now, user_id))
        c.execute("UPDATE screener_subs SET status='cancelled', expires_at=? WHERE user_id=?", (now, user_id))
        c.execute("UPDATE premium_subs SET status='cancelled', expires_at=? WHERE user_id=?", (now, user_id))
    conn.commit()
    conn.close()
    # Cache tozalash
    cache_delete(f"access_{user_id}_signals")
    cache_delete(f"screener_{user_id}")
    cache_delete(f"premium_{user_id}")

async def cancel_user_subscription(user_id: int):
    await run_in_executor(_cancel_user_subscription_sync, user_id)

def _get_expired_subscriptions_sync() -> List[Dict]:
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    if USE_POSTGRES:
        c.execute("""
            SELECT user_id, sub_type FROM subscriptions
            WHERE status='active' AND expires_at IS NOT NULL AND expires_at < NOW()
        """)
    else:
        c.execute("""
            SELECT user_id, sub_type FROM subscriptions
            WHERE status='active' AND expires_at IS NOT NULL AND expires_at < ?
        """, (now,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

async def get_expired_subscriptions() -> List[Dict]:
    return await run_in_executor(_get_expired_subscriptions_sync)

def _mark_expired_sync(user_id: int, sub_type: str):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""
            UPDATE subscriptions SET status='expired'
            WHERE user_id=%s AND sub_type=%s AND status='active'
        """, (user_id, sub_type))
    else:
        c.execute("""
            UPDATE subscriptions SET status='expired'
            WHERE user_id=? AND sub_type=? AND status='active'
        """, (user_id, sub_type))
    conn.commit()
    conn.close()

async def mark_expired(user_id: int, sub_type: str):
    await run_in_executor(_mark_expired_sync, user_id, sub_type)

def _get_expired_screener_subs_sync() -> List[Dict]:
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    if USE_POSTGRES:
        c.execute("""
            SELECT user_id FROM screener_subs
            WHERE status='active' AND expires_at IS NOT NULL AND expires_at < NOW()
        """)
    else:
        c.execute("""
            SELECT user_id FROM screener_subs
            WHERE status='active' AND expires_at IS NOT NULL AND expires_at < ?
        """, (now,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

async def get_expired_screener_subs() -> List[Dict]:
    return await run_in_executor(_get_expired_screener_subs_sync)

def _mark_screener_expired_sync(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("UPDATE screener_subs SET status='expired' WHERE user_id=%s AND status='active'", (user_id,))
    else:
        c.execute("UPDATE screener_subs SET status='expired' WHERE user_id=? AND status='active'", (user_id,))
    conn.commit()
    conn.close()
    cache_delete(f"screener_{user_id}")

async def mark_screener_expired(user_id: int):
    await run_in_executor(_mark_screener_expired_sync, user_id)

def _reject_subscription_sync(sub_id: int):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("UPDATE subscriptions SET status='rejected' WHERE id=%s", (sub_id,))
    else:
        c.execute("UPDATE subscriptions SET status='rejected' WHERE id=?", (sub_id,))
    conn.commit()
    conn.close()

async def reject_subscription(sub_id: int):
    await run_in_executor(_reject_subscription_sync, sub_id)
