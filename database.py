#!/usr/bin/env python3
"""
Azia Quant Bot — Database Module
PostgreSQL (Railway) yoki SQLite (lokal) support
"""

import os
import asyncio
from datetime import datetime, timedelta

# PostgreSQL yoki SQLite tanlash
DATABASE_URL = os.environ.get("DATABASE_URL", "")

if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
    # PostgreSQL
    import psycopg2
    import psycopg2.extras
    USE_POSTGRES = True
    print("[DB] PostgreSQL ishlatilmoqda")
else:
    # SQLite (lokal test uchun)
    import sqlite3
    USE_POSTGRES = False
    DB_PATH = "azia_quant.db"
    print("[DB] SQLite ishlatilmoqda")


# ===================== ULANISH =====================

def get_conn():
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        return conn
    else:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn


def adapt_query(query):
    """SQLite %s -> PostgreSQL $1, $2 ..."""
    if USE_POSTGRES:
        return query
    # SQLite uchun %s o'rniga ? ishlatiladi
    return query.replace("%s", "?")


# ===================== INIT =====================

def _init_db_sync():
    conn = get_conn()
    c = conn.cursor()

    if USE_POSTGRES:
        # PostgreSQL jadvallar
        c.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
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
        c.execute("""
            CREATE TABLE IF NOT EXISTS screener_subscriptions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                username TEXT,
                full_name TEXT,
                duration_months INTEGER NOT NULL,
                start_date TEXT,
                end_date TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS premium_subscriptions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                username TEXT,
                full_name TEXT,
                start_date TEXT,
                end_date TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id BIGINT PRIMARY KEY,
                chat_id BIGINT NOT NULL UNIQUE
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                ticker TEXT NOT NULL,
                ticker_type TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                condition TEXT NOT NULL,
                value REAL NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                ticker TEXT NOT NULL,
                ticker_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                buy_price REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id SERIAL PRIMARY KEY,
                referrer_id BIGINT NOT NULL,
                referred_id BIGINT NOT NULL,
                referral_code TEXT NOT NULL,
                reward_amount REAL DEFAULT 0,
                reward_paid INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS affiliates (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                username TEXT,
                full_name TEXT,
                affiliate_code TEXT UNIQUE,
                total_referrals INTEGER DEFAULT 0,
                total_earned REAL DEFAULT 0,
                pending_amount REAL DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS affiliate_earnings (
                id SERIAL PRIMARY KEY,
                affiliate_id BIGINT NOT NULL,
                referred_user_id BIGINT NOT NULL,
                section TEXT NOT NULL,
                amount REAL NOT NULL,
                paid INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS free_usage (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL UNIQUE,
                last_date TEXT,
                count INTEGER DEFAULT 0
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS promo_codes (
                id SERIAL PRIMARY KEY,
                code TEXT UNIQUE NOT NULL,
                discount_pct INTEGER NOT NULL,
                max_uses INTEGER DEFAULT 1,
                used_count INTEGER DEFAULT 0,
                section TEXT,
                expires_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS onchain_signals (
                id SERIAL PRIMARY KEY,
                signal_type TEXT NOT NULL,
                coin TEXT NOT NULL,
                data TEXT NOT NULL,
                sent_to_channel INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                ticker TEXT NOT NULL,
                ticker_type TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                ticker TEXT NOT NULL,
                ticker_type TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL UNIQUE,
                username TEXT,
                full_name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        # SQLite jadvallar
        c.execute("""CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, username TEXT, full_name TEXT,
            section TEXT NOT NULL, duration_months INTEGER NOT NULL,
            start_date TEXT, end_date TEXT, status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS screener_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, username TEXT, full_name TEXT,
            duration_months INTEGER NOT NULL, start_date TEXT, end_date TEXT,
            status TEXT DEFAULT 'pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS premium_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, username TEXT, full_name TEXT,
            start_date TEXT, end_date TEXT, status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL UNIQUE)""")
        c.execute("""CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, ticker TEXT NOT NULL, ticker_type TEXT NOT NULL,
            alert_type TEXT NOT NULL, condition TEXT NOT NULL, value REAL NOT NULL,
            status TEXT DEFAULT 'active', created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, ticker TEXT NOT NULL, ticker_type TEXT NOT NULL,
            quantity REAL NOT NULL, buy_price REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL, referred_id INTEGER NOT NULL,
            referral_code TEXT NOT NULL, reward_amount REAL DEFAULT 0,
            reward_paid INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS affiliates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, username TEXT, full_name TEXT,
            affiliate_code TEXT UNIQUE, total_referrals INTEGER DEFAULT 0,
            total_earned REAL DEFAULT 0, pending_amount REAL DEFAULT 0,
            status TEXT DEFAULT 'pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS affiliate_earnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            affiliate_id INTEGER NOT NULL, referred_user_id INTEGER NOT NULL,
            section TEXT NOT NULL, amount REAL NOT NULL, paid INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS free_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE, last_date TEXT, count INTEGER DEFAULT 0)""")
        c.execute("""CREATE TABLE IF NOT EXISTS promo_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL, discount_pct INTEGER NOT NULL,
            max_uses INTEGER DEFAULT 1, used_count INTEGER DEFAULT 0,
            section TEXT, expires_at TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS onchain_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_type TEXT NOT NULL, coin TEXT NOT NULL, data TEXT NOT NULL,
            sent_to_channel INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, ticker TEXT NOT NULL, ticker_type TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, ticker TEXT NOT NULL, ticker_type TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE, username TEXT, full_name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")

    conn.commit()
    conn.close()
    print("[DB] Jadvallar muvaffaqiyatli yaratildi!")


