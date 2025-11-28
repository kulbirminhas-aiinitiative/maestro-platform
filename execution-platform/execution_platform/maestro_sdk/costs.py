from __future__ import annotations
from typing import Optional
from .types import Usage

PRICING = {
    "mock": {"input_tokens": 0.0, "output_tokens": 0.0},
    "anthropic": {"input_tokens": 0.003/1000.0, "output_tokens": 0.015/1000.0},
    "openai": {"input_tokens": 0.0025/1000.0, "output_tokens": 0.010/1000.0},
}

def compute_cost(usage: Usage, provider: str) -> float:
    p = PRICING.get(provider) or PRICING["mock"]
    it = usage.input_tokens or 0
    ot = usage.output_tokens or 0
    return round(it * p["input_tokens"] + ot * p["output_tokens"], 6)
