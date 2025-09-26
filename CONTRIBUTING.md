# Contributing to Crypto News Aggregator

Thank you for your interest in contributing to our crypto news aggregator! This document outlines the contribution guidelines and best practices for working with our codebase.

## Table of Contents

- [Development Setup](#development-setup)
- [Test Guidelines](#test-guidelines)
- [Code Style](#code-style)
- [Pull Request Process](#pull-request-process)
- [CI/CD Pipeline](#cicd-pipeline)

## Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd crypto-news-aggregator
   ```

2. **Set up the development environment**
   ```bash
   # Install Poetry (if not already installed)
   curl -sSL https://install.python-poetry.org | python3 -

   # Install dependencies
   poetry install
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run tests**
   ```bash
   # Run all tests
   poetry run pytest

   # Run only stable tests
   poetry run pytest -m "stable"

   # Run only broken tests
   poetry run pytest -m "broken"
   ```

## Test Guidelines

### Test Categories

Our test suite uses pytest markers to categorize tests based on their current status:

#### Stable Tests
- Tests that pass consistently
- Should be run in CI and block merges if they fail
- Mark new working tests with this marker

#### Broken Tests
- Tests that fail consistently due to known issues
- Should be run in CI but not block merges
- Include a `reason` parameter explaining why the test is broken

#### Flaky Tests
- Tests that sometimes pass and sometimes fail
- Should be run in CI but not block merges
- Include a `reason` parameter explaining the flakiness

### Rules for Marking New Tests

1. **New tests should be marked as stable** by default
2. **If a test fails due to a known issue**, mark it as broken with a descriptive reason
3. **If a test exhibits intermittent behavior**, mark it as flaky with a reason
4. **Always include a reason** when marking tests as broken or flaky

### Example Test Markings

```python
import pytest

@pytest.mark.stable
def test_user_authentication():
    """Test that user authentication works correctly."""
    # Test implementation
    assert True

@pytest.mark.broken(reason="Database connection issue in test environment")
def test_database_migration():
    """Test database migration functionality."""
    # Test implementation that currently fails
    assert False  # This will fail but won't break CI

@pytest.mark.flaky(reason="External API rate limiting causes intermittent failures")
def test_external_api_call():
    """Test external API integration."""
    # Test implementation that sometimes fails
    assert True  # This might fail intermittently
```

## Code Style

### Python Code Style
- Follow PEP 8 guidelines
- Use Black for code formatting: `black --check .`
- Maximum line length: 88 characters
- Use type hints for function parameters and return values

### Import Organization
```python
# Standard library imports
import os
from typing import Dict, List

# Third-party imports
import pytest
from fastapi import FastAPI

# Local imports
from crypto_news_aggregator.core import NewsCollector
```

## Pull Request Process

### Before Submitting a PR

1. **Run the full test suite**
   ```bash
   poetry run pytest
   ```

2. **Check code formatting**
   ```bash
   black --check .
   ```

3. **Update test markers** if you've fixed any broken tests
4. **Add tests** for new functionality
5. **Update documentation** if needed

### PR Requirements

- **Title**: Use conventional commit format (e.g., `feat: add user authentication`)
- **Description**: Explain what changes were made and why
- **Tests**: Include tests for new functionality
- **Breaking changes**: Clearly document any breaking changes

### Branch Naming Convention

- Feature branches: `feature/description-of-feature`
- Bug fixes: `fix/description-of-bug`
- Documentation: `docs/description-of-docs-update`

## CI/CD Pipeline

### CI Behavior

Our GitHub Actions workflow runs two separate jobs:

#### Stable Tests Job
- **Runs**: `pytest -m "stable"` + Black linting
- **Behavior**: Fails the entire workflow if tests fail
- **Purpose**: Ensures core functionality works correctly

#### Broken/Flaky Tests Job
- **Runs**: `pytest -m "broken or flaky"`
- **Behavior**: Continues even if tests fail (`continue-on-error: true`)
- **Purpose**: Tracks progress on known issues without blocking development

### CI Workflow Triggers

The CI pipeline runs on:
- Pull requests to `main`
- Pushes to `main`
- Manual workflow dispatch

### Adding Tests Safely

1. **Start with a working test**
   ```python
   @pytest.mark.stable
   def test_new_feature():
       """Test the new feature works as expected."""
       # Implementation
       assert result == expected_value
   ```

2. **If the test fails due to environment issues**, mark it as broken
   ```python
   @pytest.mark.broken(reason="Requires external API key not available in CI")
   def test_external_service_integration():
       """Test integration with external service."""
       # This test will fail but won't break the CI
       assert False
   ```

3. **Fix the underlying issue** and update the marker
   ```python
   @pytest.mark.stable  # Changed from broken
   def test_external_service_integration():
       """Test integration with external service."""
       # Now this test passes and blocks CI if it fails
       assert True
   ```

### Best Practices for Test Development

1. **Write tests first** (TDD approach)
2. **Keep tests focused** and testing single behaviors
3. **Use descriptive test names** that explain what is being tested
4. **Mock external dependencies** to ensure tests are fast and reliable
5. **Clean up after tests** to avoid state pollution between test runs

### Debugging Failing Tests

1. **Run tests locally** to see detailed output
   ```bash
   poetry run pytest -v -s test_file.py::test_function_name
   ```

2. **Check test markers** to understand expected behavior
3. **Review CI logs** for environment-specific issues
4. **Update test markers** if issues are resolved

## Getting Help

- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Discussions**: Use GitHub Discussions for questions and general discussion
- **Documentation**: Check the README.md and docs/ directory for more information

---

Thank you for contributing to our crypto news aggregator! Your contributions help make the project better for everyone.
