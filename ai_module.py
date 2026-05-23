#!/usr/bin/env python3
"""
Azia Quant Bot — AI Module
Google Gemini API orqali AI tahlil va suhbat
"""

import requests
from config import GEMINI_API_KEY

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

SYSTEM_PROMPT = """Sen Azia Quant Botning professional moliyaviy AI yordamchisissan.

Qoidalar:
- Faqat moliya, investitsiya, trading, crypto, aksiya haqida javob ber
- O'zbek tilida javob ber
- Qisqa, aniq va professional bo'l
- Har doim risk haqida eslatib qo'y
- Hech qachon 100% kafolat berma
- Javoblar 300 so'zdan oshmasin

Mutaxassislik sohalaring:
- Aksiya tahlili (fundamental va texnik)
- Crypto tahlili
- Risk menejment
- Portfolio diversifikatsiya
- Trading strategiyalari
- DeFi va Web3
- Moliyaviy atamalar tushuntirish

Agar moliyaviy bo'lmagan savol bo'lsa:
"Men faqat moliyaviy mavzularda yordam bera olaman." de."""


def ask_gemini(user_message: str, history: list = None) -> str:
    """Gemini API ga savol yuborish"""
    try:
        # Conversation history
        contents = []

        # System prompt ni birinchi user xabar sifatida qo'shamiz
        contents.append({
            "role": "user",
            "parts": [{"text": SYSTEM_PROMPT}]
        })
        contents.append({
            "role": "model",
            "parts": [{"text": "Yaxshi! Men Azia Quant Botning moliyaviy AI yordamchisiman. Moliya, investitsiya, trading va crypto haqida savol bering!"}]
        })

        # Tarix qo'shish
        if history:
            for h in history[-6:]:  # Oxirgi 6 ta xabar
                contents.append(h)

        # Yangi savol
        contents.append({
            "role": "user",
            "parts": [{"text": user_message}]
        })

        resp = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json={
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 1024,
                }
            },
            timeout=30
        )

        if resp.status_code == 200:
            data     = resp.json()
            text     = data['candidates'][0]['content']['parts'][0]['text']
            return text.strip()
        elif resp.status_code == 429:
            return "⏳ AI so'rov limiti tugadi. Biroz kuting va qayta urinib ko'ring."
        else:
            print(f"[ERROR] Gemini: {resp.status_code} — {resp.text[:200]}")
            return "❌ AI javob bermadi. Qayta urinib ko'ring."

    except Exception as e:
        print(f"[ERROR] Gemini API: {e}")
        return "❌ AI bilan bog'lanishda xatolik. Qayta urinib ko'ring."
