"""Çoklu LLM Adaptörü (Anthropic Claude, OpenAI, Google Gemini).

Kullanıcının tercih ettiği yapay zeka sağlayıcısına (Anthropic, OpenAI veya Gemini)
göre tek tip bir arayüz sunar. Harici ekstra kütüphane bağımlılığı olmadan (Anthropic
SDK kurulu gelir; OpenAI ve Gemini REST API üzerinden standart kütüphane ile çağrılır)
çalışır.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


PROVIDERS = {
    "anthropic": {
        "name": "Anthropic (Claude)",
        "models": ["claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5"],
        "default_model": "claude-sonnet-5",
        "env_var": "ANTHROPIC_API_KEY",
    },
    "openai": {
        "name": "OpenAI (ChatGPT)",
        "models": ["gpt-4o", "gpt-4o-mini", "o3-mini"],
        "default_model": "gpt-4o",
        "env_var": "OPENAI_API_KEY",
    },
    "gemini": {
        "name": "Google Gemini",
        "models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        "default_model": "gemini-2.0-flash",
        "env_var": "GEMINI_API_KEY",
    },
}


def get_available_providers() -> List[str]:
    """Sistemde API anahtarı tanımlı olan sağlayıcıları döner."""
    available = []
    for prov_key, info in PROVIDERS.items():
        if os.environ.get(info["env_var"]):
            available.append(prov_key)
    return available or ["anthropic"]


def call_anthropic(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = "claude-sonnet-5",
    api_key: Optional[str] = None,
) -> str:
    """Anthropic Claude API çağrısı."""
    import anthropic

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY tanımlı değil veya boş.")

    client = anthropic.Anthropic(api_key=key)
    kwargs: Dict[str, Any] = {
        "model": model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system_prompt:
        kwargs["system"] = system_prompt

    resp = client.messages.create(**kwargs)
    first = resp.content[0]
    return getattr(first, "text", "")


def call_openai(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = "gpt-4o",
    api_key: Optional[str] = None,
) -> str:
    """OpenAI API çağrısı (REST)."""
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY tanımlı değil veya boş.")

    url = "https://api.openai.com/v1/chat/completions"
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"OpenAI API Hatası ({e.code}): {err_body}")


def call_gemini(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = "gemini-2.0-flash",
    api_key: Optional[str] = None,
) -> str:
    """Google Gemini API çağrısı (REST)."""
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY tanımlı değil veya boş.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

    combined_text = prompt
    if system_prompt:
        combined_text = f"{system_prompt}\n\n{prompt}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": combined_text}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 4096,
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if not candidates:
                return ""
            parts = candidates[0].get("content", {}).get("parts", [])
            return parts[0].get("text", "") if parts else ""
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Gemini API Hatası ({e.code}): {err_body}")


def generate_llm_response(
    prompt: str,
    system_prompt: Optional[str] = None,
    provider: str = "anthropic",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> str:
    """Ortak LLM yanıt üretim fonksiyonu."""
    prov = provider.lower()
    selected_model = model or PROVIDERS.get(prov, {}).get("default_model", "claude-sonnet-5")

    if prov == "anthropic":
        return call_anthropic(prompt, system_prompt=system_prompt, model=selected_model, api_key=api_key)
    elif prov == "openai":
        return call_openai(prompt, system_prompt=system_prompt, model=selected_model, api_key=api_key)
    elif prov == "gemini":
        return call_gemini(prompt, system_prompt=system_prompt, model=selected_model, api_key=api_key)
    else:
        raise ValueError(f"Desteklenmeyen sağlayıcı: {provider}. Geçerli olanlar: {list(PROVIDERS.keys())}")