def _row_to_dict(row):
    if row is None:
        return None
    if USE_POSTGRES:
        return dict(row)
    else:
        return dict(row)


# ===================== SUBSCRIPTIONS =====================

def _save_subscription_sync(user_id, username, full_name, section, duration):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""INSERT INTO subscriptions (user_id, username, full_name, section, duration_months)
            VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (user_id, username or "", full_name or "Noma'lum", section, duration))
        sub_id = c.fetchone()['id']
    else:
        c.execute("""INSERT INTO subscriptions (user_id, username, full_name, section, duration_months)
            VALUES (?, ?, ?, ?, ?)""",
            (user_id, username or "", full_name or "Noma'lum", section, duration))
        sub_id = c.lastrowid
    conn.commit()
    conn.close()
    return sub_id


def _get_subscription_sync(sub_id):
    conn = get_conn()
    c = conn.cursor()
    q = "SELECT * FROM subscriptions WHERE id=%s" if USE_POSTGRES else "SELECT * FROM subscriptions WHERE id=?"
    c.execute(q, (sub_id,))
    row = c.fetchone()
    conn.close()
    return _row_to_dict(row)


def _approve_subscription_sync(sub_id, duration_months):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now()
    if duration_months == 0:
        end_date = None
    elif duration_months == 6:
        end_date = (now + timedelta(days=180)).isoformat()
    elif duration_months == 12:
        end_date = (now + timedelta(days=365)).isoformat()
    else:
        end_date = (now + timedelta(days=30 * duration_months)).isoformat()
    q = "UPDATE subscriptions SET status='approved', start_date=%s, end_date=%s WHERE id=%s" if USE_POSTGRES else \
        "UPDATE subscriptions SET status='approved', start_date=?, end_date=? WHERE id=?"
    c.execute(q, (now.isoformat(), end_date, sub_id))
    conn.commit()
    conn.close()


def _reject_subscription_sync(sub_id):
    conn = get_conn()
    c = conn.cursor()
    q = "UPDATE subscriptions SET status='rejected' WHERE id=%s" if USE_POSTGRES else \
        "UPDATE subscriptions SET status='rejected' WHERE id=?"
    c.execute(q, (sub_id,))
    conn.commit()
    conn.close()


def _check_channel_access_sync(user_id, section):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    q = """SELECT * FROM subscriptions WHERE user_id=%s AND section=%s AND status='approved'
        AND (end_date IS NULL OR end_date > %s)""" if USE_POSTGRES else \
        """SELECT * FROM subscriptions WHERE user_id=? AND section=? AND status='approved'
        AND (end_date IS NULL OR end_date > ?)"""
    c.execute(q, (user_id, section, now))
    row = c.fetchone()
    conn.close()
    return _row_to_dict(row)


def _get_expired_subscriptions_sync():
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    q = """SELECT * FROM subscriptions WHERE status='approved'
        AND end_date IS NOT NULL AND end_date < %s""" if USE_POSTGRES else \
        """SELECT * FROM subscriptions WHERE status='approved'
        AND end_date IS NOT NULL AND end_date < ?"""
    c.execute(q, (now,))
    rows = c.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def _mark_expired_sync(sub_id):
    conn = get_conn()
    c = conn.cursor()
    q = "UPDATE subscriptions SET status='expired' WHERE id=%s" if USE_POSTGRES else \
        "UPDATE subscriptions SET status='expired' WHERE id=?"
    c.execute(q, (sub_id,))
    conn.commit()
    conn.close()


# ===================== SCREENER SUBSCRIPTIONS =====================

