# Context Owl UI - Design & Technical Overview

**Audience:** Designers and Front-End Engineers  
**Purpose:** Comprehensive description of the current UI implementation to enable informed improvements and enhancements

---

## Table of Contents
1. [Overview](#overview)
2. [Tech Stack](#tech-stack)
3. [Architecture](#architecture)
4. [Current Pages](#current-pages)
5. [Component Library](#component-library)
6. [Design System](#design-system)
7. [Data Flow & State Management](#data-flow--state-management)
8. [Known Limitations & Opportunities](#known-limitations--opportunities)

---

## Overview

**Context Owl** is a crypto news aggregation platform that surfaces market signals, emerging narratives, and entity-level insights from real-time news sources. The UI is designed to help users quickly identify unusual market activity and understand trending topics in the crypto space.

### Core Value Propositions
- **Real-time signal detection** - Identify entities experiencing unusual mention velocity
- **Narrative clustering** - Group related stories into coherent themes
- **Entity deep-dive** - Explore detailed views of specific cryptocurrencies, protocols, and companies
- **Article feed** - Chronological view of all ingested content

---

## Tech Stack

### Framework & Build Tools
- **React 18** - UI framework with hooks-based architecture
- **TypeScript** - Type safety throughout the codebase
- **Vite** - Fast build tool and dev server
- **React Router v7** - Client-side routing

### State & Data Management
- **React Query (TanStack Query v5)** - Server state management, caching, and auto-refetching
  - 30-second stale time for signals
  - 60-second refetch interval for narratives and articles
  - Automatic retry logic (1 retry)

### Styling
- **Tailwind CSS v4** - Utility-first CSS framework
- **PostCSS** - CSS processing
- No component library (custom components built from scratch)

### API Integration
- RESTful API client with API key authentication
- Base URL configured via environment variables (`VITE_API_URL`, `VITE_API_KEY`)

---

## Architecture

### Project Structure
```
src/
├── api/              # API client and endpoint functions
│   ├── client.ts     # Base axios-like client with auth
│   ├── signals.ts    # Signals API endpoints
│   ├── narratives.ts # Narratives API endpoints
│   ├── entities.ts   # Entities API endpoints
│   └── articles.ts   # Articles API endpoints
├── components/       # Reusable UI components
│   ├── Card.tsx      # Card container components
│   ├── Layout.tsx    # App shell with navigation
│   ├── Loading.tsx   # Loading spinner
│   └── ErrorMessage.tsx # Error state component
├── pages/            # Page-level components (routes)
│   ├── Signals.tsx   # Market signals dashboard
│   ├── Narratives.tsx # Narrative clusters view
│   ├── Articles.tsx  # Article feed table
│   └── EntityDetail.tsx # Entity deep-dive (disabled)
├── types/            # TypeScript type definitions
│   └── index.ts      # Shared types
├── lib/              # Utility functions
│   ├── formatters.ts # Date, number, sentiment formatters
│   └── cn.ts         # Class name utility (clsx-like)
├── App.tsx           # Root component with routing
└── main.tsx          # Entry point
```

### Routing
- `/` → Redirects to `/signals`
- `/signals` → Market Signals page
- `/narratives` → Emerging Narratives page
- `/articles` → Recent Articles feed
- `/entity/:id` → **Disabled** (backend endpoints not yet implemented)

---

## Current Pages

### 1. Market Signals (`/signals`)

**Purpose:** Display entities experiencing unusual mention velocity with contextual metadata.

#### Layout
- **Header:** Page title, description, last updated timestamp
- **Tab Navigation:** Three timeframes with emoji indicators
  - 🔥 Hot (24h) - "Breaking news and sudden spikes"
  - 📈 Trending (7d) - "Gaining momentum this week" (default)
  - ⭐ Top (30d) - "Major ongoing narratives"
- **Grid:** 3-column responsive grid (collapses to 2 on tablet, 1 on mobile)

#### Signal Card Anatomy
Each card displays:
- **Rank badge** - Blue numbered badge (#1, #2, etc.)
- **Entity name** - Parsed to separate ticker symbols (e.g., "Bitcoin $BTC")
- **Velocity indicator** - Emoji + label badge with color coding:
  - 🔥 Surging (≥500% growth) - Red
  - ↑ Rising (≥200% growth) - Green
  - → Growing (≥50% growth) - Blue
  - Active (0-50% growth) - Gray
  - ↓ Declining (<0% growth) - Orange
- **Metadata rows:**
  - Entity type (badge with color coding)
  - Source count
  - Sentiment (Positive/Neutral/Negative with color)
  - Last updated (relative time)
- **Narrative context section:**
  - "Emerging" badge if not part of any narrative
  - Clickable theme badges if part of narratives
- **Recent articles (expandable):**
  - Collapsible section showing recent mentions
  - Article title (clickable link), source, and publish time

#### Interaction Patterns
- Tab switching fetches new data via React Query
- Expandable article sections (click to toggle)
- Narrative badges navigate to `/narratives` page
- Auto-refresh every 30 seconds

#### Current Limitations
- Entity names not clickable (entity detail page disabled)
- No filtering or search functionality
- No sorting controls (server-side sorted only)
- Velocity thresholds are hardcoded (not configurable)

---

### 2. Emerging Narratives (`/narratives`)

**Purpose:** Display clustered stories grouped by theme with associated entities and articles.

#### Layout
- **Header:** Page title, description, last updated timestamp
- **Vertical stack:** Full-width cards in a single column

#### Narrative Card Anatomy
Each card displays:
- **Title** - Narrative theme/title (e.g., "Bitcoin ETF Approval")
- **Article count badge** - Blue pill showing number of articles
- **Summary** - AI-generated narrative summary (if available)
- **Entity badges** - Horizontal scrollable list of related entities (blue pills)
- **Expandable articles section:**
  - Button: "📰 View X articles"
  - Expanded view shows article cards with:
    - Title (clickable external link)
    - Source and publish time
- **Footer:** Last updated timestamp

#### Interaction Patterns
- Expandable article sections (click to toggle)
- External links open in new tabs
- Auto-refresh every 60 seconds

#### Current Limitations
- No theme filtering or categorization
- Entity badges not clickable
- No timeline or temporal visualization
- No narrative strength/confidence indicators
- Summary quality varies (AI-generated)

---

### 3. Recent Articles (`/articles`)

**Purpose:** Chronological feed of all ingested articles with entity extraction.

#### Layout
- **Header:** Page title with article count
- **Table:** Full-width responsive table with horizontal scroll

#### Table Columns
1. **Time** - Relative time (e.g., "2 hours ago")
2. **Title** - Clickable link with external icon on hover
3. **Source** - Colored badge (different colors per source)
4. **Entities** - Pills showing first 3 entities + "+X more" indicator

#### Source Color Coding
- Twitter - Blue
- Telegram - Cyan
- RSS - Orange
- CoinDesk - Purple
- Cointelegraph - Pink
- Decrypt - Green
- Bitcoin Magazine - Yellow
- Default - Gray

#### Interaction Patterns
- Row hover state (light gray background)
- External links open in new tabs
- Auto-refresh every 60 seconds
- Limit: 100 most recent articles

#### Current Limitations
- No pagination or infinite scroll
- No filtering by source or entity
- No search functionality
- Entity pills not clickable
- Table not sortable
- Mobile experience suboptimal (horizontal scroll required)

---

### 4. Entity Detail (`/entity/:id`) - **DISABLED**

**Purpose:** Deep-dive view of a specific entity with signals, mentions, and articles.

**Status:** Commented out in routing. Backend endpoints not yet implemented.

#### Planned Layout (from code)
- Back navigation to signals page
- Entity name and type header
- Two-column grid:
  - **Recent Signals card** - Signal history with scores
  - **Article Mentions card** - Mention counts and sentiment
- **Recent Articles section** - Full-width card with article list

---

## Component Library

### Core Components

#### `<Card>`, `<CardHeader>`, `<CardTitle>`, `<CardContent>`
**Purpose:** Consistent card container pattern used throughout the app.

**Styling:**
- White background
- Rounded corners (`rounded-lg`)
- Drop shadow (`shadow-md`)
- 24px padding (`p-6`)

**Usage:** All major content blocks use this pattern.

---

#### `<Layout>`
**Purpose:** App shell with navigation and content area.

**Features:**
- Fixed top navigation bar
- Logo: "Context Owl" in blue
- Horizontal nav links (Signals, Narratives, Articles)
- Active state: Blue underline border
- Max-width content area (7xl = 1280px)
- Responsive padding

**Styling:**
- Nav: White background, subtle shadow, gray border
- Content: Gray background (`bg-gray-50`)

---

#### `<Loading>`
**Purpose:** Loading state indicator.

**Implementation:** Simple spinner component (details not shown in files reviewed).

---

#### `<ErrorMessage>`
**Purpose:** Error state with retry functionality.

**Features:**
- Error message display
- Optional retry button
- Consistent error UI pattern

---

### Utility Functions (`lib/formatters.ts`)

#### Date & Time
- `formatDate(dateString)` - "Jan 15, 2024, 10:30 AM"
- `formatRelativeTime(dateString)` - "2 hours ago", "3 days ago"

#### Numbers
- `formatNumber(num)` - "1,234,567"
- `formatPercentage(num, decimals)` - "45.2%"

#### Sentiment
- `formatSentiment(score)` - "Positive" | "Neutral" | "Negative"
- `getSentimentColor(score)` - Returns Tailwind color class
  - Positive (>0.3): `text-green-600`
  - Negative (<-0.3): `text-red-600`
  - Neutral: `text-gray-500`

#### Entity Types
- `formatEntityType(type)` - Maps technical types to friendly labels
- `getEntityTypeColor(type)` - Returns background + text color classes
  - Cryptocurrency: Blue
  - Blockchain: Purple
  - Protocol: Indigo
  - Company: Green
  - Organization: Orange
  - Event: Red
  - Person: Pink
  - Concept/Location/Ticker/Project: Various

#### Narrative Themes
- `formatTheme(theme)` - Maps theme keys to labels
- `getThemeColor(theme)` - Returns badge color classes with hover states
  - Regulatory: Red
  - DeFi Adoption: Purple
  - Institutional Investment: Green
  - Technology Upgrade: Blue
  - Market Volatility: Orange
  - Security Breach: Red
  - Partnership: Indigo
  - Ecosystem Growth: Teal

---

## Design System

### Color Palette

#### Brand Colors
- **Primary:** Blue (`text-blue-600`, `bg-blue-600`)
- **Background:** Gray-50 (`bg-gray-50`)
- **Surface:** White (`bg-white`)

#### Semantic Colors
- **Success/Positive:** Green-600
- **Warning:** Yellow/Orange-600
- **Danger/Negative:** Red-600
- **Neutral:** Gray-500

#### Entity Type Colors
Consistent color coding across entity types using Tailwind's color scale (50 for backgrounds, 600 for text).

### Typography

#### Headings
- **H1:** `text-3xl font-bold text-gray-900` (30px)
- **H3 (Card titles):** `text-xl font-semibold text-gray-900` (20px)
- **Body:** `text-gray-700` (default 16px)
- **Small text:** `text-sm` (14px), `text-xs` (12px)

#### Font Stack
Default system fonts (not explicitly defined, using browser defaults).

### Spacing
- **Card padding:** 24px (`p-6`)
- **Content max-width:** 1280px (`max-w-7xl`)
- **Grid gaps:** 24px (`gap-6`)
- **Component spacing:** Consistent use of Tailwind spacing scale

### Borders & Shadows
- **Card shadow:** `shadow-md` (medium drop shadow)
- **Border radius:** `rounded-lg` (8px) for cards, `rounded-full` for badges
- **Dividers:** `border-gray-200` (light gray)

### Badges & Pills
- **Pattern:** Small text, rounded-full, padding `px-2 py-1` or `px-2.5 py-0.5`
- **Colors:** Semantic (100 background, 700 text for contrast)
- **Font:** `text-xs font-medium`

---

## Data Flow & State Management

### React Query Configuration
```javascript
{
  refetchOnWindowFocus: false,  // Don't refetch when tab regains focus
  retry: 1,                      // Retry failed requests once
  staleTime: 30000,              // Consider data stale after 30s
}
```

### Query Keys
- `['signals', timeframe]` - Signals page (varies by timeframe)
- `['narratives']` - Narratives page
- `['articles', 'recent']` - Articles page
- `['entity', entityId]` - Entity detail (disabled)

### Refetch Intervals
- **Signals:** 30 seconds
- **Narratives:** 60 seconds
- **Articles:** 60 seconds

### API Client
- Base client with API key header injection
- Error handling at component level
- No global error boundary (opportunity for improvement)

---

## Known Limitations & Opportunities

### UX/UI Improvements

#### Navigation & Wayfinding
- ❌ No breadcrumbs or back navigation (except entity detail)
- ❌ No search functionality across any page
- ❌ No bookmarking or favorites system
- ❌ No user preferences or settings

#### Data Visualization
- ❌ No charts or graphs (all data is text/badges)
- ❌ No timeline visualizations for narratives
- ❌ No trend indicators beyond velocity badges
- ❌ No comparative views (e.g., compare entities)

#### Filtering & Sorting
- ❌ No client-side filtering on any page
- ❌ No sorting controls (relies on server-side sorting)
- ❌ No saved filters or views
- ❌ No entity type filtering on signals page

#### Interaction Patterns
- ❌ No keyboard shortcuts
- ❌ No bulk actions
- ❌ No share functionality
- ❌ Limited expandable sections (only articles)
- ❌ No tooltips or contextual help

#### Mobile Experience
- ⚠️ Articles table requires horizontal scroll on mobile
- ⚠️ Grid collapses but could be optimized further
- ⚠️ No mobile-specific navigation (hamburger menu)
- ⚠️ Badge text may wrap awkwardly on small screens

### Technical Improvements

#### Performance
- ❌ No virtualization for long lists
- ❌ No lazy loading of images (none currently used)
- ❌ No code splitting beyond route-level
- ❌ No service worker or offline support

#### Accessibility
- ❌ No ARIA labels on interactive elements
- ❌ No keyboard navigation support
- ❌ No focus management
- ❌ No screen reader testing
- ❌ Color contrast not verified (likely passes but not tested)

#### State Management
- ❌ No persistent state (filters, preferences)
- ❌ No URL state synchronization (e.g., selected timeframe)
- ❌ No optimistic updates
- ❌ No error recovery beyond retry button

#### Design System
- ❌ No design tokens or CSS variables
- ❌ Inconsistent spacing in some areas
- ❌ No dark mode support
- ❌ No animation or transition system
- ❌ No icon library (using emoji for icons)

### Content & Data

#### Missing Features
- ❌ No entity detail page (backend not ready)
- ❌ No user authentication or personalization
- ❌ No alerts or notifications
- ❌ No export functionality (CSV, PDF)
- ❌ No article summaries on signals page
- ❌ No sentiment trend over time

#### Data Quality
- ⚠️ Velocity thresholds are hardcoded (not data-driven)
- ⚠️ Narrative summaries vary in quality
- ⚠️ Entity name parsing is regex-based (fragile)
- ⚠️ Date parsing has extensive fallback logic (suggests data inconsistency)

---

## Recommendations for Improvement

### High-Impact Quick Wins
1. **Add search functionality** - Global search across entities and narratives
2. **Implement URL state** - Persist selected timeframe in URL
3. **Mobile navigation** - Hamburger menu for small screens
4. **Loading skeletons** - Replace spinner with content-shaped skeletons
5. **Empty states** - Better messaging when no data is available

### Medium-Term Enhancements
1. **Data visualization** - Add charts for velocity trends, sentiment over time
2. **Filtering system** - Client-side filters for entity type, source, sentiment
3. **Keyboard shortcuts** - Power user features (e.g., `?` for help, `/` for search)
4. **Dark mode** - Toggle between light/dark themes
5. **Icon system** - Replace emoji with proper icon library (Lucide, Heroicons)

### Long-Term Strategic Improvements
1. **Entity detail page** - Complete implementation when backend is ready
2. **Personalization** - User accounts, saved searches, custom alerts
3. **Real-time updates** - WebSocket integration for live data
4. **Advanced analytics** - Correlation analysis, predictive signals
5. **Accessibility audit** - Full WCAG 2.1 AA compliance
6. **Design system documentation** - Storybook or similar for component library

---

## Technical Debt & Code Quality

### Positive Aspects
- ✅ TypeScript throughout (type safety)
- ✅ Consistent component patterns
- ✅ Clean separation of concerns (API, components, pages)
- ✅ React Query for server state (good practice)
- ✅ Utility-first CSS (Tailwind)

### Areas for Improvement
- ⚠️ Extensive date parsing fallback logic (suggests API inconsistency)
- ⚠️ Regex-based entity name parsing (fragile)
- ⚠️ Hardcoded color maps in formatters (should be in design tokens)
- ⚠️ No error boundaries (app could crash on unexpected errors)
- ⚠️ No logging or analytics integration
- ⚠️ No E2E tests (only manual testing)

---

## Conclusion

The Context Owl UI is a **functional MVP** with a clean, consistent design and solid technical foundation. It successfully delivers core value propositions (signals, narratives, articles) with real-time data updates.

**Strengths:**
- Fast, responsive React + Vite setup
- Clean component architecture
- Consistent design patterns
- Real-time data with React Query

**Primary Gaps:**
- Limited interactivity (no search, filtering, sorting)
- No data visualization (charts, graphs)
- Mobile experience needs work
- Accessibility not addressed
- No personalization or user accounts

**Next Steps for Designers:**
- Design search and filtering UI patterns
- Create data visualization concepts (charts, timelines)
- Improve mobile navigation and layouts
- Establish formal design system with tokens
- Design entity detail page (when backend ready)

**Next Steps for Engineers:**
- Implement URL state management
- Add search functionality
- Build filtering system
- Improve mobile responsiveness
- Add accessibility features (ARIA, keyboard nav)
- Integrate icon library
- Set up E2E testing

---

**Document Version:** 1.0  
**Last Updated:** October 13, 2025  
**Maintainer:** Development Team
