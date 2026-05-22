#!/usr/bin/env python3
"""
Azia Quant Bot — Crypto Screener Module
CoinGecko, DefiLlama, Alternative.me + RSS orqali crypto tahlili
"""

import requests
import feedparser
from config import COINGECKO_BASE, ALTERNATIVE_BASE, DEFILLAMA_BASE, CRYPTO_TICKER_MAP


def _fmt_big(n):
    if not n or n == 0: return "N/A"
    try:
        n = float(n)
        if abs(n) >= 1e12: return f"${n/1e12:.2f}T"
        if abs(n) >= 1e9:  return f"${n/1e9:.2f}B"
        if abs(n) >= 1e6:  return f"${n/1e6:.2f}M"
        return f"${n:,.2f}"
    except: return "N/A"


def get_coin_id(ticker: str) -> str:
    """Ticker dan CoinGecko ID ni topadi"""
    ticker_upper = ticker.upper()
    if ticker_upper in CRYPTO_TICKER_MAP:
        return CRYPTO_TICKER_MAP[ticker_upper]
    try:
        resp = requests.get(
            f"{COINGECKO_BASE}/search",
            params={"query": ticker},
            timeout=10
        )
        if resp.status_code == 200:
            coins = resp.json().get('coins', [])
            for coin in coins[:5]:
                if coin.get('symbol', '').upper() == ticker_upper:
                    return coin['id']
            if coins:
                return coins[0]['id']
    except: pass
    return ticker.lower()


def _calc_rsi_crypto(prices, period=14):
    try:
        if len(prices) < period + 1: return None
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains  = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        avg_g  = sum(gains[-period:]) / period
        avg_l  = sum(losses[-period:]) / period
        if avg_l == 0: return 100.0
        rs = avg_g / avg_l
        return 100 - (100 / (1 + rs))
    except: return None


def _rsi_label(rsi):
    if rsi is None: return "N/A"
    if rsi < 30:   return f"{rsi:.0f} — Oversold 🟢"
    elif rsi > 70: return f"{rsi:.0f} — Overbought 🔴"
    else:          return f"{rsi:.0f} — Neytral ⚪"


