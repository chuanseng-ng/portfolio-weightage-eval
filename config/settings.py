"""Environment-variable-backed settings for the portfolio weightage evaluator."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Settings for the portfolio weightage evaluator, loaded from environment variables."""

    brokerage_api_key: str
    base_currency: str

    @classmethod
    def from_env(cls) -> Settings:
        """Factory method to create Settings instance from environment variables."""
        return cls(
            brokerage_api_key=os.environ.get("BROKERAGE_API_KEY", ""),
            base_currency=os.environ.get("BASE_CURRENCY", "SGD"),
        )
