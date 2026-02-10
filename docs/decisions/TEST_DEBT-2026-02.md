# Test Debt Documentation

This document tracks known test issues and technical debt in the test suite. It serves as a reference for future test improvements.

## Last Updated
2025-07-05

## High Priority

### 1. API Test Failures
- **File**: `tests/api/test_article_endpoints.py`
  - **Issue**: Route mismatches and authentication issues
  - **Details**:
    - Tests are using trailing slashes in URLs where they shouldn't
    - Missing API key authentication in test requests
    - Test data doesn't match expected API response format
  - **Impact**: Prevents API integration tests from passing
  - **Suggested Fix**:
    - Update test URLs to match actual routes
    - Add proper authentication headers
    - Align test data with API response models

## Medium Priority

### 1. Async Test Issues
- **Files**: Multiple files in `scripts/` and `tests/`
  - **Issue**: Tests failing with "async def functions not natively supported"
  - **Impact**: Many integration and script tests are skipped or failing
  - **Suggested Fix**:
    - Ensure tests use `pytest.mark.asyncio`
    - Use `AsyncMock` for async function mocks
    - Update test runners to properly handle async tests

### 2. News Collector Tests
- **Files**:
  - `tests/core/test_news_collector.py`
  - `tests/test_news_collector.py`
- **Issues**:
  - Missing imports (`timezone`, `text`)
  - Test data structure mismatches
  - Async/await issues
- **Impact**: Core functionality tests are not running

## Low Priority

### 1. Pydantic Deprecation Warnings
- **Files**: Throughout the codebase
  - **Issue**: Using deprecated Pydantic v1 features
  - **Impact**: Warnings in test output, future compatibility risk
  - **Suggested Fix**:
    - Update to use Pydantic v2 patterns
    - Replace `json_encoders` with custom serializers
    - Update `Config` classes to use `ConfigDict`

## Test Improvement Backlog

### 1. Test Coverage
- [ ] Add tests for error cases
- [ ] Increase unit test coverage for core services
- [ ] Add integration tests for API endpoints

### 2. Test Data Management
- [ ] Create reusable test fixtures
- [ ] Set up test database with consistent data
- [ ] Add test data validation

### 3. Test Performance
- [ ] Identify and fix slow-running tests
- [ ] Add test parallelization
- [ ] Implement test data cleanup

## Notes
- The core notification service tests are passing and provide good coverage
- API functionality should be manually verified until tests are fixed
- Consider adding a test CI/CD pipeline to prevent regressions