def get_fear_greed():
    try:
        resp = requests.get(f"{ALTERNATIVE_BASE}/fng/", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            val  = int(data['data'][0]['value'])
            cls  = data['data'][0]['value_classification']
            if val >= 75:   icon = "🔴"
            elif val >= 55: icon = "🟡"
            elif val >= 35: icon = "🟠"
            else:           icon = "🟢"
            return f"{val}/100 — {cls} {icon}"
    except: pass
    return "N/A"


def get_crypto_news_rss(coin_name: str, symbol: str) -> str:
    """RSS Feed orqali crypto yangiliklari"""
    try:
        news_txt = ""

        # CoinDesk RSS
        feeds = [
            f"https://www.coindesk.com/arc/outboundfeeds/rss/",
            f"https://cointelegraph.com/rss",
            f"https://news.google.com/rss/search?q={symbol}+crypto&hl=en&gl=US&ceid=US:en",
        ]

        for feed_url in feeds:
            try:
                feed  = feedparser.parse(feed_url)
                count = 0
                for entry in feed.entries[:10]:
                    title = (entry.get('title') or '')[:65]
                    link  = entry.get('link') or ''
                    src   = feed.feed.get('title', 'News')

                    # Coin nomi yoki symbol mavjudmi
                    if (symbol.lower() in title.lower() or
                        coin_name.lower() in title.lower() or
                        'crypto' in title.lower() or
                        'bitcoin' in title.lower()):

                        if title and link:
                            news_txt += f"• <a href='{link}'>{title}</a>\n  📰 {src}\n"
                            count += 1
                    if count >= 2: break
                if news_txt: break
            except: continue

        return news_txt or "• Yangilik topilmadi\n"
    except Exception as e:
        print(f"[ERROR] Crypto news RSS: {e}")
        return "• Yangilik topilmadi\n"


def get_developer_activity(coin_id: str, data: dict) -> str:
    """Developer faolligi"""
    try:
        dev = data.get('developer_data', {})
        if not dev:
            return "• Ma'lumot yo'q\n"

        forks     = dev.get('forks') or 0
        stars     = dev.get('stars') or 0
        commits   = dev.get('commit_count_4_weeks') or 0
        prs       = dev.get('pull_requests_merged') or 0
        contrib   = dev.get('pull_request_contributors') or 0

        if commits > 100:   level = "Juda faol 🟢"
        elif commits > 30:  level = "Faol ✅"
        elif commits > 5:   level = "O'rtacha ⚪"
        elif commits > 0:   level = "Past faollik 🟡"
        else:               level = "Faol emas 🔴"

        txt = f"• Faollik: {level}\n"
        if commits: txt += f"• Commitlar (4 hafta): {commits}\n"
        if stars:   txt += f"• GitHub stars: {stars:,}\n"
        if forks:   txt += f"• Forks: {forks:,}\n"
        return txt
    except:
        return "• Ma'lumot yo'q\n"


def get_token_unlock(coin_id: str) -> str:
    """Token Unlock (DefiLlama)"""
    try:
        from datetime import datetime
        resp = requests.get(
            f"https://coins.llama.fi/emission/{coin_id}",
            timeout=10
        )
        if resp.status_code == 200:
            events  = resp.json().get('events', [])
            now_ts  = datetime.now().timestamp()
            future  = sorted(
                [e for e in events if e.get('timestamp', 0) > now_ts],
                key=lambda x: x.get('timestamp', 0)
            )
            unlock_txt = ""
            for ev in future[:3]:
                ev_date   = datetime.fromtimestamp(ev['timestamp']).strftime("%d-%b %Y")
                ev_amount = ev.get('noOfTokens', [0])
                ev_amount = ev_amount[0] if isinstance(ev_amount, list) else ev_amount
                ev_desc   = ev.get('description', 'Noma\'lum')
                days_left = int((ev['timestamp'] - now_ts) / 86400)
                unlock_txt += f"• {ev_date}: {ev_amount:,.0f} token\n  {ev_desc} ({days_left} kun)\n"
            return unlock_txt or "• Unlock ma'lumoti yo'q ✅\n"
        return "• Ma'lumot topilmadi\n"
    except:
        return "• Ma'lumot topilmadi\n"


def get_crypto_data(ticker: str, is_free: bool = False) -> str:
    try:
        coin_id = get_coin_id(ticker)

        resp = requests.get(
            f"{COINGECKO_BASE}/coins/{coin_id}",
            params={
                "localization":   "false",
                "tickers":        "false",
                "market_data":    "true",
                "community_data": "true",
                "developer_data": "true",
            },
            timeout=15
        )

        if resp.status_code == 429:
            return "⏳ CoinGecko so'rov limiti. Biroz kuting."
        if resp.status_code != 200:
            return None

        data   = resp.json()
        md     = data.get('market_data', {})
        name   = data.get('name', ticker)
        symbol = data.get('symbol', '').upper()

        price      = md.get('current_price', {}).get('usd') or 0
        change_24h = md.get('price_change_percentage_24h') or 0
        mkt_cap    = md.get('market_cap', {}).get('usd') or 0
        volume_24h = md.get('total_volume', {}).get('usd') or 0
        circ_sup   = md.get('circulating_supply') or 0
        max_sup    = md.get('max_supply')
        fdv        = md.get('fully_diluted_valuation', {}).get('usd') or 0
        ath        = md.get('ath', {}).get('usd') or 0
        atl        = md.get('atl', {}).get('usd') or 0
        ath_chg    = md.get('ath_change_percentage', {}).get('usd') or 0

        change_icon = "📈" if change_24h >= 0 else "📉"
        change_sign = "+" if change_24h >= 0 else ""

        if max_sup and circ_sup:
            mined_pct = (circ_sup / max_sup) * 100
            mined_txt = f"{mined_pct:.1f}%"
        else:
            mined_txt = "Cheksiz (Max Supply yo'q)"

        if mkt_cap >= 10e9:  cap_cat = "Large Cap 🔵"
        elif mkt_cap >= 1e9: cap_cat = "Mid Cap 🟡"
        elif mkt_cap >= 100e6: cap_cat = "Small Cap 🟠"
        else:                cap_cat = "Micro Cap 🔴"

        # BEPUL VERSIYA
        if is_free:
            return (
                f"🔍 <b>{symbol} — {name}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 <b>ASOSIY:</b>\n"
                f"• Narx: <b>${price:,.4f}</b> ({change_sign}{change_24h:.2f}% {change_icon})\n"
                f"• Bozor kap: {_fmt_big(mkt_cap)}\n"
                f"• Toifa: {cap_cat}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💎 <b>To'liq tahlil uchun obuna oling!</b>"
            )

        # RSI
        try:
            ohlc_resp = requests.get(
                f"{COINGECKO_BASE}/coins/{coin_id}/ohlc",
                params={"vs_currency": "usd", "days": "30"},
                timeout=10
            )
            if ohlc_resp.status_code == 200:
                closes  = [c[4] for c in ohlc_resp.json()]
                rsi_v   = _calc_rsi_crypto(closes)
                rsi_txt = _rsi_label(rsi_v)
            else:
                rsi_txt = "N/A"
        except:
            rsi_txt = "N/A"

        # MA50 va MA200
        try:
            hist_resp = requests.get(
                f"{COINGECKO_BASE}/coins/{coin_id}/market_chart",
                params={"vs_currency": "usd", "days": "200"},
                timeout=10
            )
            if hist_resp.status_code == 200:
                prices  = [p[1] for p in hist_resp.json().get('prices', [])]
                ma50_v  = sum(prices[-50:]) / 50 if len(prices) >= 50 else None
                ma200_v = sum(prices[-200:]) / 200 if len(prices) >= 200 else None
                ma50_txt  = f"${ma50_v:,.4f} {'✅' if price > ma50_v else '❌'}" if ma50_v else "N/A"
                ma200_txt = f"${ma200_v:,.4f} {'✅' if price > ma200_v else '❌'}" if ma200_v else "N/A"
            else:
                ma50_txt = ma200_txt = "N/A"
        except:
            ma50_txt = ma200_txt = "N/A"

        fg_txt     = get_fear_greed()
        unlock_txt = get_token_unlock(coin_id)
        news_txt   = get_crypto_news_rss(name, symbol)
        dev_txt    = get_developer_activity(coin_id, data)

        return (
            f"🔍 <b>{symbol} — {name}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"

            f"💰 <b>ASOSIY:</b>\n"
            f"• Narx: <b>${price:,.4f}</b> ({change_sign}{change_24h:.2f}% {change_icon})\n"
            f"• Bozor kap: {_fmt_big(mkt_cap)} ({cap_cat})\n"
            f"• Hajm (24s): {_fmt_big(volume_24h)}\n\n"

            f"📦 <b>TA'MINOT:</b>\n"
            f"• Muomaladagi: {circ_sup:,.0f} {symbol}\n"
            f"• Max Supply: {f'{max_sup:,.0f}' if max_sup else 'Cheksiz'} {symbol}\n"
            f"• Qazilgan: {mined_txt}\n"
            f"• FDV: {_fmt_big(fdv)}\n\n"

            f"📈 <b>TEXNIK:</b>\n"
            f"• RSI (14): {rsi_txt}\n"
            f"• MA50: {ma50_txt}\n"
            f"• MA200: {ma200_txt}\n"
            f"• ATH: ${ath:,.4f} ({ath_chg:.1f}%)\n"
            f"• ATL: ${atl:,.8f}\n\n"

            f"🔓 <b>TOKEN UNLOCK:</b>\n"
            f"{unlock_txt}\n"

            f"💻 <b>DEVELOPER FAOLLIGI:</b>\n"
            f"{dev_txt}\n"

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

    except Exception as e:
        print(f"[ERROR] Crypto data ({ticker}): {e}")
        return None
