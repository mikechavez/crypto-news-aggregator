#!/bin/bash
set -euo pipefail

# Documentation Validation Script
# Validates system docs, context docs, and evidence pack for structural requirements
# Exit codes: 0 = success, non-zero = failures found

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Helper: print section header
print_header() {
    echo ""
    printf "%s\n" "════════════════════════════════════════"
    printf "%s\n" "$1"
    printf "%s\n" "════════════════════════════════════════"
}

# Helper: extract anchor from file
get_file_anchor() {
    local file=$1
    if grep -q "^Anchor:" "$file"; then
        grep "^Anchor:" "$file" | head -1 | sed 's/Anchor: *`#\([^`]*\)`.*/\1/'
    else
        basename "$file" .md | sed 's/^[0-9]*-//'
    fi
}

# Helper: check if anchor exists in system docs
anchor_exists() {
    local anchor=$1
    local system_dir="docs/_generated/system"

    for file in "$system_dir"/*.md; do
        if [[ -f "$file" ]]; then
            # Check for explicit anchor or implicit one
            if grep -q "#$anchor" "$file"; then
                return 0
            fi
        fi
    done
    return 1
}

# Validate system docs
validate_system_docs() {
    print_header "SYSTEM DOCUMENTATION VALIDATION"

    local system_dir="docs/_generated/system"

    if [[ ! -d "$system_dir" ]]; then
        echo "✗ System docs directory not found: $system_dir"
        ((ERRORS++))
        return
    fi

    local file_count=0
    for file in "$system_dir"/*.md; do
        [[ -f "$file" ]] && ((file_count++))
    done

    if [[ $file_count -eq 0 ]]; then
        echo "✗ No system docs found in $system_dir"
        ((ERRORS++))
        return
    fi

    echo "Found $file_count system doc(s)"
    echo ""

    # Validate each system doc
    for file in "$system_dir"/*.md; do
        [[ ! -f "$file" ]] && continue

        local basename=$(basename "$file" .md)
        local doc_errors=0

        printf "%-35s " "$(basename "$file"):"

        # Check required sections (00-overview has different structure, others are standard)
        basename=$(basename "$file" .md)
        local required_sections

        if [[ "$basename" == "00-overview" ]]; then
            # Overview doc needs: Overview + at least System Diagram or Module Interconnections + Relevant Module Documentation
            if ! grep -q "^## Overview" "$file"; then
                if [[ $doc_errors -eq 0 ]]; then
                    echo ""
                fi
                echo "  ✗ Missing section: '## Overview'"
                ((doc_errors++))
                ((ERRORS++))
            fi
            if ! grep -q "^## Relevant Module Documentation" "$file"; then
                if [[ $doc_errors -eq 0 ]]; then
                    echo ""
                fi
                echo "  ✗ Missing section: '## Relevant Module Documentation'"
                ((doc_errors++))
                ((ERRORS++))
            fi
        else
            # Standard system docs need: Overview, Architecture, Implementation, Operational Checks
            required_sections=("## Overview" "## Architecture" "## Implementation Details" "## Operational Checks")
            for section in "${required_sections[@]}"; do
                if ! grep -q "^$section" "$file"; then
                    if [[ $doc_errors -eq 0 ]]; then
                        echo ""
                    fi
                    echo "  ✗ Missing section: '$section'"
                    ((doc_errors++))
                    ((ERRORS++))
                fi
            done
        fi

        # Check line count (before appendix if exists, or total)
        local total_lines=$(wc -l < "$file")
        local core_lines=$(grep -n "^## Appendix" "$file" | cut -d: -f1 | head -1)

        if [[ -z "$core_lines" ]]; then
            core_lines=$total_lines
        else
            core_lines=$((core_lines - 1))
        fi

        if [[ $core_lines -gt 400 ]]; then
            if [[ $doc_errors -eq 0 ]]; then
                echo ""
            fi
            echo "  ✗ Content too long: $core_lines lines (max 400)"
            ((doc_errors++))
            ((ERRORS++))
        elif [[ $core_lines -gt 350 ]]; then
            if [[ $doc_errors -eq 0 ]]; then
                echo ""
            fi
            echo "  ⚠ Content approaching limit: $core_lines/400 lines"
            ((WARNINGS++))
        fi

        if [[ $total_lines -gt 500 ]]; then
            if [[ $doc_errors -eq 0 ]] && [[ $core_lines -le 350 ]]; then
                echo ""
            fi
            echo "  ⚠ Total length: $total_lines lines (some docs reach 500)"
            ((WARNINGS++))
        fi

        # Check for operational checks with runnable commands
        if grep -q "^## Operational Checks" "$file"; then
            if ! sed -n '/^## Operational Checks/,/^## /p' "$file" | grep -q '```'; then
                if [[ $doc_errors -eq 0 ]]; then
                    echo ""
                fi
                echo "  ⚠ Operational Checks section has no code blocks"
                ((WARNINGS++))
            fi
        fi

        if [[ $doc_errors -eq 0 ]]; then
            echo "✓ Pass ($core_lines/$total_lines lines)"
        else
            echo "✗ $doc_errors validation error(s)"
        fi
    done

    echo ""
}

# Validate context docs
validate_context_docs() {
    print_header "CONTEXT DOCUMENTATION VALIDATION"

    local context_dir="docs/_generated/context"

    if [[ ! -d "$context_dir" ]]; then
        echo "⚠ Context docs directory not found (optional): $context_dir"
        echo ""
        return
    fi

    local file_count=0
    for file in "$context_dir"/*.md; do
        [[ -f "$file" ]] && ((file_count++))
    done

    if [[ $file_count -eq 0 ]]; then
        echo "No context docs found (optional)"
        echo ""
        return
    fi

    echo "Found $file_count context doc(s)"
    echo ""

    # Validate each context doc
    for file in "$context_dir"/*.md; do
        [[ ! -f "$file" ]] && continue

        printf "%-35s " "$(basename "$file"):"
        local doc_errors=0

        # Count entries (lines starting with "- doc:")
        local entry_count
        entry_count=$(grep -c "^- doc:" "$file" 2>/dev/null || echo "0")
        entry_count=$(echo "$entry_count" | tr -d ' \n')

        if [[ "$entry_count" -eq 0 ]]; then
            echo "⚠ No entries found"
            ((WARNINGS++))
            continue
        fi

        # Check entry limit (warn at 8+, fail at 11+)
        if [[ "$entry_count" -gt 10 ]]; then
            echo ""
            echo "  ✗ Too many entries: $entry_count (max 10)"
            ((doc_errors++))
            ((ERRORS++))
        elif [[ "$entry_count" -gt 8 ]]; then
            echo ""
            echo "  ⚠ Many entries: $entry_count/10"
            ((WARNINGS++))
        fi

        # Critical: Check Context Extraction Rule - every entry must have relates_to with valid anchor
        local rule_violations=0
        local invalid_anchors=0

        while IFS= read -r line_num; do
            # Check if relates_to field exists within next 4 lines
            local has_relates_to=$(sed -n "$((line_num)),$((line_num+4))p" "$file" | grep -c "relates_to:" || echo 0)

            if [[ $has_relates_to -eq 0 ]]; then
                if [[ $rule_violations -eq 0 ]] && [[ $doc_errors -eq 0 ]]; then
                    echo ""
                fi
                echo "  ✗ Entry at line $line_num: missing 'relates_to' field (CRITICAL)"
                ((rule_violations++))
                ((doc_errors++))
                ((ERRORS++))
            else
                # Extract anchor from relates_to field
                local anchor_ref=$(sed -n "$((line_num)),$((line_num+4))p" "$file" | grep "relates_to:" | sed -E 's/.*#([a-z0-9-]+).*/\1/' | head -1)

                if [[ -n "$anchor_ref" ]]; then
                    if ! anchor_exists "$anchor_ref"; then
                        if [[ $invalid_anchors -eq 0 ]] && [[ $rule_violations -eq 0 ]] && [[ $doc_errors -eq 0 ]]; then
                            echo ""
                        fi
                        echo "  ✗ Entry at line $line_num: anchor '#$anchor_ref' not found in system docs"
                        ((invalid_anchors++))
                        ((doc_errors++))
                        ((ERRORS++))
                    fi
                fi
            fi
        done < <(grep -n "^- doc:" "$file" | cut -d: -f1)

        # Check entry field format (adds, confidence)
        local missing_fields=0
        while IFS= read -r line_num; do
            local entry_block=$(sed -n "$((line_num)),$((line_num+4))p" "$file")

            if ! echo "$entry_block" | grep -q "  adds:"; then
                ((missing_fields++))
            fi
            if ! echo "$entry_block" | grep -q "  confidence:"; then
                ((missing_fields++))
            fi
        done < <(grep -n "^- doc:" "$file" | cut -d: -f1)

        if [[ $missing_fields -gt 0 ]]; then
            if [[ $doc_errors -gt 0 ]]; then
                echo "  ✗ $missing_fields entries missing required fields"
            else
                echo ""
                echo "  ✗ $missing_fields entries missing required fields"
            fi
            ((doc_errors+=$missing_fields))
            ((ERRORS+=$missing_fields))
        fi

        # Check confidence values (must be: high, med, low)
        local invalid_confidence=0
        while IFS= read -r conf_value; do
            if ! echo "$conf_value" | grep -qE "^(high|med|low)$"; then
                ((invalid_confidence++))
            fi
        done < <(grep "confidence:" "$file" | sed -E 's/.*confidence: *([a-z]+).*/\1/')

        if [[ $invalid_confidence -gt 0 ]]; then
            if [[ $doc_errors -gt 0 ]]; then
                echo "  ✗ $invalid_confidence invalid confidence values (must be: high, med, low)"
            else
                echo ""
                echo "  ✗ $invalid_confidence invalid confidence values (must be: high, med, low)"
            fi
            ((doc_errors+=$invalid_confidence))
            ((ERRORS+=$invalid_confidence))
        fi

        if [[ $doc_errors -eq 0 ]]; then
            echo "✓ Pass ($entry_count entries)"
        else
            echo "✗ $doc_errors validation error(s)"
        fi
    done

    echo ""
}