def _save_screener_sub_sync(user_id, username, full_name, duration):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""INSERT INTO screener_subscriptions (user_id, username, full_name, duration_months)
            VALUES (%s, %s, %s, %s) RETURNING id""",
            (user_id, username or "", full_name or "Noma'lum", duration))
        sub_id = c.fetchone()['id']
    else:
        c.execute("""INSERT INTO screener_subscriptions (user_id, username, full_name, duration_months)
            VALUES (?, ?, ?, ?)""",
            (user_id, username or "", full_name or "Noma'lum", duration))
        sub_id = c.lastrowid
    conn.commit()
    conn.close()
    return sub_id


def _get_screener_sub_sync(sub_id):
    conn = get_conn()
    c = conn.cursor()
    q = "SELECT * FROM screener_subscriptions WHERE id=%s" if USE_POSTGRES else \
        "SELECT * FROM screener_subscriptions WHERE id=?"
    c.execute(q, (sub_id,))
    row = c.fetchone()
    conn.close()
    return _row_to_dict(row)


def _approve_screener_sub_sync(sub_id, duration_months):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now()
    if duration_months == 0:
        end_date = None
    elif duration_months == 6:
        end_date = (now + timedelta(days=180)).isoformat()
    else:
        end_date = (now + timedelta(days=365)).isoformat()
    q = "UPDATE screener_subscriptions SET status='approved', start_date=%s, end_date=%s WHERE id=%s" if USE_POSTGRES else \
        "UPDATE screener_subscriptions SET status='approved', start_date=?, end_date=? WHERE id=?"
    c.execute(q, (now.isoformat(), end_date, sub_id))
    conn.commit()
    conn.close()


def _reject_screener_sub_sync(sub_id):
    conn = get_conn()
    c = conn.cursor()
    q = "UPDATE screener_subscriptions SET status='rejected' WHERE id=%s" if USE_POSTGRES else \
        "UPDATE screener_subscriptions SET status='rejected' WHERE id=?"
    c.execute(q, (sub_id,))
    conn.commit()
    conn.close()


def _check_screener_access_sync(user_id):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    q = """SELECT * FROM screener_subscriptions WHERE user_id=%s AND status='approved'
        AND (end_date IS NULL OR end_date > %s)""" if USE_POSTGRES else \
        """SELECT * FROM screener_subscriptions WHERE user_id=? AND status='approved'
        AND (end_date IS NULL OR end_date > ?)"""
    c.execute(q, (user_id, now))
    row = c.fetchone()
    conn.close()
    return _row_to_dict(row)


def _get_expired_screener_subs_sync():
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    q = """SELECT * FROM screener_subscriptions WHERE status='approved'
        AND end_date IS NOT NULL AND end_date < %s""" if USE_POSTGRES else \
        """SELECT * FROM screener_subscriptions WHERE status='approved'
        AND end_date IS NOT NULL AND end_date < ?"""
    c.execute(q, (now,))
    rows = c.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def _mark_screener_expired_sync(sub_id):
    conn = get_conn()
    c = conn.cursor()
    q = "UPDATE screener_subscriptions SET status='expired' WHERE id=%s" if USE_POSTGRES else \
        "UPDATE screener_subscriptions SET status='expired' WHERE id=?"
    c.execute(q, (sub_id,))
    conn.commit()
    conn.close()


# ===================== PREMIUM =====================

def _save_premium_sub_sync(user_id, username, full_name):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""INSERT INTO premium_subscriptions (user_id, username, full_name)
            VALUES (%s, %s, %s) RETURNING id""",
            (user_id, username or "", full_name or "Noma'lum"))
        sub_id = c.fetchone()['id']
    else:
        c.execute("""INSERT INTO premium_subscriptions (user_id, username, full_name)
            VALUES (?, ?, ?)""",
            (user_id, username or "", full_name or "Noma'lum"))
        sub_id = c.lastrowid
    conn.commit()
    conn.close()
    return sub_id


def _get_premium_sub_sync(sub_id):
    conn = get_conn()
    c = conn.cursor()
    q = "SELECT * FROM premium_subscriptions WHERE id=%s" if USE_POSTGRES else \
        "SELECT * FROM premium_subscriptions WHERE id=?"
    c.execute(q, (sub_id,))
    row = c.fetchone()
    conn.close()
    return _row_to_dict(row)


def _approve_premium_sub_sync(sub_id):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now()
    q = "UPDATE premium_subscriptions SET status='approved', start_date=%s, end_date=NULL WHERE id=%s" if USE_POSTGRES else \
        "UPDATE premium_subscriptions SET status='approved', start_date=?, end_date=NULL WHERE id=?"
    c.execute(q, (now.isoformat(), sub_id))
    conn.commit()
    conn.close()


def _reject_premium_sub_sync(sub_id):
    conn = get_conn()
    c = conn.cursor()
    q = "UPDATE premium_subscriptions SET status='rejected' WHERE id=%s" if USE_POSTGRES else \
        "UPDATE premium_subscriptions SET status='rejected' WHERE id=?"
    c.execute(q, (sub_id,))
    conn.commit()
    conn.close()


def _check_premium_access_sync(user_id):
    conn = get_conn()
    c = conn.cursor()
    q = "SELECT * FROM premium_subscriptions WHERE user_id=%s AND status='approved'" if USE_POSTGRES else \
        "SELECT * FROM premium_subscriptions WHERE user_id=? AND status='approved'"
    c.execute(q, (user_id,))
    row = c.fetchone()
    conn.close()
    return _row_to_dict(row)


# ===================== ADMINS =====================

