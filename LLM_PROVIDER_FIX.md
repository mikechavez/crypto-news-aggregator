# LLM Provider Configuration Fix

## Issue
The RSS fetcher was failing with `AttributeError: 'OpenAIProvider' object has no attribute 'extract_entities_batch'` because:
1. Default `LLM_PROVIDER` was set to `"openai"` in config
2. `OpenAIProvider` class was incomplete (missing `extract_entities_batch` method)
3. System was attempting to use OpenAI provider instead of Anthropic

## Solution
Fixed the configuration to use only Anthropic provider:

### Changes Made

**Branch**: `fix/llm-provider-anthropic-only`

1. **`src/crypto_news_aggregator/core/config.py`**
   - Changed default `LLM_PROVIDER` from `"openai"` to `"anthropic"` (line 40)

2. **`src/crypto_news_aggregator/llm/factory.py`**
   - Removed `OpenAIProvider` import
   - Removed `"openai"` from `PROVIDER_MAP`
   - Updated `get_llm_provider()` default fallback to `"anthropic"`
   - Removed OpenAI-specific API key handling
   - Added Sentient provider API key handling for completeness

### Testing
✅ All LLM-related tests pass:
- `tests/background/test_entity_extraction.py` - 11/11 passed
- `tests/background/test_rss_fetcher_enrichment.py` - LLM error handling passed
- `tests/test_performance_monitoring.py` - LLM operation logging passed

✅ Verified provider initialization:
```python
from src.crypto_news_aggregator.llm.factory import get_llm_provider
provider = get_llm_provider()
# Returns: AnthropicProvider with extract_entities_batch method
```

### Deployment Notes

**Railway Environment Variables**:
- ✅ `LLM_PROVIDER` can be removed (defaults to `"anthropic"` now)
- ✅ `OPENAI_API_KEY` can be removed (no longer used)
- ⚠️ Ensure `ANTHROPIC_API_KEY` is set

**Available Providers**:
- `anthropic` (default) - Full implementation with entity extraction
- `sentient` - Alternative provider (if configured)

### Impact
- RSS fetcher entity extraction will now work correctly
- System exclusively uses Anthropic's Claude models
- No more OpenAI provider initialization attempts

### Commit
```
fix: configure LLM provider to use only Anthropic

- Changed default LLM_PROVIDER from 'openai' to 'anthropic' in config.py
- Removed OpenAI provider from factory.py imports and PROVIDER_MAP
- Updated provider initialization to handle only anthropic and sentient
- Removed OpenAI-specific API key handling from factory

This fixes the AttributeError where OpenAIProvider was missing the
extract_entities_batch method. The system now exclusively uses
AnthropicProvider which has full implementation.

Fixes RSS fetcher entity extraction failures.
```

### Next Steps
1. ✅ Push branch to origin
2. ⏳ Create PR to merge into main
3. ⏳ After merge, verify Railway deployment
4. ⏳ Monitor RSS fetcher logs for successful entity extraction