# Validate evidence pack
validate_evidence_pack() {
    print_header "EVIDENCE PACK VALIDATION"

    local evidence_dir="docs/_generated/evidence"

    if [[ ! -d "$evidence_dir" ]]; then
        echo "⚠ Evidence directory not found (optional): $evidence_dir"
        echo ""
        return
    fi

    local file_count=0
    for file in "$evidence_dir"/*.txt; do
        [[ -f "$file" ]] && ((file_count++))
    done

    if [[ $file_count -eq 0 ]]; then
        echo "No evidence files found (optional)"
        echo ""
        return
    fi

    echo "Found $file_count evidence file(s)"
    echo ""

    for file in "$evidence_dir"/*.txt; do
        [[ ! -f "$file" ]] && continue

        printf "%-35s " "$(basename "$file"):"

        # Check if file is empty
        if [[ ! -s "$file" ]]; then
            echo "✗ Empty file"
            ((ERRORS++))
            continue
        fi

        # Check line count
        local line_count=$(wc -l < "$file")

        if [[ $line_count -gt 500 ]]; then
            echo "⚠ Large file ($line_count lines)"
            ((WARNINGS++))
        else
            echo "✓ OK ($line_count lines)"
        fi
    done

    echo ""
}

# Main validation flow
main() {
    echo ""
    print_header "DOCUMENTATION VALIDATION"

    validate_system_docs
    validate_context_docs
    validate_evidence_pack

    # Print summary
    print_header "SUMMARY"

    if [[ $ERRORS -eq 0 ]]; then
        echo "✓ Validation PASSED"
        if [[ $WARNINGS -gt 0 ]]; then
            echo "⚠ $WARNINGS warning(s)"
        fi
        echo ""
        return 0
    else
        echo "✗ Validation FAILED"
        echo "  $ERRORS error(s)"
        if [[ $WARNINGS -gt 0 ]]; then
            echo "  $WARNINGS warning(s)"
        fi
        echo ""
        return 1
    fi
}

main "$@"