def _save_admin_id_sync(chat_id):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("INSERT INTO admins (id, chat_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                  (chat_id, chat_id))
    else:
        c.execute("INSERT OR REPLACE INTO admins (id, chat_id) VALUES (?, ?)", (chat_id, chat_id))
    conn.commit()
    conn.close()


def _get_admin_ids_sync():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT chat_id FROM admins")
    rows = c.fetchall()
    conn.close()
    return [r['chat_id'] for r in rows]


# ===================== ALERTS =====================

def _save_alert_sync(user_id, ticker, ticker_type, alert_type, condition, value):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""INSERT INTO alerts (user_id, ticker, ticker_type, alert_type, condition, value)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
            (user_id, ticker, ticker_type, alert_type, condition, value))
        aid = c.fetchone()['id']
    else:
        c.execute("""INSERT INTO alerts (user_id, ticker, ticker_type, alert_type, condition, value)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, ticker, ticker_type, alert_type, condition, value))
        aid = c.lastrowid
    conn.commit()
    conn.close()
    return aid


def _get_active_alerts_sync():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM alerts WHERE status='active'")
    rows = c.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def _get_user_alerts_sync(user_id):
    conn = get_conn()
    c = conn.cursor()
    q = "SELECT * FROM alerts WHERE user_id=%s AND status='active'" if USE_POSTGRES else \
        "SELECT * FROM alerts WHERE user_id=? AND status='active'"
    c.execute(q, (user_id,))
    rows = c.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def _deactivate_alert_sync(alert_id):
    conn = get_conn()
    c = conn.cursor()
    q = "UPDATE alerts SET status='triggered' WHERE id=%s" if USE_POSTGRES else \
        "UPDATE alerts SET status='triggered' WHERE id=?"
    c.execute(q, (alert_id,))
    conn.commit()
    conn.close()


def _delete_alert_sync(alert_id, user_id):
    conn = get_conn()
    c = conn.cursor()
    q = "DELETE FROM alerts WHERE id=%s AND user_id=%s" if USE_POSTGRES else \
        "DELETE FROM alerts WHERE id=? AND user_id=?"
    c.execute(q, (alert_id, user_id))
    conn.commit()
    conn.close()


# ===================== PORTFOLIO =====================

def _add_portfolio_sync(user_id, ticker, ticker_type, quantity, buy_price):
    conn = get_conn()
    c = conn.cursor()
    q = """INSERT INTO portfolio (user_id, ticker, ticker_type, quantity, buy_price)
        VALUES (%s, %s, %s, %s, %s)""" if USE_POSTGRES else \
        """INSERT INTO portfolio (user_id, ticker, ticker_type, quantity, buy_price)
        VALUES (?, ?, ?, ?, ?)"""
    c.execute(q, (user_id, ticker, ticker_type, quantity, buy_price))
    conn.commit()
    conn.close()


def _get_portfolio_sync(user_id):
    conn = get_conn()
    c = conn.cursor()
    q = "SELECT * FROM portfolio WHERE user_id=%s" if USE_POSTGRES else \
        "SELECT * FROM portfolio WHERE user_id=?"
    c.execute(q, (user_id,))
    rows = c.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def _delete_portfolio_item_sync(item_id, user_id):
    conn = get_conn()
    c = conn.cursor()
    q = "DELETE FROM portfolio WHERE id=%s AND user_id=%s" if USE_POSTGRES else \
        "DELETE FROM portfolio WHERE id=? AND user_id=?"
    c.execute(q, (item_id, user_id))
    conn.commit()
    conn.close()


# ===================== REFERRAL =====================

def _save_referral_sync(referrer_id, referred_id, referral_code):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""INSERT INTO referrals (referrer_id, referred_id, referral_code)
            VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
            (referrer_id, referred_id, referral_code))
    else:
        c.execute("""INSERT OR IGNORE INTO referrals (referrer_id, referred_id, referral_code)
            VALUES (?, ?, ?)""", (referrer_id, referred_id, referral_code))
    conn.commit()
    conn.close()


def _get_referral_stats_sync(user_id):
    conn = get_conn()
    c = conn.cursor()
    q = """SELECT COUNT(*) as total, COALESCE(SUM(reward_amount),0) as total_reward,
        COALESCE(SUM(CASE WHEN reward_paid=1 THEN reward_amount ELSE 0 END),0) as paid_reward
        FROM referrals WHERE referrer_id=%s""" if USE_POSTGRES else \
        """SELECT COUNT(*) as total, COALESCE(SUM(reward_amount),0) as total_reward,
        COALESCE(SUM(CASE WHEN reward_paid=1 THEN reward_amount ELSE 0 END),0) as paid_reward
        FROM referrals WHERE referrer_id=?"""
    c.execute(q, (user_id,))
    row = c.fetchone()
    conn.close()
    return _row_to_dict(row)


def _update_referral_reward_sync(referrer_id, referred_id, amount):
    conn = get_conn()
    c = conn.cursor()
    q = "UPDATE referrals SET reward_amount=%s WHERE referrer_id=%s AND referred_id=%s" if USE_POSTGRES else \
        "UPDATE referrals SET reward_amount=? WHERE referrer_id=? AND referred_id=?"
    c.execute(q, (amount, referrer_id, referred_id))
    conn.commit()
    conn.close()


# ===================== AFFILIATE =====================

def _save_affiliate_sync(user_id, username, full_name, affiliate_code):
    conn = get_conn()
    c = conn.cursor()
    q = """INSERT INTO affiliates (user_id, username, full_name, affiliate_code)
        VALUES (%s, %s, %s, %s)""" if USE_POSTGRES else \
        """INSERT INTO affiliates (user_id, username, full_name, affiliate_code)
        VALUES (?, ?, ?, ?)"""
    c.execute(q, (user_id, username or "", full_name or "Noma'lum", affiliate_code))
    conn.commit()
    conn.close()


def _get_affiliate_sync(user_id):
    conn = get_conn()
    c = conn.cursor()
    q = "SELECT * FROM affiliates WHERE user_id=%s" if USE_POSTGRES else \
        "SELECT * FROM affiliates WHERE user_id=?"
    c.execute(q, (user_id,))
    row = c.fetchone()
    conn.close()
    return _row_to_dict(row)


def _get_affiliate_by_code_sync(code):
    conn = get_conn()
    c = conn.cursor()
    q = "SELECT * FROM affiliates WHERE affiliate_code=%s AND status='approved'" if USE_POSTGRES else \
        "SELECT * FROM affiliates WHERE affiliate_code=? AND status='approved'"
    c.execute(q, (code,))
    row = c.fetchone()
    conn.close()
    return _row_to_dict(row)


def _approve_affiliate_sync(user_id):
    conn = get_conn()
    c = conn.cursor()
    q = "UPDATE affiliates SET status='approved' WHERE user_id=%s" if USE_POSTGRES else \
        "UPDATE affiliates SET status='approved' WHERE user_id=?"
    c.execute(q, (user_id,))
    conn.commit()
    conn.close()


def _add_affiliate_earning_sync(affiliate_id, referred_user_id, section, amount):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""INSERT INTO affiliate_earnings (affiliate_id, referred_user_id, section, amount)
            VALUES (%s, %s, %s, %s)""", (affiliate_id, referred_user_id, section, amount))
        c.execute("""UPDATE affiliates SET total_referrals=total_referrals+1,
            total_earned=total_earned+%s, pending_amount=pending_amount+%s WHERE id=%s""",
            (amount, amount, affiliate_id))
    else:
        c.execute("""INSERT INTO affiliate_earnings (affiliate_id, referred_user_id, section, amount)
            VALUES (?, ?, ?, ?)""", (affiliate_id, referred_user_id, section, amount))
        c.execute("""UPDATE affiliates SET total_referrals=total_referrals+1,
            total_earned=total_earned+?, pending_amount=pending_amount+? WHERE id=?""",
            (amount, amount, affiliate_id))
    conn.commit()
    conn.close()


