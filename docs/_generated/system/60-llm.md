# LLM Integration & Briefing Generation

## Overview

The briefing agent uses Anthropic's Claude API to generate crypto market briefings. This document describes LLM initialization, the generation prompt structure, model selection, quality refinement, and cost tracking. Understanding this layer enables debugging generation failures and optimizing LLM usage.

**Anchor:** `#llm-integration-generation`

## Architecture

### Key Components

- **LLM Provider Factory**: Initializes and returns Claude client based on configuration
- **BriefingAgent**: Orchestrates briefing generation using LLM calls
- **Prompt Templates**: System prompts, generation prompts, critique/refinement prompts
- **Self-Refine Loop**: Quality assurance through iterative refinement
- **Cost Tracker**: Logs token usage for billing and optimization
- **Model Fallback**: Automatic fallback to cheaper models on API errors

### Data Flow

1. **Gather Inputs** → Collect signals, narratives, patterns, and memory context
2. **Build Prompts** → Generate system prompt and generation prompt with context
3. **Call LLM** → Make API request to Claude (try primary model, fallback to cheaper models)
4. **Parse Response** → Extract narrative, insights, recommendations from LLM output
5. **Self-Refine** → Critique output and refine if quality issues detected
6. **Track Cost** → Log token usage for cost monitoring
7. **Save Briefing** → Persist final briefing to MongoDB

## Implementation Details

### LLM Client Initialization

**File:** `src/crypto_news_aggregator/llm/factory.py:15-50`

The factory function returns the configured LLM provider:

```python
def get_llm_provider() -> LLMProvider:
    """Get the singleton LLMProvider instance."""
    settings = get_settings()
    provider_name = getattr(settings, "LLM_PROVIDER", "anthropic").lower()

    if provider_name == "anthropic":
        return AnthropicProvider(
            api_key=settings.ANTHROPIC_API_KEY,
            model_name=settings.ANTHROPIC_DEFAULT_MODEL
        )
```

**Key configuration:**
- `LLM_PROVIDER`: Set to "anthropic" (supports other providers via strategy pattern)
- `ANTHROPIC_API_KEY`: Loaded from environment (required)
- `ANTHROPIC_DEFAULT_MODEL`: Defaults to fallback if not specified

**File:** `src/crypto_news_aggregator/core/config.py:40-47`

Model configuration:
- `ANTHROPIC_DEFAULT_MODEL`: "claude-3-haiku-20240307" (fallback)
- `ANTHROPIC_ENTITY_MODEL`: "claude-3-5-haiku-20241022" (entity extraction)
- `ANTHROPIC_ENTITY_FALLBACK_MODEL`: "claude-3-5-sonnet-20241022" (expensive fallback)

### Briefing Generation Workflow

**File:** `src/crypto_news_aggregator/services/briefing_agent.py:111-165`

High-level generation flow:

```python
async def generate_briefing(
    self,
    briefing_type: str,  # "morning", "afternoon", "evening"
    force: bool = False,
    is_smoke: bool = False,
    task_id: str | None = None,
) -> Optional[Dict[str, Any]]:
    # 1. Check if briefing already exists (unless force=true)
    exists = await check_briefing_exists_for_slot(briefing_type)
    if exists and not force:
        return None  # Skip, already generated

    # 2. Gather inputs (signals, narratives, patterns, memory)
    briefing_input = await self._gather_inputs(briefing_type)

    # 3. Generate initial briefing with LLM
    generated = await self._generate_with_llm(briefing_input)

    # 4. Self-refine for quality (up to 2 iterations)
    generated = await self._self_refine(generated, briefing_input)

    # 5. Save to database
    briefing_doc = await self._save_briefing(
        briefing_type, briefing_input, generated, is_smoke, task_id
    )

    return briefing_doc
```

### LLM API Request

**File:** `src/crypto_news_aggregator/services/briefing_agent.py:766-834`

Direct API call to Anthropic (bypasses Python SDK to avoid client initialization issues):

```python
async def _call_llm(
    self,
    prompt: str,
    system_prompt: str,
    max_tokens: int = 2048,
) -> str:
    """Call the LLM API with fallback models."""
    models_to_try = [
        "claude-sonnet-4-5-20250929",          # Primary (line 46)
        "claude-3-5-haiku-20241022",           # Fallback 1 (line 48)
        "claude-3-haiku-20240307",             # Fallback 2 (line 49)
    ]

    for model in models_to_try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",  # Line 779
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=120,
            )
```

**Key behaviors:**
- Uses **Sonnet 4.5** (primary model) for instruction following quality
- Falls back to **Haiku** if API returns 403 Forbidden
- Falls back further to **old Haiku** if 5 retries exhausted
- Tracks tokens for cost monitoring (line 804-817)
- Timeout: 120 seconds per request

### System Prompt

**File:** `src/crypto_news_aggregator/services/briefing_agent.py:402-425`

The system prompt establishes role and constraints:

