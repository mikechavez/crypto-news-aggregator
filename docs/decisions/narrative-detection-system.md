# Narrative Detection System

## Overview

Narratives are **story-centric clusters** of related articles, distinct from signal scores which are **entity-centric metrics**.

| Feature | Signal Scores | Narratives |
|---------|---------------|------------|
| Question answered | "What entities are hot?" | "What stories are developing?" |
| Granularity | Per entity | Per story cluster |
| Used by | Signals page, Alerts | Narratives page, Briefings |
| Computation | Mention counting | LLM clustering + fingerprinting |

---

## How Narratives Are Determined

### Step 1: Article Enrichment

Each article is analyzed by Claude to extract:

- **Nucleus entity**: The central subject (e.g., "SEC", "Bitcoin ETF")
- **Actors**: People/orgs involved with salience scores (1-5)
- **Tensions**: Conflicts/dynamics in the story
- **Actions**: What's happening

### Step 2: Salience-Aware Clustering

Articles are grouped using actor overlap:

```
Article A: nucleus="SEC", actors=["SEC", "Coinbase", "Gensler"]
Article B: nucleus="SEC", actors=["SEC", "Binance", "enforcement"]
Article C: nucleus="SEC", actors=["SEC", "Coinbase", "lawsuit"]
    ↓
Cluster together → Same nucleus + overlapping actors
    ↓
Narrative: "SEC Regulatory Actions"
```

**Clustering rules (from narrative_service.py):**
- Min 3 articles per narrative
- Link strength threshold: 0.8 (actor overlap score)
- Ignores "ubiquitous" entities like Bitcoin, Ethereum (too common to cluster on)

### Step 3: Fingerprint Matching

Each cluster gets a fingerprint for deduplication:

```json
{
  "nucleus_entity": "SEC",
  "top_actors": ["Coinbase", "Gensler"],
  "key_actions": ["lawsuit", "enforcement"]
}
```

New clusters check for existing narratives with similar fingerprints (similarity > 0.5-0.6). If found, articles merge into existing narrative.

### Step 4: Lifecycle Tracking

Narratives have states based on activity:

```
emerging → rising → hot → cooling → dormant
                              ↓
                    (can be reactivated)
```

---

## Key Insight

**Narratives are story-centric, not entity-centric.**

- **Signal:** "Bitcoin is trending" (entity focus)
- **Narrative:** "SEC delays Bitcoin ETF decision amid market uncertainty" (story focus)

The briefing feature uses narratives because they provide **context and storylines**, not just "what's hot."

---

## Relevance to Briefings

From `briefing_agent.py`:

> "Your role is to synthesize ONLY the narratives listed below into an insightful briefing."

Briefings are built from narratives, which provide:
- Story context
- Key actors and their roles
- Tensions and dynamics
- Timeline of events

Signal scores serve as supplementary context ("Bitcoin mentions are up 40%") but are not the primary content source.
