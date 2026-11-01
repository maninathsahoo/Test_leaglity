from __future__ import annotations

import random
import string
import time
from datetime import date, timedelta
from pathlib import Path

from flask import current_app


class MockExtractionTimeout(Exception):
    pass


class MockExtractionFailure(Exception):
    pass


def _random_date_string() -> str:
    start = date(2020, 1, 1)
    offset = random.randint(0, 365 * 5)
    return (start + timedelta(days=offset)).isoformat()


def _random_value_for_variable(variable_name: str) -> str:
    name = variable_name.lower()
    if "date" in name:
        return _random_date_string()
    if "amount" in name or "rent" in name or "deposit" in name or "charge" in name:
        return f"{random.randint(1000, 999999)}.{random.randint(0, 99):02d}"
    if "period" in name or "days" in name:
        return str(random.randint(7, 180))
    if "law" in name or "clause" in name:
        words = ["India", "Delhi", "Maharashtra", "Standard", "Mutual", "30-day notice"]
        return random.choice(words) + " " + "".join(
            random.choices(string.ascii_letters, k=8)
        )
    return "".join(random.choices(string.ascii_letters + string.digits, k=12))


def extract(file_path: str | Path, variables: list[str]) -> dict[str, str]:
    """Mock extraction API: latency, optional timeout/failure, random values per variable."""
    path = Path(file_path)
    if not path.is_file():
        raise MockExtractionFailure(f"File not found: {path}")

    timeout_rate = float(current_app.config.get("MOCK_TIMEOUT_RATE", 0))
    fail_rate = float(current_app.config.get("MOCK_FAIL_RATE", 0))
    sleep_min = float(current_app.config.get("MOCK_SLEEP_MIN", 0.01))
    sleep_max = float(current_app.config.get("MOCK_SLEEP_MAX", 0.05))

    if random.random() < timeout_rate:
        time.sleep(sleep_max + 1)
        raise MockExtractionTimeout("Mock extraction timed out")

    if random.random() < fail_rate:
        raise MockExtractionFailure("Mock extraction failed")

    time.sleep(random.uniform(sleep_min, sleep_max))

    return {var: _random_value_for_variable(var) for var in variables}