def _get_all_affiliates_sync():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM affiliates WHERE status='approved'")
    rows = c.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


# ===================== FREE USAGE =====================

def _check_free_usage_sync(user_id):
    conn = get_conn()
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    q = "SELECT * FROM free_usage WHERE user_id=%s" if USE_POSTGRES else \
        "SELECT * FROM free_usage WHERE user_id=?"
    c.execute(q, (user_id,))
    row = c.fetchone()
    if not row:
        q2 = "INSERT INTO free_usage (user_id, last_date, count) VALUES (%s, %s, 0)" if USE_POSTGRES else \
             "INSERT INTO free_usage (user_id, last_date, count) VALUES (?, ?, 0)"
        c.execute(q2, (user_id, today))
        conn.commit()
        conn.close()
        return True
    row = _row_to_dict(row)
    if row['last_date'] != today:
        q3 = "UPDATE free_usage SET last_date=%s, count=0 WHERE user_id=%s" if USE_POSTGRES else \
             "UPDATE free_usage SET last_date=?, count=0 WHERE user_id=?"
        c.execute(q3, (today, user_id))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return row['count'] < 1


def _increment_free_usage_sync(user_id):
    conn = get_conn()
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    if USE_POSTGRES:
        c.execute("""INSERT INTO free_usage (user_id, last_date, count) VALUES (%s, %s, 1)
            ON CONFLICT (user_id) DO UPDATE SET
            count = CASE WHEN free_usage.last_date=%s THEN free_usage.count+1 ELSE 1 END,
            last_date = %s""", (user_id, today, today, today))
    else:
        c.execute("""INSERT INTO free_usage (user_id, last_date, count) VALUES (?, ?, 1)
            ON CONFLICT(user_id) DO UPDATE SET
            count = CASE WHEN last_date=? THEN count+1 ELSE 1 END, last_date = ?""",
            (user_id, today, today, today))
    conn.commit()
    conn.close()


# ===================== PROMO CODES =====================

def _check_promo_code_sync(code):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    q = """SELECT * FROM promo_codes WHERE code=%s AND used_count < max_uses
        AND (expires_at IS NULL OR expires_at > %s)""" if USE_POSTGRES else \
        """SELECT * FROM promo_codes WHERE code=? AND used_count < max_uses
        AND (expires_at IS NULL OR expires_at > ?)"""
    c.execute(q, (code, now))
    row = c.fetchone()
    conn.close()
    return _row_to_dict(row)


def _use_promo_code_sync(code):
    conn = get_conn()
    c = conn.cursor()
    q = "UPDATE promo_codes SET used_count=used_count+1 WHERE code=%s" if USE_POSTGRES else \
        "UPDATE promo_codes SET used_count=used_count+1 WHERE code=?"
    c.execute(q, (code,))
    conn.commit()
    conn.close()


def _create_promo_code_sync(code, discount_pct, max_uses, section, expires_at):
    conn = get_conn()
    c = conn.cursor()
    q = """INSERT INTO promo_codes (code, discount_pct, max_uses, section, expires_at)
        VALUES (%s, %s, %s, %s, %s)""" if USE_POSTGRES else \
        """INSERT INTO promo_codes (code, discount_pct, max_uses, section, expires_at)
        VALUES (?, ?, ?, ?, ?)"""
    c.execute(q, (code, discount_pct, max_uses, section, expires_at))
    conn.commit()
    conn.close()


# ===================== ONCHAIN SIGNALS =====================

