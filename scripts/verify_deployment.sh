#!/bin/bash

# Deployment Verification Script
# Checks that all background workers are functioning correctly

set -e

# Get Railway domain
BASE_URL="https://context-owl-production.up.railway.app"

echo "🔍 Verifying Context Owl Deployment"
echo "===================================="
echo ""

# 1. Health Check
echo "1️⃣  Health Check..."
HEALTH=$(curl -s "$BASE_URL/" | jq -r '.status')
if [ "$HEALTH" = "ok" ]; then
    echo "   ✅ Service is healthy"
else
    echo "   ❌ Service health check failed"
    exit 1
fi
echo ""

# 2. Signal Scores
echo "2️⃣  Signal Scores (should have fresh timestamps & non-zero velocity)..."
SIGNALS=$(curl -s "$BASE_URL/api/v1/signals/trending?limit=3")
SIGNAL_COUNT=$(echo "$SIGNALS" | jq '.count')
echo "   Found $SIGNAL_COUNT signals"

if [ "$SIGNAL_COUNT" -gt 0 ]; then
    echo "$SIGNALS" | jq -r '.signals[] | "   - \(.entity) (\(.entity_type)): score=\(.signal_score), velocity=\(.velocity)"' | head -3
    
    # Check for non-zero velocity
    ZERO_VELOCITY=$(echo "$SIGNALS" | jq '[.signals[] | select(.velocity == 0)] | length')
    if [ "$ZERO_VELOCITY" -eq 0 ]; then
        echo "   ✅ All signals have non-zero velocity"
    else
        echo "   ⚠️  Warning: Some signals have zero velocity"
    fi
else
    echo "   ⚠️  No signals found (may need time to populate)"
fi
echo ""

# 3. Narratives
echo "3️⃣  Narratives (should appear if co-occurring entities found)..."
NARRATIVES=$(curl -s "$BASE_URL/api/v1/narratives/active?limit=3")
NARRATIVE_COUNT=$(echo "$NARRATIVES" | jq '. | length')
echo "   Found $NARRATIVE_COUNT narratives"

if [ "$NARRATIVE_COUNT" -gt 0 ]; then
    echo "$NARRATIVES" | jq -r '.[] | "   - \(.theme) (\(.article_count) articles)"' | head -3
    echo "   ✅ Narratives are being detected"
else
    echo "   ⚠️  No narratives found (may need more co-occurring entities)"
fi
echo ""

# 4. Entity Alerts
echo "4️⃣  Entity Alerts (should trigger on velocity spikes)..."
ALERTS=$(curl -s "$BASE_URL/api/v1/entity-alerts/recent" | jq '. | length')
echo "   Found $ALERTS alerts"

if [ "$ALERTS" -gt 0 ]; then
    curl -s "$BASE_URL/api/v1/entity-alerts/recent" | jq -r '.[:3] | .[] | "   - \(.entity) (\(.type)): \(.details.message)"'
    echo "   ✅ Alerts are being triggered"
else
    echo "   ⚠️  No alerts found (may need higher entity activity)"
fi
echo ""

# 5. Recent Articles
echo "5️⃣  Recent Articles (RSS feed should be active)..."
ARTICLES=$(curl -s "$BASE_URL/api/v1/articles/recent?limit=1" 2>/dev/null || echo '{"error": true}')

if echo "$ARTICLES" | jq -e '.count' >/dev/null 2>&1; then
    ARTICLE_COUNT=$(echo "$ARTICLES" | jq '.count')
    echo "   Found $ARTICLE_COUNT recent articles"
    
    if [ "$ARTICLE_COUNT" -gt 0 ]; then
        LATEST=$(echo "$ARTICLES" | jq -r '.articles[0] | "   Latest: \(.title) (published: \(.published_at))"')
        echo "$LATEST"
        echo "   ✅ RSS feed is active"
    else
        echo "   ⚠️  No articles found (RSS feed may need time)"
    fi
else
    echo "   ⚠️  Articles endpoint error (check logs)"
    ARTICLE_COUNT=0
fi
echo ""

echo "===================================="
echo "✨ Verification Complete!"
echo ""
echo "📊 Summary:"
echo "   - Signals: $SIGNAL_COUNT"
echo "   - Narratives: $NARRATIVE_COUNT"
echo "   - Alerts: $ALERTS"
echo "   - Articles: $ARTICLE_COUNT"
echo ""
echo "🔗 Dashboard: $BASE_URL/docs"
