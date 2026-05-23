#!/usr/bin/env python3
"""
Azia Quant Bot — AI Module
OpenRouter API orqali AI tahlil va suhbat
"""

import requests
import os

OPENROUTER_API_KEY = os.environ.get(
    "OPENROUTER_API_KEY",
    "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"
)
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """Sen Azia Quant Botning professional moliyaviy AI yordamchisissan.

Qoidalar:
- Faqat moliya, investitsiya, trading, crypto, aksiya haqida javob ber
- O'zbek tilida javob ber
- Qisqa, aniq va professional bo'l
- Har doim risk haqida eslatib qo'y
- Hech qachon 100% kafolat berma
- Javoblar 400 so'zdan oshmasin

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


def ask_ai(user_message: str, history: list = None) -> str:
    """OpenRouter API ga savol yuborish"""
    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Tarix qo'shish (oxirgi 6 ta)
        if history:
            for h in history[-6:]:
                messages.append({
                    "role": h["role"],
                    "content": h["content"]
                })

        # Yangi savol
        messages.append({"role": "user", "content": user_message})

        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://t.me/AziaQuantBot",
                "X-Title": "Azia Quant Bot",
            },
            json={
                "model": "google/gemini-flash-1.5-8b",
                "messages": messages,
                "max_tokens": 1024,
                "temperature": 0.7,
            },
            timeout=30
        )

        if resp.status_code == 200:
            data    = resp.json()
            content = data['choices'][0]['message']['content']
            return content.strip()
        elif resp.status_code == 429:
            return "⏳ AI band. Biroz kuting va qayta urinib ko'ring."
        elif resp.status_code == 402:
            return "⏳ AI kredit tugadi. Admin bilan bog'laning."
        else:
            print(f"[ERROR] OpenRouter: {resp.status_code} — {resp.text[:200]}")
            return "❌ AI javob bermadi. Qayta urinib ko'ring."

    except Exception as e:
        print(f"[ERROR] OpenRouter API: {e}")
        return "❌ AI bilan bog'lanishda xatolik. Qayta urinib ko'ring."
