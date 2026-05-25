#!/usr/bin/env python3
"""
Azia Quant Bot — Stock Screener Module
Yahoo Finance + Finnhub orqali aksiya tahlili
"""

import os
import yfinance as yf
import requests
import feedparser

FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")
FINNHUB_BASE = "https://finnhub.io/api/v1"


def _get_finnhub(endpoint, params={}):
    """Finnhub API dan ma'lumot olish"""
    try:
        if not FINNHUB_API_KEY:
            return None
        params['token'] = FINNHUB_API_KEY
        resp = requests.get(f"{FINNHUB_BASE}/{endpoint}", params=params, timeout=8)
        if resp.status_code == 200:
            return resp.json()
        return None
    except:
        return None


def _fmt_big(n):
    if not n or n == 0: return "N/A"
    try:
        n = float(n)
        if abs(n) >= 1e12: return f"${n/1e12:.2f}T"
        if abs(n) >= 1e9:  return f"${n/1e9:.2f}B"
        if abs(n) >= 1e6:  return f"${n/1e6:.2f}M"
        return f"${n:,.2f}"
    except: return "N/A"


def _fmt_pct(n):
    if n is None: return "N/A"
    try: return f"{float(n)*100:.1f}%"
    except: return "N/A"


def _calc_rsi(hist, period=14):
    try:
        if hist is None or len(hist) < period + 1: return None
        delta = hist['Close'].diff()
        gain  = delta.where(delta > 0, 0).rolling(period).mean()
        loss  = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs    = gain / loss
        return float(100 - (100 / (1 + rs.iloc[-1])))
    except: return None


def _rsi_label(rsi):
    if rsi is None: return "N/A"
    if rsi < 30:   return f"{rsi:.0f} — Oversold 🟢"
    elif rsi > 70: return f"{rsi:.0f} — Overbought 🔴"
    else:          return f"{rsi:.0f} — Neytral ⚪"


def get_stock_news(ticker, name):
    """Finnhub + Google News RSS orqali yangiliklar"""
    try:
        news_txt = ""

        # Finnhub news (eng ishonchli)
        try:
            from datetime import datetime, timedelta
            date_to   = datetime.now().strftime('%Y-%m-%d')
            date_from = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            fh_news = _get_finnhub("company-news", {
                "symbol": ticker.upper(),
                "from": date_from,
                "to": date_to
            })
            if fh_news:
                for n in fh_news[:3]:
                    title = (n.get('headline') or '')[:65]
                    link  = n.get('url') or ''
                    src   = n.get('source') or ''
                    if title and link:
                        news_txt += f"• <a href='{link}'>{title}</a>\n  📰 {src}\n"
            if news_txt:
                return news_txt
        except: pass

        # yfinance news fallback
        try:
            stock = yf.Ticker(ticker)
            news_list = stock.news or []
            for n in news_list[:3]:
                title = (n.get('title') or '')[:65]
                link  = n.get('link') or ''
                pub   = n.get('publisher') or ''
                if title and link:
                    news_txt += f"• <a href='{link}'>{title}</a>\n  📰 {pub}\n"
            if news_txt:
                return news_txt
        except: pass

        # Google News RSS fallback
        query = f"{ticker} stock"
        feed  = feedparser.parse(
            f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        )
        count = 0
        for entry in feed.entries[:5]:
            title = (entry.get('title') or '')[:65]
            link  = entry.get('link') or ''
            if title and link:
                news_txt += f"• <a href='{link}'>{title}</a>\n"
                count += 1
                if count >= 3: break

        return news_txt or "• Yangilik topilmadi\n"
    except:
        return "• Yangilik topilmadi\n"


