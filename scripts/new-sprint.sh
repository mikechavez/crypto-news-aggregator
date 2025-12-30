#!/bin/bash

# Interactive Sprint Transition Script
# Usage: ./scripts/new-sprint.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Paths
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CURRENT_SPRINT_FILE="$REPO_ROOT/docs/current-sprint.md"
EXTERNAL_SPRINTS_DIR="/Users/mc/Documents/claude-vault/projects/app-backdrop/development/sprints"
EXTERNAL_SPRINTS_MD="/Users/mc/Documents/claude-vault/projects/app-backdrop/development/SPRINTS.md"

# Check if current-sprint.md exists
if [ ! -f "$CURRENT_SPRINT_FILE" ]; then
    echo -e "${RED}Error: $CURRENT_SPRINT_FILE not found${NC}"
    exit 1
fi

# Extract current sprint number from file
CURRENT_SPRINT=$(grep "^# Current Sprint:" "$CURRENT_SPRINT_FILE" | sed -E 's/.*Sprint ([0-9]+).*/\1/')

if [ -z "$CURRENT_SPRINT" ]; then
    echo -e "${RED}Error: Could not determine current sprint number${NC}"
    exit 1
fi

NEXT_SPRINT=$((CURRENT_SPRINT + 1))

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Sprint Transition Tool                           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Show current sprint summary
echo -e "${YELLOW}Current Sprint Summary (Sprint $CURRENT_SPRINT):${NC}"
echo ""
cat "$CURRENT_SPRINT_FILE" | grep -A 20 "## Completed This Sprint" | head -20
echo ""

# Count completed tickets
COMPLETED_COUNT=$(grep -c "^- ✅" "$CURRENT_SPRINT_FILE" || echo "0")
echo -e "${GREEN}Completed tickets: $COMPLETED_COUNT${NC}"
echo ""

# Show what will happen
echo -e "${YELLOW}What this script will do:${NC}"
echo "  1. Archive Sprint $CURRENT_SPRINT to external sprints folder"
echo "  2. Open archived file for you to add retrospective notes"
echo "  3. Create fresh Sprint $NEXT_SPRINT in docs/current-sprint.md"
echo "  4. Commit the change to git"
echo ""

# Confirmation prompt
read -p "$(echo -e ${YELLOW}Ready to transition from Sprint $CURRENT_SPRINT to Sprint $NEXT_SPRINT? [y/N]: ${NC})" -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Sprint transition cancelled.${NC}"
    exit 0
fi

echo ""
echo -e "${GREEN}Starting sprint transition...${NC}"
echo ""

# Step 1: Create archive directory if it doesn't exist
mkdir -p "$EXTERNAL_SPRINTS_DIR"

# Step 2: Archive current sprint
ARCHIVE_FILE="$EXTERNAL_SPRINTS_DIR/sprint-$(printf "%03d" $CURRENT_SPRINT)-retro.md"

echo -e "${BLUE}[1/4]${NC} Archiving Sprint $CURRENT_SPRINT to:"
echo "      $ARCHIVE_FILE"

# Copy current sprint and add retrospective template
cat > "$ARCHIVE_FILE" << 'HEADER'
# Sprint Retrospective

---

## Sprint Plan (Original)

HEADER

cat "$CURRENT_SPRINT_FILE" >> "$ARCHIVE_FILE"

cat >> "$ARCHIVE_FILE" << 'FOOTER'

---

## Retrospective

### What Went Well
-

### What Could Improve
-

### Lessons Learned
-

### Action Items for Next Sprint
-

### Metrics
- Planned tickets:
- Completed tickets:
- Velocity:
- Sprint duration:
- Average complexity:

FOOTER

echo -e "${GREEN}✓ Sprint $CURRENT_SPRINT archived${NC}"
echo ""

# Step 3: Prompt user to fill in retrospective
echo -e "${BLUE}[2/4]${NC} Opening archived sprint for retrospective notes..."
echo ""
read -p "$(echo -e ${YELLOW}Press ENTER to open the file in your editor...${NC})"