def _save_onchain_signal_sync(signal_type, coin, data):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""INSERT INTO onchain_signals (signal_type, coin, data)
            VALUES (%s, %s, %s) RETURNING id""", (signal_type, coin, data))
        sid = c.fetchone()['id']
    else:
        c.execute("""INSERT INTO onchain_signals (signal_type, coin, data)
            VALUES (?, ?, ?)""", (signal_type, coin, data))
        sid = c.lastrowid
    conn.commit()
    conn.close()
    return sid


def _mark_signal_sent_sync(signal_id):
    conn = get_conn()
    c = conn.cursor()
    q = "UPDATE onchain_signals SET sent_to_channel=1 WHERE id=%s" if USE_POSTGRES else \
        "UPDATE onchain_signals SET sent_to_channel=1 WHERE id=?"
    c.execute(q, (signal_id,))
    conn.commit()
    conn.close()


# ===================== WATCHLIST =====================

def _add_watchlist_sync(user_id, ticker, ticker_type):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""INSERT INTO watchlist (user_id, ticker, ticker_type)
            VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""", (user_id, ticker, ticker_type))
    else:
        c.execute("""INSERT OR IGNORE INTO watchlist (user_id, ticker, ticker_type)
            VALUES (?, ?, ?)""", (user_id, ticker, ticker_type))
    conn.commit()
    conn.close()


def _get_watchlist_sync(user_id):
    conn = get_conn()
    c = conn.cursor()
    q = "SELECT * FROM watchlist WHERE user_id=%s" if USE_POSTGRES else \
        "SELECT * FROM watchlist WHERE user_id=?"
    c.execute(q, (user_id,))
    rows = c.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def _remove_watchlist_sync(user_id, ticker):
    conn = get_conn()
    c = conn.cursor()
    q = "DELETE FROM watchlist WHERE user_id=%s AND ticker=%s" if USE_POSTGRES else \
        "DELETE FROM watchlist WHERE user_id=? AND ticker=?"
    c.execute(q, (user_id, ticker))
    conn.commit()
    conn.close()


# ===================== SEARCH HISTORY =====================

def _save_search_sync(user_id, ticker, ticker_type):
    conn = get_conn()
    c = conn.cursor()
    q = """INSERT INTO search_history (user_id, ticker, ticker_type)
        VALUES (%s, %s, %s)""" if USE_POSTGRES else \
        """INSERT INTO search_history (user_id, ticker, ticker_type)
        VALUES (?, ?, ?)"""
    c.execute(q, (user_id, ticker, ticker_type))
    conn.commit()
    conn.close()