```
You are a senior crypto market analyst writing a {time_context} briefing memo.

Your role is to synthesize ONLY the narratives listed below into an insightful briefing.

IMPORTANT RULES:
1. Use ONLY the narratives provided—do NOT add external knowledge
2. Focus on explaining narrative themes and their market implications
3. Keep key_insights concise (max 3-5 per briefing)
4. Recommendations must reference narratives provided, not external
5. Be accurate—if data conflicts with your training, trust the data provided
```

The prompt is dynamically set to "morning" or "evening" context (line 404).

### Generation Prompt Structure

**File:** `src/crypto_news_aggregator/services/briefing_agent.py:433-650` (estimated)

The generation prompt includes:

1. **Briefing Type & Context**: "Generate a morning briefing" with current time
2. **Recent Signals** (20 signals max): Market events, price movements, sentiment
3. **Active Narratives** (15 max): Story threads with entities and recent articles
4. **Detected Patterns** (8 max): Market anomalies, correlations, divergences
5. **Memory Context** (feedback history): Past analyst feedback and preferences
6. **Instructions**: Output format (JSON with narrative, key_insights, recommendations)

Example instructions in prompt:
```
Generate a structured briefing with:
- narrative (2-3 paragraphs synthesizing the narratives)
- key_insights (3-5 most important takeaways)
- entities_mentioned (people, companies, projects discussed)
- detected_patterns (market patterns observed)
- recommendations (2-3 narratives to read for context)

Output as JSON only, no markdown.
```

### Self-Refine Quality Loop

**File:** `src/crypto_news_aggregator/services/briefing_agent.py:329-400`

Two-iteration quality assurance:

**Iteration 1:**
1. Generate briefing (line 319-327)
2. Build critique prompt evaluating: completeness, accuracy, grammar, actionability
3. Call LLM to get critique response (line 359-363)
4. Parse critique: Does it say "PASS" or list issues? (line 366)
5. If PASS → Return with "Quality passed on iteration 1" (line 371)
6. If issues → Build refinement prompt with critique (line 378-379)

**Iteration 2:**
1. Call LLM with refinement prompt (line 382-386)
2. Parse refined response (line 388)
3. Check quality again
4. If PASS → Return with "Quality passed on iteration 2"
5. If fail → Log warning, reduce confidence to 0.6, add "Max refinement reached" (line 391-398)

**Cost of refinement:**
- Primary generation: 4,000 max tokens (Sonnet, ~$0.02)
- Critique 1: 1,024 max tokens (Sonnet, ~$0.005)
- Refinement 1: 4,000 max tokens (Sonnet, ~$0.02)
- Critique 2: 1,024 max tokens (Sonnet, ~$0.005)
- **Total: ~$0.05 per briefing** (before fallbacks)

### Cost Tracking

**File:** `src/crypto_news_aggregator/services/briefing_agent.py:809-817`

Token usage is logged asynchronously:

```python
# Extract usage from LLM response
usage = data.get("usage", {})
input_tokens = usage.get("input_tokens", 0)
output_tokens = usage.get("output_tokens", 0)

# Track asynchronously (non-blocking)
tracker = await self._get_cost_tracker()
asyncio.create_task(
    tracker.track_call(
        operation="briefing_generation",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached=False
    )
)
```

Cost is tracked in `llm_usage` collection for billing and optimization.

### Response Parsing

**File:** `src/crypto_news_aggregator/services/briefing_agent.py:730-764` (estimated)

LLM response is parsed from JSON:

```python
def _parse_briefing_response(self, response_text: str) -> GeneratedBriefing:
    """Parse JSON response from LLM into GeneratedBriefing dataclass."""
    try:
        data = json.loads(response_text)
        return GeneratedBriefing(
            narrative=data.get("narrative", ""),
            key_insights=data.get("key_insights", []),
            entities_mentioned=data.get("entities_mentioned", []),
            detected_patterns=data.get("detected_patterns", []),
            recommendations=data.get("recommendations", []),
            confidence_score=data.get("confidence_score", 0.85),
        )
    except json.JSONDecodeError:
        logger.error(f"Failed to parse LLM response: {response_text[:200]}")
        # Return low-confidence placeholder
        return GeneratedBriefing(...)
```

## Operational Checks

### Health Verification

**Check 1: LLM provider is accessible**
```bash
# Test API key and connectivity
curl -X POST https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-5-haiku-20241022","max_tokens":100,"messages":[{"role":"user","content":"Say ok"}]}'
# Should return 200 with content in response
```
*File reference:* `src/crypto_news_aggregator/services/briefing_agent.py:779-792` (API request structure)

**Check 2: System prompt is well-formed**
```bash
# Verify system prompt doesn't have syntax errors
python -c "
from crypto_news_aggregator.services.briefing_agent import BriefingAgent
agent = BriefingAgent()
prompt = agent._get_system_prompt('morning')
assert 'crypto market analyst' in prompt
assert 'morning' in prompt
print('✓ System prompt OK')
"
```
*File reference:* `src/crypto_news_aggregator/services/briefing_agent.py:402-425`