def get_stock_data(ticker: str, is_free: bool = False) -> str:
    try:
        stock = yf.Ticker(ticker)
        info  = stock.info

        if not info or not (info.get('regularMarketPrice') or info.get('currentPrice')):
            hist = stock.history(period="1d")
            if hist is None or hist.empty: return None

        name     = info.get('longName') or info.get('shortName') or ticker
        price    = info.get('regularMarketPrice') or info.get('currentPrice') or 0
        change   = info.get('regularMarketChangePercent') or 0
        mkt_cap  = info.get('marketCap') or 0
        w52_high = info.get('fiftyTwoWeekHigh') or 0
        w52_low  = info.get('fiftyTwoWeekLow') or 0
        sector   = info.get('sector') or "N/A"
        exchange = info.get('exchange') or ""

        # Finnhub dan real-time narx
        fh_quote = _get_finnhub("quote", {"symbol": ticker.upper()})
        if fh_quote and fh_quote.get('c'):
            price  = fh_quote['c']
            change = fh_quote.get('dp', change)

        change_icon = "📈" if change >= 0 else "📉"
        change_sign = "+" if change >= 0 else ""

        if is_free:
            return (
                f"🔎 <b>{ticker.upper()} — {name}</b>\n"
                f"📍 {sector} | {exchange}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 <b>ASOSIY:</b>\n"
                f"• Narx: <b>${price:,.2f}</b> ({change_sign}{change:.2f}% {change_icon})\n"
                f"• Bozor kap: {_fmt_big(mkt_cap)}\n"
                f"• 52 hafta: ${w52_low:,.2f} — ${w52_high:,.2f}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💎 <b>To'liq tahlil uchun obuna oling!</b>"
            )

        # Fundamental
        pe_ratio  = info.get('trailingPE') or 0
        pb_ratio  = info.get('priceToBook') or 0
        ps_ratio  = info.get('priceToSalesTrailing12Months') or 0
        ev_ebitda = info.get('enterpriseToEbitda') or 0
        eps       = info.get('trailingEps') or 0
        eps_growth= info.get('earningsGrowth') or 0
        revenue   = info.get('totalRevenue') or 0
        net_income= info.get('netIncomeToCommon') or 0
        gross_m   = info.get('grossMargins') or 0
        net_m     = info.get('profitMargins') or 0
        roe       = info.get('returnOnEquity') or 0
        roa       = info.get('returnOnAssets') or 0
        debt_eq   = info.get('debtToEquity') or 0
        fcf       = info.get('freeCashflow') or 0
        dividend  = info.get('dividendRate') or 0
        div_yield = info.get('dividendYield') or 0
        # div_yield odatda 0.0035 formatida keladi (0.35%)
        # Agar 1 dan katta bo'lsa — 100 ga bo'lish kerak
        if div_yield and div_yield > 1:
            div_yield = div_yield / 100
        # Agar hali ham 0.5 dan katta bo'lsa — noto'g'ri, 100 ga bo'lamiz
        if div_yield and div_yield > 0.5:
            div_yield = div_yield / 100

        # Texnik
        beta  = info.get('beta') or 0
        ma50  = info.get('fiftyDayAverage') or 0
        ma200 = info.get('twoHundredDayAverage') or 0
        short_pct = info.get('shortPercentOfFloat') or 0

        hist    = stock.history(period="1mo")
        rsi_val = _calc_rsi(hist)
        rsi_txt = _rsi_label(rsi_val)

        ma50_txt  = f"${ma50:,.2f} {'✅' if price > ma50 else '❌'}"  if ma50 else "N/A"
        ma200_txt = f"${ma200:,.2f} {'✅' if price > ma200 else '❌'}" if ma200 else "N/A"

        if w52_high and w52_low and (w52_high - w52_low) > 0:
            w52_pos = ((price - w52_low) / (w52_high - w52_low)) * 100
            w52_pos_txt = f"{w52_pos:.0f}% (pastdan)"
        else:
            w52_pos_txt = "N/A"

        # Analyst
        rec         = (info.get('recommendationKey') or 'N/A').upper()
        target_price= info.get('targetMeanPrice') or 0
        analyst_num = info.get('numberOfAnalystOpinions') or 0
        rec_map = {
            'STRONG_BUY': 'KUCHLI SOTIB OL 🟢',
            'BUY':        'SOTIB OL ✅',
            'HOLD':       'KUTING ⚪',
            'SELL':       'SOTMA ❌',
            'STRONG_SELL':'KUCHLI SOTMA 🔴',
        }
        rec_txt = rec_map.get(rec, rec)

        # Institutional
        inst_pct    = info.get('institutionPercentHeld') or 0
        insider_pct = info.get('insiderPercentHeld') or 0
        if inst_pct > 0:
            inst_txt = f"• Fondlar ulushi: {inst_pct*100:.1f}%\n• Insider ulushi: {insider_pct*100:.1f}%\n"
        else:
            inst_txt = "• Ma'lumot yuklanmoqda\n"

        # Insider tranzaksiyalar (Finnhub)
        try:
            insider_txt = ""
            fh_insider = _get_finnhub("stock/insider-transactions", {"symbol": ticker.upper()})
            if fh_insider and fh_insider.get('data'):
                for item in fh_insider['data'][:3]:
                    iname  = (item.get('name') or "Noma'lum")[:30]
                    ishares = float(item.get('share') or 0)
                    idate  = str(item.get('transactionDate') or '')[:10]
                    itype  = item.get('transactionCode') or ''
                    icon   = "SOTDI ⚠️" if itype in ['S', 'D'] else "OLDI ✅"
                    insider_txt += f"• {iname}: {abs(ishares):,.0f} {icon} | {idate}\n"
            if not insider_txt:
                # yfinance dan fallback
                idf = stock.insider_transactions
                if idf is not None and not idf.empty:
                    for _, row in idf.head(3).iterrows():
                        iname   = (str(row.get('Name') or row.get('Insider') or "Noma'lum"))[:30]
                        ishares = float(row.get('Shares') or 0)
                        ival    = float(row.get('Value') or 0)
                        idate   = str(row.get('Start Date') or row.get('startDate') or '')[:10]
                        icon    = "SOTDI ⚠️" if ishares < 0 else "OLDI ✅"
                        insider_txt += f"• {iname}: {abs(ishares):,.0f} {icon}\n  {_fmt_big(abs(ival))} | {idate}\n"
            if not insider_txt:
                insider_txt = "• Ma'lumot topilmadi\n"
        except:
            insider_txt = "• Ma'lumot topilmadi\n"

        # Choraklik hisobotlar
        try:
            earnings_txt = ""
            # Yangi usul
            eh = stock.earnings_history
            if eh is not None and not eh.empty:
                for _, row in eh.head(4).iterrows():
                    date_str = str(getattr(row, 'name', '') or '')[:10]
                    eps_est  = float(row.get('epsEstimate') or 0)
                    eps_act  = float(row.get('epsActual') or 0)
                    if eps_est and eps_act:
                        diff = ((eps_act - eps_est) / abs(eps_est)) * 100
                        icon = "✅" if diff >= 0 else "❌"
                        earnings_txt += f"• {date_str}: ${eps_act:.2f} (kut. ${eps_est:.2f}) {diff:+.1f}% {icon}\n"

            if not earnings_txt:
                ed = stock.earnings_dates
                if ed is not None and not ed.empty:
                    for idx, row in ed.head(4).iterrows():
                        date_str = str(idx)[:10]
                        eps_est  = float(row.get('EPS Estimate') or 0)
                        eps_act  = float(row.get('Reported EPS') or 0)
                        if eps_est and eps_act and eps_act != 0:
                            diff = ((eps_act - eps_est) / abs(eps_est)) * 100
                            icon = "✅" if diff >= 0 else "❌"
                            earnings_txt += f"• {date_str}: ${eps_act:.2f} (kut. ${eps_est:.2f}) {diff:+.1f}% {icon}\n"

            if not earnings_txt:
                earnings_txt = "• Ma'lumot topilmadi\n"
        except:
            earnings_txt = "• Ma'lumot topilmadi\n"

        # Yangiliklar
        news_txt  = get_stock_news(ticker, name)
        short_txt = f"{short_pct*100:.1f}% ({'Yuqori ⚠️' if short_pct > 0.1 else 'Normal ✅'})" if short_pct else "N/A"

        return (
            f"🔎 <b>{ticker.upper()} — {name}</b>\n"
            f"📍 {sector} | {exchange}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"

            f"💰 <b>ASOSIY:</b>\n"
            f"• Narx: <b>${price:,.2f}</b> ({change_sign}{change:.2f}% {change_icon})\n"
            f"• Bozor kap: {_fmt_big(mkt_cap)}\n"
            f"• 52 hafta: ${w52_low:,.2f} — ${w52_high:,.2f}\n"
            f"• 52 hafta pozitsiyasi: {w52_pos_txt}\n\n"

            f"📊 <b>FUNDAMENTAL:</b>\n"
            f"• P/E: {pe_ratio:.1f}\n"
            f"• P/B: {pb_ratio:.1f}\n"
            f"• P/S: {ps_ratio:.1f}\n"
            f"• EV/EBITDA: {ev_ebitda:.1f}\n"
            f"• EPS: ${eps:.2f} ({'+' if eps_growth >= 0 else ''}{eps_growth*100:.1f}%)\n"
            f"• Daromad: {_fmt_big(revenue)}\n"
            f"• Sof foyda: {_fmt_big(net_income)}\n"
            f"• Gross Margin: {_fmt_pct(gross_m)}\n"
            f"• Net Margin: {_fmt_pct(net_m)}\n"
            f"• ROE: {_fmt_pct(roe)}\n"
            f"• ROA: {_fmt_pct(roa)}\n"
            f"• Qarz/Kapital: {debt_eq:.2f}\n"
            f"• Free Cash Flow: {_fmt_big(fcf)}\n"
            f"• Dividend: ${dividend:.2f} ({div_yield*100:.2f}%)\n\n"

            f"📈 <b>TEXNIK:</b>\n"
            f"• RSI (14): {rsi_txt}\n"
            f"• MA50: {ma50_txt}\n"
            f"• MA200: {ma200_txt}\n"
            f"• Beta: {beta:.2f}\n"
            f"• Short Interest: {short_txt}\n\n"

            f"🏦 <b>ANALYST REYTINGI:</b>\n"
            f"• Xulosa: <b>{rec_txt}</b>\n"
            f"• Maqsad narx: ${target_price:,.2f}\n"
            f"• Analitiklar soni: {analyst_num}\n\n"

            f"🏛 <b>INSTITUTIONAL:</b>\n"
            f"{inst_txt}\n"

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

    except Exception as e:
        print(f"[ERROR] Stock data ({ticker}): {e}")
        return None