def _get_search_history_sync(user_id, limit=5):
    conn = get_conn()
    c = conn.cursor()
    q = """SELECT DISTINCT ticker, ticker_type FROM search_history
        WHERE user_id=%s ORDER BY created_at DESC LIMIT %s""" if USE_POSTGRES else \
        """SELECT DISTINCT ticker, ticker_type FROM search_history
        WHERE user_id=? ORDER BY created_at DESC LIMIT ?"""
    c.execute(q, (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


# ===================== ADMIN STATS =====================

def _get_stats_sync():
    conn = get_conn()
    c = conn.cursor()
    this_month = datetime.now().strftime("%Y-%m")
    results = {}

    def fetch_count(query, params=None):
        if params:
            c.execute(query, params)
        else:
            c.execute(query)
        row = c.fetchone()
        if USE_POSTGRES:
            return list(dict(row).values())[0]
        else:
            return row[0]

    results['channel_subs']   = fetch_count("SELECT COUNT(DISTINCT user_id) FROM subscriptions WHERE status='approved'")
    results['screener_subs']  = fetch_count("SELECT COUNT(DISTINCT user_id) FROM screener_subscriptions WHERE status='approved'")
    results['premium_subs']   = fetch_count("SELECT COUNT(DISTINCT user_id) FROM premium_subscriptions WHERE status='approved'")
    results['pending']        = fetch_count("SELECT COUNT(*) FROM subscriptions WHERE status='pending'")

    if USE_POSTGRES:
        results['new_this_month'] = fetch_count(
            "SELECT COUNT(*) FROM subscriptions WHERE status='approved' AND created_at LIKE %s",
            (f"{this_month}%",)
        )
    else:
        results['new_this_month'] = fetch_count(
            "SELECT COUNT(*) FROM subscriptions WHERE status='approved' AND created_at LIKE ?",
            (f"{this_month}%",)
        )

    conn.close()
    return results


def _get_all_users_sync():
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""
            SELECT DISTINCT user_id, username, full_name FROM subscriptions WHERE status='approved'
            UNION SELECT DISTINCT user_id, username, full_name FROM screener_subscriptions WHERE status='approved'
            UNION SELECT DISTINCT user_id, username, full_name FROM premium_subscriptions WHERE status='approved'
        """)
    else:
        c.execute("""
            SELECT DISTINCT user_id, username, full_name FROM subscriptions WHERE status='approved'
            UNION SELECT DISTINCT user_id, username, full_name FROM screener_subscriptions WHERE status='approved'
            UNION SELECT DISTINCT user_id, username, full_name FROM premium_subscriptions WHERE status='approved'
        """)
    rows = c.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def _cancel_subscription_sync(user_id, section):
    conn = get_conn()
    c = conn.cursor()
    q = "UPDATE subscriptions SET status='cancelled' WHERE user_id=%s AND section=%s AND status='approved'" if USE_POSTGRES else \
        "UPDATE subscriptions SET status='cancelled' WHERE user_id=? AND section=? AND status='approved'"
    c.execute(q, (user_id, section))
    conn.commit()
    conn.close()


# ===================== ASYNC WRAPPERS =====================

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

async def check_channel_access(user_id, section):
    return await asyncio.to_thread(_check_channel_access_sync, user_id, section)

async def get_expired_subscriptions():
    return await asyncio.to_thread(_get_expired_subscriptions_sync)

async def mark_expired(sub_id):
    await asyncio.to_thread(_mark_expired_sync, sub_id)

async def save_screener_sub(user_id, username, full_name, duration):
    return await asyncio.to_thread(_save_screener_sub_sync, user_id, username, full_name, duration)

async def get_screener_sub(sub_id):
    return await asyncio.to_thread(_get_screener_sub_sync, sub_id)

async def approve_screener_sub(sub_id, duration_months):
    await asyncio.to_thread(_approve_screener_sub_sync, sub_id, duration_months)

async def reject_screener_sub(sub_id):
    await asyncio.to_thread(_reject_screener_sub_sync, sub_id)

async def check_screener_access(user_id):
    return await asyncio.to_thread(_check_screener_access_sync, user_id)

async def get_expired_screener_subs():
    return await asyncio.to_thread(_get_expired_screener_subs_sync)

async def mark_screener_expired(sub_id):
    await asyncio.to_thread(_mark_screener_expired_sync, sub_id)

async def save_premium_sub(user_id, username, full_name):
    return await asyncio.to_thread(_save_premium_sub_sync, user_id, username, full_name)

async def get_premium_sub(sub_id):
    return await asyncio.to_thread(_get_premium_sub_sync, sub_id)

async def approve_premium_sub(sub_id):
    await asyncio.to_thread(_approve_premium_sub_sync, sub_id)

async def reject_premium_sub(sub_id):
    await asyncio.to_thread(_reject_premium_sub_sync, sub_id)

async def check_premium_access(user_id):
    return await asyncio.to_thread(_check_premium_access_sync, user_id)

async def save_admin_id(chat_id):
    await asyncio.to_thread(_save_admin_id_sync, chat_id)

async def get_admin_ids():
    return await asyncio.to_thread(_get_admin_ids_sync)

async def save_alert(user_id, ticker, ticker_type, alert_type, condition, value):
    return await asyncio.to_thread(_save_alert_sync, user_id, ticker, ticker_type, alert_type, condition, value)

async def get_active_alerts():
    return await asyncio.to_thread(_get_active_alerts_sync)

async def get_user_alerts(user_id):
    return await asyncio.to_thread(_get_user_alerts_sync, user_id)

async def deactivate_alert(alert_id):
    await asyncio.to_thread(_deactivate_alert_sync, alert_id)

async def delete_alert(alert_id, user_id):
    await asyncio.to_thread(_delete_alert_sync, alert_id, user_id)

async def add_portfolio(user_id, ticker, ticker_type, quantity, buy_price):
    await asyncio.to_thread(_add_portfolio_sync, user_id, ticker, ticker_type, quantity, buy_price)

async def get_portfolio(user_id):
    return await asyncio.to_thread(_get_portfolio_sync, user_id)

async def delete_portfolio_item(item_id, user_id):
    await asyncio.to_thread(_delete_portfolio_item_sync, item_id, user_id)

async def save_referral(referrer_id, referred_id, referral_code):
    await asyncio.to_thread(_save_referral_sync, referrer_id, referred_id, referral_code)

async def get_referral_stats(user_id):
    return await asyncio.to_thread(_get_referral_stats_sync, user_id)

async def update_referral_reward(referrer_id, referred_id, amount):
    await asyncio.to_thread(_update_referral_reward_sync, referrer_id, referred_id, amount)

async def save_affiliate(user_id, username, full_name, affiliate_code):
    await asyncio.to_thread(_save_affiliate_sync, user_id, username, full_name, affiliate_code)

async def get_affiliate(user_id):
    return await asyncio.to_thread(_get_affiliate_sync, user_id)

async def get_affiliate_by_code(code):
    return await asyncio.to_thread(_get_affiliate_by_code_sync, code)

async def approve_affiliate(user_id):
    await asyncio.to_thread(_approve_affiliate_sync, user_id)

async def add_affiliate_earning(affiliate_id, referred_user_id, section, amount):
    await asyncio.to_thread(_add_affiliate_earning_sync, affiliate_id, referred_user_id, section, amount)

async def get_all_affiliates():
    return await asyncio.to_thread(_get_all_affiliates_sync)

async def check_free_usage(user_id):
    return await asyncio.to_thread(_check_free_usage_sync, user_id)

async def increment_free_usage(user_id):
    await asyncio.to_thread(_increment_free_usage_sync, user_id)

async def check_promo_code(code):
    return await asyncio.to_thread(_check_promo_code_sync, code)

async def use_promo_code(code):
    await asyncio.to_thread(_use_promo_code_sync, code)

async def create_promo_code(code, discount_pct, max_uses, section, expires_at):
    await asyncio.to_thread(_create_promo_code_sync, code, discount_pct, max_uses, section, expires_at)

async def save_onchain_signal(signal_type, coin, data):
    return await asyncio.to_thread(_save_onchain_signal_sync, signal_type, coin, data)

async def mark_signal_sent(signal_id):
    await asyncio.to_thread(_mark_signal_sent_sync, signal_id)

async def add_watchlist(user_id, ticker, ticker_type):
    await asyncio.to_thread(_add_watchlist_sync, user_id, ticker, ticker_type)

async def get_watchlist(user_id):
    return await asyncio.to_thread(_get_watchlist_sync, user_id)

async def remove_watchlist(user_id, ticker):
    await asyncio.to_thread(_remove_watchlist_sync, user_id, ticker)

async def save_search(user_id, ticker, ticker_type):
    await asyncio.to_thread(_save_search_sync, user_id, ticker, ticker_type)

async def get_search_history(user_id, limit=5):
    return await asyncio.to_thread(_get_search_history_sync, user_id, limit)

async def get_stats():
    return await asyncio.to_thread(_get_stats_sync)

async def get_all_users():
    return await asyncio.to_thread(_get_all_users_sync)

async def cancel_subscription(user_id, section):
    await asyncio.to_thread(_cancel_subscription_sync, user_id, section)


def _cancel_screener_subscription_sync(user_id):
    conn = get_conn()
    c = conn.cursor()
    q = "UPDATE screener_subscriptions SET status='cancelled' WHERE user_id=%s AND status='approved'" if USE_POSTGRES else \
        "UPDATE screener_subscriptions SET status='cancelled' WHERE user_id=? AND status='approved'"
    c.execute(q, (user_id,))
    conn.commit()
    conn.close()


def _cancel_premium_subscription_sync(user_id):
    conn = get_conn()
    c = conn.cursor()
    q = "UPDATE premium_subscriptions SET status='cancelled' WHERE user_id=%s AND status='approved'" if USE_POSTGRES else \
        "UPDATE premium_subscriptions SET status='cancelled' WHERE user_id=? AND status='approved'"
    c.execute(q, (user_id,))
    conn.commit()
    conn.close()


async def cancel_screener_subscription(user_id):
    await asyncio.to_thread(_cancel_screener_subscription_sync, user_id)

async def cancel_premium_subscription(user_id):
    await asyncio.to_thread(_cancel_premium_subscription_sync, user_id)


# ===================== USERS =====================

def _save_user_sync(user_id, username, full_name):
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""INSERT INTO users (user_id, username, full_name)
            VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET
            username=EXCLUDED.username, full_name=EXCLUDED.full_name""",
            (user_id, username or "", full_name or ""))
    else:
        # Avval foydalanuvchi bormi tekshirish
        c.execute("SELECT created_at FROM users WHERE user_id=?", (user_id,))
        existing = c.fetchone()
        if existing:
            # Bor bo'lsa faqat username va full_name yangilansin, created_at saqlansin
            c.execute("""UPDATE users SET username=?, full_name=? WHERE user_id=?""",
                (username or "", full_name or "", user_id))
        else:
            # Yangi foydalanuvchi — created_at avtomatik qo'shiladi
            c.execute("""INSERT INTO users (user_id, username, full_name)
                VALUES (?, ?, ?)""", (user_id, username or "", full_name or ""))
    conn.commit()
    conn.close()


def _get_non_subscribers_sync():
    """Obuna bo'lmagan foydalanuvchilar"""
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""
            SELECT u.user_id, u.username, u.full_name FROM users u
            WHERE u.user_id NOT IN (
                SELECT DISTINCT user_id FROM subscriptions WHERE status='approved'
                UNION
                SELECT DISTINCT user_id FROM screener_subscriptions WHERE status='approved'
                UNION
                SELECT DISTINCT user_id FROM premium_subscriptions WHERE status='approved'
            )
        """)
    else:
        c.execute("""
            SELECT u.user_id, u.username, u.full_name FROM users u
            WHERE u.user_id NOT IN (
                SELECT DISTINCT user_id FROM subscriptions WHERE status='approved'
                UNION
                SELECT DISTINCT user_id FROM screener_subscriptions WHERE status='approved'
                UNION
                SELECT DISTINCT user_id FROM premium_subscriptions WHERE status='approved'
            )
        """)
    rows = c.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def _get_all_bot_users_sync():
    """Barcha foydalanuvchilar"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


async def save_user(user_id, username, full_name):
    await asyncio.to_thread(_save_user_sync, user_id, username, full_name)

async def get_non_subscribers():
    return await asyncio.to_thread(_get_non_subscribers_sync)

async def get_all_bot_users():
    return await asyncio.to_thread(_get_all_bot_users_sync)


def _get_all_promos_sync():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM promo_codes ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]

def _delete_promo_code_sync(code):
    conn = get_conn()
    c = conn.cursor()
    q = "DELETE FROM promo_codes WHERE code=%s" if USE_POSTGRES else \
        "DELETE FROM promo_codes WHERE code=?"
    c.execute(q, (code,))
    conn.commit()
    conn.close()

async def get_all_promos():
    return await asyncio.to_thread(_get_all_promos_sync)

async def delete_promo_code(code):
    await asyncio.to_thread(_delete_promo_code_sync, code)
