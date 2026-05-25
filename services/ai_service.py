#!/usr/bin/env python3
"""
Azia Quant Bot — AI Service
Claude API orqali aqlli tahlil
"""

import logging
import requests
from typing import Optional, List, Dict

from config import CLAUDE_API_KEY, CLAUDE_MODEL
from database import cache_get, cache_set

logger = logging.getLogger(__name__)

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"


class AIService:
    """Claude API servisi"""

    def __init__(self):
        self.api_key = CLAUDE_API_KEY
        self.model   = CLAUDE_MODEL

    def _is_available(self) -> bool:
        return bool(self.api_key)

    def _call(self, system: str, messages: List[Dict], max_tokens: int = 1000) -> Optional[str]:
        """Claude API ga so'rov"""
        try:
            if not self._is_available():
                return None

            resp = requests.post(
                CLAUDE_API_URL,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": messages
                },
                timeout=30
            )
            if resp.status_code == 200:
                return resp.json()["content"][0]["text"]
            logger.error(f"Claude API xato: {resp.status_code} {resp.text[:200]}")
        except Exception as e:
            logger.error(f"Claude API xato: {e}")
        return None

    # ── Screener tahlili ─────────────────────────────────────────

    def analyze_screener(self, ticker: str, screener_data: str, ticker_type: str = "crypto") -> Optional[str]:
        """Screener natijasini AI tahlil qilish"""
        cache_key = f"ai_screener_{ticker}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        system = (
            "Siz professional moliyaviy tahlilchisiz. "
            "O'zbek tilida qisqa, aniq va tushunarli tahlil yozing. "
            "Maksimal 200 so'z. Texnik terminlarni oddiy tilda tushuntiring. "
            "Hech qachon 100% kafolat bermang."
        )

        user_msg = (
            f"{ticker_type.upper()} aktivini tahlil qiling:\n\n"
            f"{screener_data}\n\n"
            f"Quyidagilarni O'zbek tilida yozing:\n"
            f"1. Hozirgi holat (1-2 gap)\n"
            f"2. Kuchli tomonlari\n"
            f"3. Zaif tomonlari\n"
            f"4. Qisqa muddatli taxmin\n"
            f"5. Tavsiya (Sotib ol / Kuzat / Sot)"
        )

        result = self._call(system, [{"role": "user", "content": user_msg}])
        if result:
            formatted = f"🤖 <b>AI TAHLIL:</b>\n\n{result}"
            cache_set(cache_key, formatted, ttl=1800)
            return formatted
        return None

    # ── Foydalanuvchi savoli ─────────────────────────────────────

    def answer_question(self, question: str, history: List[Dict] = []) -> Optional[str]:
        """Foydalanuvchi savoliga javob"""
        system = (
            "Siz 'Azia Quant Bot' ning AI moliyaviy yordamchisisiz. "
            "O'zbek tilida professional, aniq va foydali javob bering. "
            "Moliyaviy maslahat berganingizda doim risk haqida eslatib o'ting. "
            "Qisqa va tushunarli bo'ling."
        )

        messages = history[-8:] + [{"role": "user", "content": question}]
        return self._call(system, messages, max_tokens=800)

    # ── Kunlik briefing ──────────────────────────────────────────

    def generate_daily_briefing(self, market_data: str) -> Optional[str]:
        """Har kuni ertalab bozor tahlili"""
        cache_key = "daily_briefing"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        system = (
            "Siz professional moliyaviy tahlilchisiz. "
            "Har kuni ertalab O'zbek tilida bozor xulasasini yozing. "
            "Qisqa, aniq va foydali bo'lsin. Maksimal 300 so'z."
        )

        user_msg = (
            f"Bugungi bozor ma'lumotlari:\n\n{market_data}\n\n"
            f"Quyidagilarni O'zbek tilida yozing:\n"
            f"1. Kecha nima bo'ldi (1-2 gap)\n"
            f"2. Bugun e'tibor berish kerak bo'lgan 3 ta narsa\n"
            f"3. BTC va ETH qisqa tahlil\n"
            f"4. Bugungi kayfiyat (Bullish/Bearish/Neytral)"
        )

        result = self._call(system, [{"role": "user", "content": user_msg}], max_tokens=600)
        if result:
            briefing = (
                f"☀️ <b>KUNLIK BRIFING</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{result}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 <i>Azia Quant Bot AI tahlili</i>"
            )
            cache_set(cache_key, briefing, ttl=3600)
            return briefing
        return None

    # ── Yangilik tahlili ─────────────────────────────────────────

    def analyze_news(self, news_list: List[Dict]) -> Optional[str]:
        """Yangiliklar O'zbek tilida tahlil"""
        if not news_list:
            return None

        cache_key = f"ai_news_{hash(str(news_list))}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        system = (
            "Siz moliyaviy yangiliklar tahlilchisisiz. "
            "Yangiliklar ro'yxatini O'zbek tilida qisqa tahlil qiling. "
            "Bozorga ta'sirini baholang."
        )

        news_txt = "\n".join([f"- {n['title']}" for n in news_list[:5]])
        user_msg = (
            f"Quyidagi yangiliklar bozorga qanday ta'sir qiladi?\n\n"
            f"{news_txt}\n\n"
            f"O'zbek tilida qisqa tahlil yozing (maksimal 150 so'z)."
        )

        result = self._call(system, [{"role": "user", "content": user_msg}], max_tokens=400)
        if result:
            cache_set(cache_key, result, ttl=1800)
            return result
        return None

    # ── Risk/Reward tahlil ───────────────────────────────────────

    def analyze_risk_reward(self, ticker: str, price: float,
                             support: float, resistance: float) -> Optional[str]:
        """Risk/Reward tahlil"""
        system = (
            "Siz risk menejment mutaxassisisiz. "
            "O'zbek tilida aniq va qisqa tahlil yozing."
        )

        user_msg = (
            f"{ticker} uchun Risk/Reward tahlil:\n"
            f"• Hozirgi narx: ${price:,.2f}\n"
            f"• Support: ${support:,.2f}\n"
            f"• Resistance: ${resistance:,.2f}\n\n"
            f"Quyidagilarni hisoblang:\n"
            f"1. Stop-loss (support dan pastda)\n"
            f"2. Take-profit darajalari (TP1, TP2, TP3)\n"
            f"3. Risk/Reward nisbati\n"
            f"4. Tavsiya"
        )

        return self._call(system, [{"role": "user", "content": user_msg}], max_tokens=400)

    # ── Portfel tahlil ───────────────────────────────────────────

    def analyze_portfolio(self, portfolio: List[Dict]) -> Optional[str]:
        """Portfel tahlili"""
        if not portfolio:
            return None

        system = (
            "Siz portfel menejeri siz. "
            "O'zbek tilida portfelni tahlil qiling."
        )

        portfolio_txt = "\n".join([
            f"• {p['ticker']}: {p.get('quantity', 0)} dona"
            for p in portfolio
        ])

        user_msg = (
            f"Mening portfelim:\n{portfolio_txt}\n\n"
            f"Quyidagilarni O'zbek tilida yozing:\n"
            f"1. Diversifikatsiya darajasi\n"
            f"2. Risklar\n"
            f"3. Tavsiyalar"
        )

        return self._call(system, [{"role": "user", "content": user_msg}], max_tokens=400)


# Global instance
ai_service = AIService()
