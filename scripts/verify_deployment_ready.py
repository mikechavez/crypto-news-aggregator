#!/usr/bin/env python3
"""Utility script to verify deployment readiness before pushing to main.

This script performs three checks:
1. Ensures required environment variables are populated.
2. Validates that critical application modules import without raising errors.
3. Executes the smoke test suite with pytest to confirm core flows still pass.

The script exits with status code 0 when every check succeeds, and 1 otherwise.
"""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"

# Ensure the application source tree is on sys.path for module import checks.
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

SMOKE_TEST_COMMAND = ["poetry", "run", "pytest", "tests/smoke/", "-v"]

# Environment variables that must be set for the application to boot successfully.
REQUIRED_ENV_VARS = (
    "MONGODB_URI",
    "SECRET_KEY",
    "API_KEY",
)

# Modules that have historically raised import errors when dependencies or paths were misconfigured.
# Each maps to a failure we have seen on Railway:
# - main: missing optional dependencies or settings import errors prevented app boot.
# - core.config: env parsing regressions made Settings raise during import time.
# - api.v1.articles: router import errors due to circular dependencies and missing models.
# - background.price_monitor: background scheduler regressions and optional dependency imports.
CRITICAL_MODULES = (
    "crypto_news_aggregator.main",  # ASGI entrypoint used by Railway
    "crypto_news_aggregator.core.config",  # Settings model and env parsing
    "crypto_news_aggregator.api.v1.articles",  # Core API router
    "crypto_news_aggregator.background.price_monitor",  # Background task registry
    "crypto_news_aggregator.db.mongodb",  # Database manager initialization
)


def load_dotenv_if_available() -> None:
    """Load environment variables from a .env file when python-dotenv is installed."""

    dotenv_path = PROJECT_ROOT / ".env"
    if not dotenv_path.exists():
        return

    try:
        from dotenv import load_dotenv  # type: ignore
    except ModuleNotFoundError:
        return

    load_dotenv(dotenv_path, override=False)


class CheckResult:
    def __init__(self, name: str) -> None:
        self.name = name
        self.success = True
        self.messages: list[tuple[str, bool]] = []

    def add_failure(self, message: str) -> None:
        self.success = False
        self.messages.append((message, False))

    def add_success(self, message: str) -> None:
        self.messages.append((message, True))


def print_heading(title: str) -> None:
    print(f"\n=== {title} ===")


def check_environment_variables(required_vars: Iterable[str]) -> CheckResult:
    result = CheckResult("Environment Variables")
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            result.add_failure(f"Missing required environment variable: {var}")
        else:
            result.add_success(f"{var} is set")
    if result.success:
        result.add_success("All required environment variables are present")
    return result


def check_module_imports(modules: Iterable[str]) -> CheckResult:
    result = CheckResult("Module Imports")
    for module in modules:
        try:
            importlib.import_module(module)
        except Exception as exc:  # noqa: BLE001
            result.add_failure(f"Failed to import {module}: {exc}")
        else:
            result.add_success(f"Imported {module}")
    if result.success:
        result.add_success("All critical modules imported successfully")
    return result


def run_smoke_tests(command: list[str]) -> CheckResult:
    result = CheckResult("Smoke Tests")
    try:
        completed = subprocess.run(
            command,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        result.add_failure(f"Failed to execute smoke tests: {exc}")
        return result

    if completed.returncode != 0:
        result.add_failure(
            "Smoke tests failed. Review the output above to address failing tests."
        )
        result.messages.append((completed.stdout, False))
    else:
        result.add_success("Smoke tests passed")
    return result


def main() -> int:
    print_heading("Context Owl Deployment Safety Check")
    print(f"Project root: {PROJECT_ROOT}")

    load_dotenv_if_available()

    checks = (
        check_environment_variables(REQUIRED_ENV_VARS),
        check_module_imports(CRITICAL_MODULES),
        run_smoke_tests(SMOKE_TEST_COMMAND),
    )

    exit_code = 0
    for check in checks:
        print_heading(check.name)
        for message, is_success in check.messages:
            status = "OK" if is_success else "WARN"
            print(f"[{status}] {message}")
        if not check.success:
            exit_code = 1

    if exit_code == 0:
        print("\nAll checks passed. Safe to deploy.")
    else:
        print("\nOne or more checks failed. Resolve the issues before deploying.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
