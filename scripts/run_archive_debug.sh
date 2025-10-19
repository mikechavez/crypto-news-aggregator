#!/bin/bash
# Run all archive tab debugging scripts

set -e

echo "=========================================="
echo "ARCHIVE TAB DEBUG SUITE"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "Error: Must run from project root directory"
    exit 1
fi

echo "Step 1: Checking MongoDB for dormant narratives..."
echo "=========================================="
poetry run python scripts/check_dormant_narratives.py
echo ""
echo ""

echo "Step 2: Testing API endpoint..."
echo "=========================================="
poetry run python scripts/test_archive_api.py
echo ""
echo ""

echo "=========================================="
echo "DEBUG COMPLETE"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Check the output above for any issues"
echo "2. Open the frontend and check browser console logs"
echo "3. Look for [DEBUG] messages in the console"
echo "4. See scripts/debug_archive_tab.md for detailed analysis"
echo ""