**Check 3: Cost tracking is working**
```bash
# Query cost tracking database
db.llm_usage.findOne({operation: "briefing_generation"})
# Should return recent documents with model, input_tokens, output_tokens
```
*File reference:* `src/crypto_news_aggregator/services/briefing_agent.py:809-817` (cost tracking)

**Check 4: Briefing generation completes within timeout**
```bash
# Trigger a briefing and measure time
time curl -X POST "http://localhost:8000/admin/trigger-briefing?force=true"
# Should complete in < 120 seconds (timeout is 120s per LLM call)
```
*File reference:* `src/crypto_news_aggregator/services/briefing_agent.py:791` (timeout)

### Model Selection & Fallback

**Current model hierarchy:**
1. **Primary:** `claude-sonnet-4-5-20250929` (best quality, $5/$15 per 1M tokens)
2. **Fallback 1:** `claude-3-5-haiku-20241022` (good quality, $0.80/$4 per 1M tokens)
3. **Fallback 2:** `claude-3-haiku-20240307` (legacy, $0.80/$4 per 1M tokens)

**When to fallback:**
- 403 Forbidden: Model rate-limited or API key invalid
- Other 4xx: Continue to next model
- Timeout: Retry with same model (line 791)

*File reference:* `src/crypto_news_aggregator/services/briefing_agent.py:46-50` (model list), `824-829` (fallback logic)

## Debugging

**Issue:** LLM API returns "Invalid API key" (403 Forbidden)
- **Root cause:** ANTHROPIC_API_KEY env var not set or expired
- **Verification:** Check `echo $ANTHROPIC_API_KEY` and verify in Anthropic console
- **Fix:** Set/update ANTHROPIC_API_KEY in environment and restart workers
  *Reference:* `src/crypto_news_aggregator/services/briefing_agent.py:94-97` (initialization)

**Issue:** Briefing fails with "All LLM models failed" error
- **Root cause:** All three models returned errors (rate limit, auth, service outage)
- **Verification:** Check worker logs for per-model errors
- **Fix:** Check Anthropic status page; may need to wait for rate limit recovery
  *Reference:* `src/crypto_news_aggregator/services/briefing_agent.py:834`

**Issue:** Generated briefing is empty or has no narrative
- **Root cause:** JSON parsing failed or LLM returned invalid format
- **Verification:** Check worker logs for "Failed to parse LLM response"
- **Fix:** Review generation prompt (may be incomplete); could be malformed JSON
  *Reference:* `src/crypto_news_aggregator/services/briefing_agent.py:730-764` (parsing)

**Issue:** Self-refine loop runs multiple iterations instead of stopping at 1
- **Root cause:** Critique prompt says "needs refinement" even though content is good
- **Verification:** Check logs for "Briefing needs refinement"; review critique response
- **Fix:** Adjust critique prompt to be less strict, or check for LLM consistency issues
  *Reference:* `src/crypto_news_aggregator/services/briefing_agent.py:366-372` (refinement check)

**Issue:** Cost tracking shows high token counts but briefing seems short
- **Root cause:** System prompt and generation prompt are much longer than output
- **Verification:** Log prompt lengths: `len(system_prompt) + len(generation_prompt)`
- **Fix:** This is normal; input tokens include full context. Monitor for outliers
  *Reference:* `src/crypto_news_aggregator/services/briefing_agent.py:805-806` (token counting)

## Relevant Files

### Core Logic
- `src/crypto_news_aggregator/services/briefing_agent.py` - Main generation orchestration
  - Lines 111-165: `generate_briefing()` entry point
  - Lines 315-327: `_generate_with_llm()` - Initial generation
  - Lines 329-400: `_self_refine()` - Quality refinement loop
  - Lines 766-834: `_call_llm()` - API request with fallback
  - Lines 402-425: `_get_system_prompt()` - System prompt template

### Configuration
- `src/crypto_news_aggregator/llm/factory.py:15-50` - Provider initialization
- `src/crypto_news_aggregator/core/config.py:40-47` - Model configuration
- `.env` - ANTHROPIC_API_KEY

### Cost Tracking
- `src/crypto_news_aggregator/services/cost_tracker.py` - Token cost calculation
- `src/crypto_news_aggregator/services/briefing_agent.py:809-817` - Cost logging

### Integration Points
- `src/crypto_news_aggregator/tasks/briefing_tasks.py` - Celery task wrapper calls agent
- `src/crypto_news_aggregator/api/admin.py:415` - HTTP endpoint to trigger generation

### Related Systems
- **Scheduling (20-scheduling.md)** - How briefings are triggered for generation
- **Data Model (50-data-model.md)** - Where generated briefings are stored

---
*Last updated: 2026-02-10* | *Generated from: 04-llm-client.txt, 04-llm-prompts.txt, 05-briefing-generation.txt* | *Anchor: llm-integration-generation*
