"""Excel portfolio loader - reads holdings from a pre-defined column schema."""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

import pandas as pd

from src.exceptions import ValidationError
from src.models import VALID_CURRENCIES, Holding, detect_market

_REQUIRED_COLUMNS = {"ticker", "quantity", "purchase price", "currency"}


class ExcelParser:
    """Parses an Excel file containing portfolio holdings into a list of Holding objects."""

    def parse(self, source: str | Path | BinaryIO) -> list[Holding]:
        """Parse the given Excel file and return a list of Holding objects."""
        df = pd.read_excel(source, engine="openpyxl")

        # Normalize column names
        df.columns = [str(c).strip().lower() for c in df.columns]

        if df.empty:
            return []

        missing = _REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValidationError(f"Missing required columns: {sorted(missing)}")

        holdings: list[Holding] = []
        for row_idx, row in df.iterrows():
            row_num = int(str(row_idx)) + 2  # 1-based + header

            ticker = row["ticker"]
            if not isinstance(ticker, str) or not ticker.strip():
                raise ValidationError(f"Row {row_num}: 'ticker' must be a non-empty string")
            ticker = ticker.strip()

            quantity = row["quantity"]
            try:
                quantity = float(quantity)
            except (TypeError, ValueError) as exc:
                raise ValidationError(f"Row {row_num}: 'quantity' must be a number") from exc
            if quantity <= 0:
                raise ValidationError(f"Row {row_num}: 'quantity' must be positive, got {quantity}")

            price = row["purchase price"]
            try:
                price = float(price)
            except (TypeError, ValueError) as exc:
                raise ValidationError(f"Row {row_num}: 'purchase price' must be a number") from exc
            if price < 0:
                raise ValidationError(
                    f"Row {row_num}: 'purchase price' cannot be negative, got {price}"
                )

            currency = row["currency"]
            if not isinstance(currency, str) or currency.strip().upper() not in VALID_CURRENCIES:
                raise ValidationError(
                    f"Row {row_num}: 'currency' must be one of {sorted(VALID_CURRENCIES)}, "
                    f"got '{currency}'"
                )

            currency = currency.strip().upper()

            holdings.append(
                Holding(
                    ticker=ticker,
                    quantity=quantity,
                    price=price,
                    currency=currency,
                    market=detect_market(ticker),
                )
            )

        return holdings