# Open in default editor (use EDITOR env var, fallback to code/vim)
if [ -n "$EDITOR" ]; then
    $EDITOR "$ARCHIVE_FILE"
elif command -v code &> /dev/null; then
    code "$ARCHIVE_FILE"
elif command -v vim &> /dev/null; then
    vim "$ARCHIVE_FILE"
else
    echo -e "${YELLOW}Could not detect editor. Please edit manually:${NC}"
    echo "$ARCHIVE_FILE"
fi

echo ""
read -p "$(echo -e ${YELLOW}Have you finished adding retrospective notes? [y/N]: ${NC})" -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}You can edit the retrospective later at:${NC}"
    echo "$ARCHIVE_FILE"
    echo ""
fi

# Step 4: Create new sprint
echo -e "${BLUE}[3/4]${NC} Creating Sprint $NEXT_SPRINT..."

# Prompt for sprint name
read -p "$(echo -e ${YELLOW}Enter Sprint $NEXT_SPRINT name (e.g., 'Design Phase'): ${NC})" SPRINT_NAME

if [ -z "$SPRINT_NAME" ]; then
    SPRINT_NAME="Sprint $NEXT_SPRINT"
fi

# Get start and end dates
START_DATE=$(date +%Y-%m-%d)
read -p "$(echo -e ${YELLOW}Sprint end date (YYYY-MM-DD) [leave empty for +7 days]: ${NC})" END_DATE

if [ -z "$END_DATE" ]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        END_DATE=$(date -v+7d +%Y-%m-%d)
    else
        # Linux
        END_DATE=$(date -d "+7 days" +%Y-%m-%d)
    fi
fi

# Create new sprint file
cat > "$CURRENT_SPRINT_FILE" << EOF
# Current Sprint: Sprint $NEXT_SPRINT ($SPRINT_NAME)

**Goal:** [Fill in sprint goal]

**Sprint Duration:** $START_DATE to $END_DATE

**Velocity Target:** $COMPLETED_COUNT tickets (based on Sprint $CURRENT_SPRINT)

---

## Backlog

- [ ] [TICKET-ID] Ticket description
  - Location: \`/Users/mc/Documents/claude-vault/projects/app-backdrop/development/backlog/ticket-file.md\`
  - Priority:
  - Complexity:

---

## In Progress

None yet - ready to start!

---

## Completed This Sprint

None yet

---

## Blocked

None currently

---

## Notes

- Sprint just started
- Add notes here as work progresses

---

## External References

- **Full sprint plan:** \`/Users/mc/Documents/claude-vault/projects/app-backdrop/development/SPRINTS.md\`
- **All tickets:** \`/Users/mc/Documents/claude-vault/projects/app-backdrop/development/\`
- **Previous sprint:** \`$ARCHIVE_FILE\`
- **Product vision:** \`/Users/mc/Documents/claude-vault/projects/app-backdrop/planning/vision.md\`
- **Roadmap:** \`/Users/mc/Documents/claude-vault/projects/app-backdrop/planning/roadmap.md\`
EOF

echo -e "${GREEN}✓ Sprint $NEXT_SPRINT created${NC}"
echo ""

# Step 5: Commit changes
echo -e "${BLUE}[4/4]${NC} Committing sprint transition to git..."

cd "$REPO_ROOT"
git add docs/current-sprint.md

# Check if there are changes to commit
if git diff --cached --quiet; then
    echo -e "${YELLOW}No changes to commit${NC}"
else
    git commit -m "chore(docs): start Sprint $NEXT_SPRINT ($SPRINT_NAME)"
    echo -e "${GREEN}✓ Changes committed${NC}"
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Sprint Transition Complete! 🎉                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Review Sprint $NEXT_SPRINT in: docs/current-sprint.md"
echo "  2. Add sprint goal and tickets"
echo "  3. Update external SPRINTS.md with Sprint $NEXT_SPRINT details"
echo "  4. Review Sprint $CURRENT_SPRINT retrospective in:"
echo "     $ARCHIVE_FILE"
echo ""
echo -e "${BLUE}Ready to start Sprint $NEXT_SPRINT! 🚀${NC}"
