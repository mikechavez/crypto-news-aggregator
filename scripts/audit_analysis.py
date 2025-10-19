"""Comprehensive narrative quality analysis - all-in-one module."""

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Dict, List, Any

from src.crypto_news_aggregator.services.narrative_themes import calculate_fingerprint_similarity

# Constants
GENERIC_ENTITIES = ['BTC', 'ETH', 'crypto', 'Bitcoin', 'Ethereum', 'blockchain', 
                    'market', 'price', 'traders', 'investors', 'Crypto market']
GENERIC_TITLE_KEYWORDS = ['Activity', 'Updates', 'News', 'Daily', 'Overview', 
                          'Movement', 'Comprehensive', 'Spanning']
GENERIC_SUMMARY_PHRASES = ['Recent developments', 'General updates', 'Market overview', 
                           'Latest news', 'Price movements']


def parse_datetime(dt) -> datetime:
    """Parse datetime from string or datetime object, ensuring timezone awareness."""
    if dt is None:
        return None
    if isinstance(dt, str):
        return datetime.fromisoformat(dt.replace('Z', '+00:00'))
    elif isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    return None


def run_full_audit(narratives: List[Dict], now: datetime):
    """Run complete audit and generate reports."""
    
    # Collect all data
    audit_data = {
        'metadata': {},
        'issues': {},
        'scores': [],
        'recommendations': []
    }
    
    total = len(narratives)
    
    # ===== PART 1: METADATA =====
    print(f"\n{'=' * 80}\nPART 1: AUDIT METADATA\n{'=' * 80}")
    
    total_articles = sum(n.get('article_count', 0) for n in narratives)
    article_counts = [n.get('article_count', 0) for n in narratives]
    median_articles = sorted(article_counts)[len(article_counts) // 2] if article_counts else 0
    avg_articles = total_articles / total if total > 0 else 0
    
    ages = []
    for n in narratives:
        created_at = parse_datetime(n.get('created_at'))
        if created_at:
            ages.append((now - created_at).days)
    median_age = sorted(ages)[len(ages) // 2] if ages else 0
    
    entity_counter = Counter([n.get('nucleus_entity', 'Unknown') for n in narratives])
    top_entities = entity_counter.most_common(5)
    
    complete = sum(1 for n in narratives if all([n.get('title'), n.get('summary'), 
                   n.get('entities') or n.get('actors'), n.get('fingerprint')]))
    complete_pct = (complete / total * 100) if total > 0 else 0
    
    print(f"\n📊 Overview:")
    print(f"  Total narratives: {total}")
    print(f"  Total articles: {total_articles}")
    print(f"  Median article count: {median_articles}")
    print(f"  Average articles: {avg_articles:.2f}")
    print(f"  Median age: {median_age} days")
    print(f"\n🏆 Top 5 entities:")
    for entity, count in top_entities:
        print(f"    {entity}: {count}")
    print(f"\n✅ Complete data: {complete} ({complete_pct:.1f}%)")
    
    audit_data['metadata'] = {
        'total_narratives': total,
        'total_articles': total_articles,
        'median_article_count': median_articles,
        'avg_article_count': avg_articles,
        'median_age': median_age,
        'top_entities': [(e, c) for e, c in top_entities],
        'complete_pct': complete_pct
    }
    
    # ===== PART 2: ISSUES =====
    print(f"\n{'=' * 80}\nPART 2: ISSUE CATEGORIES\n{'=' * 80}")
    
    # A. Generic narratives
    generic = []
    for n in narratives:
        entity = n.get('nucleus_entity', '')
        title = n.get('title', '')
        summary = n.get('summary', '')
        
        is_gen_entity = entity in GENERIC_ENTITIES
        is_gen_title = len(title.split()) < 4 or any(k.lower() in title.lower() for k in GENERIC_TITLE_KEYWORDS)
        is_gen_summary = any(p.lower() in summary.lower() for p in GENERIC_SUMMARY_PHRASES)
        
        if is_gen_entity or is_gen_title or is_gen_summary:
            generic.append({
                'id': str(n.get('_id')),
                'title': title,
                'entity': entity,
                'articles': n.get('article_count', 0),
                'double_penalty': is_gen_title and is_gen_summary
            })
    
    print(f"\n🔤 A. Generic/Vague: {len(generic)} ({len(generic)/total*100:.1f}%)")
    print(f"  Total articles: {sum(g['articles'] for g in generic)}")
    print(f"  Double penalty: {sum(1 for g in generic if g['double_penalty'])}")
    for i, g in enumerate(generic[:5], 1):
        print(f"    {i}. {g['title'][:60]} (Entity: {g['entity']}, Articles: {g['articles']})")
    
    audit_data['issues']['generic'] = generic
    
    # B. Low article count
    low_count = {'emerging': [], 'failed': [], 'stalled': []}
    for n in narratives:
        count = n.get('article_count', 0)
        created = n.get('created_at')
        if created:
            created_dt = parse_datetime(created)
            if not created_dt:
                continue
            age = (now - created_dt).days
            if count < 3 and age < 3:
                low_count['emerging'].append({'id': str(n.get('_id')), 'title': n.get('title', ''), 
                                              'articles': count, 'age': age})
            elif count < 3 and age > 7:
                low_count['failed'].append({'id': str(n.get('_id')), 'title': n.get('title', ''), 
                                           'articles': count, 'age': age})
            elif count < 5 and age > 14:
                low_count['stalled'].append({'id': str(n.get('_id')), 'title': n.get('title', ''), 
                                            'articles': count, 'age': age})
    
    print(f"\n📉 B. Low Article Count:")
    for cat, items in low_count.items():
        print(f"  {cat.upper()}: {len(items)}")
        for i, item in enumerate(items[:3], 1):
            print(f"    {i}. {item['title'][:60]} (Articles: {item['articles']}, Age: {item['age']}d)")
    
    audit_data['issues']['low_count'] = low_count
    
    # C. Stale narratives
    stale = {'7-14d': [], '14-30d': [], '30d+': []}
    mismatches = []
    for n in narratives:
        updated = n.get('last_updated')
        if updated:
            updated_dt = parse_datetime(updated)
            if not updated_dt:
                continue
            days = (now - updated_dt).days
            if days > 7:
                item = {'id': str(n.get('_id')), 'title': n.get('title', ''), 'days': days}
                if days <= 14:
                    stale['7-14d'].append(item)
                elif days <= 30:
                    stale['14-30d'].append(item)
                else:
                    stale['30d+'].append(item)
                
                if n.get('lifecycle_state') in ['hot', 'emerging']:
                    mismatches.append(item)
    
    print(f"\n⏰ C. Stale Narratives:")
    for bucket, items in stale.items():
        print(f"  {bucket}: {len(items)}")
    print(f"  ⚠️  Lifecycle mismatches: {len(mismatches)}")
    
    audit_data['issues']['stale'] = stale
    audit_data['issues']['mismatches'] = mismatches
    
    # D. Duplicates
    title_groups = defaultdict(list)
    for n in narratives:
        if n.get('title'):
            title_groups[n['title'].lower().strip()].append(n)
    
    exact_dups = {k: v for k, v in title_groups.items() if len(v) > 1}
    
    print(f"\n🔄 D. Duplicates:")
    print(f"  Exact: {len(exact_dups)} groups, {sum(len(v) for v in exact_dups.values())} narratives")
    
    audit_data['issues']['duplicates'] = {
        'exact_count': len(exact_dups),
        'exact_narratives': sum(len(v) for v in exact_dups.values())
    }
    
    # E. Missing data
    missing = {
        'title': sum(1 for n in narratives if not n.get('title')),
        'summary': sum(1 for n in narratives if not n.get('summary')),
        'entities': sum(1 for n in narratives if not (n.get('entities') or n.get('actors'))),
        'fingerprint': sum(1 for n in narratives if not n.get('fingerprint')),
        'zero_article_bug': sum(1 for n in narratives if n.get('article_count', 0) == 0 and n.get('lifecycle_state') != 'dormant')
    }
    
    print(f"\n❌ E. Missing Data:")
    for field, count in missing.items():
        pct = (count / total * 100) if total > 0 else 0
        print(f"  {field}: {count} ({pct:.1f}%)")
    
    audit_data['issues']['missing'] = missing
    
    # F. Old schema
    old_schema = {
        'nucleus_no_title': sum(1 for n in narratives if n.get('nucleus_entity') and not n.get('title')),
        'actors_no_entities': sum(1 for n in narratives if n.get('actors') and not n.get('entities')),
        'narrative_summary_no_summary': sum(1 for n in narratives if n.get('narrative_summary') and not n.get('summary'))
    }
    
    print(f"\n🏛️  F. Old Schema: {sum(old_schema.values())} total")
    for schema_type, count in old_schema.items():
        print(f"  {schema_type}: {count}")
    
    audit_data['issues']['old_schema'] = old_schema
    
    # ===== PART 3: QUALITY SCORES =====
    print(f"\n{'=' * 80}\nPART 3: QUALITY SCORING (0-110)\n{'=' * 80}")
    
    scored = []
    for n in narratives:
        score = 100
        issues_list = []
        
        # Check issues
        title = n.get('title', '')
        summary = n.get('summary', '')
        is_gen_title = len(title.split()) < 4 or any(k.lower() in title.lower() for k in GENERIC_TITLE_KEYWORDS)
        is_gen_summary = any(p.lower() in summary.lower() for p in GENERIC_SUMMARY_PHRASES)
        
        if is_gen_title and is_gen_summary:
            score -= 40
            issues_list.append('generic_both')
        elif is_gen_title or is_gen_summary or n.get('nucleus_entity') in GENERIC_ENTITIES:
            score -= 20
            issues_list.append('generic')
        
        # Low count
        if n.get('created_at'):
            created_dt = parse_datetime(n.get('created_at'))
            if not created_dt:
                continue
            age = (now - created_dt).days
            count = n.get('article_count', 0)
            if (count < 3 and age > 7) or (count < 5 and age > 14):
                score -= 20
                issues_list.append('low_count')
        
        # Stale
        if n.get('last_updated'):
            updated_dt = parse_datetime(n.get('last_updated'))
            if not updated_dt:
                continue
            days = (now - updated_dt).days
            if days > 7:
                score -= 20
                issues_list.append('stale')
        
        # Missing data
        if not all([n.get('title'), n.get('summary'), n.get('entities') or n.get('actors'), n.get('fingerprint')]):
            score -= 20
            issues_list.append('missing_data')
        
        # Duplicate
        if title and title.lower().strip() in exact_dups:
            score -= 20
            issues_list.append('duplicate')
        
        # High performer bonus
        if n.get('article_count', 0) >= 10 and n.get('lifecycle_state') in ['hot', 'rising']:
            score += 10
            issues_list.append('high_performer')
        
        scored.append({
            'id': str(n.get('_id')),
            'title': title,
            'score': score,
            'articles': n.get('article_count', 0),
            'lifecycle': n.get('lifecycle_state', 'N/A'),
            'issues': issues_list
        })
    
    # Distribution
    buckets = {'90-110': 0, '70-89': 0, '50-69': 0, '30-49': 0, '0-29': 0}
    for s in scored:
        if s['score'] >= 90:
            buckets['90-110'] += 1
        elif s['score'] >= 70:
            buckets['70-89'] += 1
        elif s['score'] >= 50:
            buckets['50-69'] += 1
        elif s['score'] >= 30:
            buckets['30-49'] += 1
        else:
            buckets['0-29'] += 1
    
    print(f"\n📊 Score Distribution:")
    for bucket, count in buckets.items():
        print(f"  {bucket}: {count}")
    
    print(f"\n⚠️  TOP 5 OFFENDERS:")
    for i, s in enumerate(sorted(scored, key=lambda x: x['score'])[:5], 1):
        print(f"\n  {i}. Score: {s['score']}/110")
        print(f"     {s['title'][:60]}")
        print(f"     Articles: {s['articles']}, State: {s['lifecycle']}")
        print(f"     Issues: {', '.join(s['issues'])}")
    
    audit_data['scores'] = scored
    
    # ===== PART 4: RECOMMENDATIONS =====
    print(f"\n{'=' * 80}\nPART 4: CLEANUP RECOMMENDATIONS\n{'=' * 80}")
    
    recommendations = []
    
    if generic:
        recommendations.append({
            'category': 'Generic',
            'action': 'DELETE',
            'confidence': 'HIGH',
            'count': len(generic),
            'articles': sum(g['articles'] for g in generic),
            'priority': 'MEDIUM'
        })
    
    if exact_dups:
        recommendations.append({
            'category': 'Duplicates',
            'action': 'MERGE',
            'confidence': 'MEDIUM',
            'count': sum(len(v) for v in exact_dups.values()),
            'priority': 'HIGH'
        })
    
    failed_stalled_count = len(low_count['failed']) + len(low_count['stalled'])
    if failed_stalled_count > 0:
        recommendations.append({
            'category': 'Failed/Stalled',
            'action': 'DELETE',
            'confidence': 'HIGH',
            'count': failed_stalled_count,
            'priority': 'HIGH'
        })
    
    if mismatches:
        recommendations.append({
            'category': 'Lifecycle Mismatch',
            'action': 'UPDATE STATE',
            'confidence': 'HIGH',
            'count': len(mismatches),
            'priority': 'HIGH'
        })
    
    print(f"\n| Category | Action | Confidence | Count | Priority |")
    print(f"|----------|--------|-----------|-------|----------|")
    for rec in recommendations:
        print(f"| {rec['category']} | {rec['action']} | {rec['confidence']} | {rec['count']} | {rec['priority']} |")
    
    audit_data['recommendations'] = recommendations
    
    # ===== WRITE REPORTS =====
    write_markdown_report(audit_data)
    write_json_report(audit_data)


def write_markdown_report(data: Dict):
    """Write human-readable markdown report."""
    with open('NARRATIVE_QUALITY_AUDIT.md', 'w') as f:
        f.write("# Narrative Quality Audit Report\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        
        f.write("## Part 1: Metadata\n\n")
        m = data['metadata']
        f.write(f"- **Total narratives**: {m['total_narratives']}\n")
        f.write(f"- **Total articles**: {m['total_articles']}\n")
        f.write(f"- **Median article count**: {m['median_article_count']}\n")
        f.write(f"- **Average articles**: {m['avg_article_count']:.2f}\n")
        f.write(f"- **Median age**: {m['median_age']} days\n")
        f.write(f"- **Complete data**: {m['complete_pct']:.1f}%\n\n")
        
        f.write("### Top 5 Entities\n\n")
        for entity, count in m['top_entities']:
            f.write(f"- {entity}: {count}\n")
        
        f.write("\n## Part 2: Issues\n\n")
        
        f.write(f"### Generic Narratives: {len(data['issues']['generic'])}\n\n")
        f.write(f"### Low Article Count\n\n")
        for cat, items in data['issues']['low_count'].items():
            f.write(f"- {cat}: {len(items)}\n")
        
        f.write(f"\n### Stale Narratives\n\n")
        for bucket, items in data['issues']['stale'].items():
            f.write(f"- {bucket}: {len(items)}\n")
        f.write(f"- Lifecycle mismatches: {len(data['issues']['mismatches'])}\n")
        
        f.write(f"\n### Duplicates\n\n")
        f.write(f"- Exact: {data['issues']['duplicates']['exact_count']} groups\n")
        
        f.write(f"\n### Missing Data\n\n")
        for field, count in data['issues']['missing'].items():
            f.write(f"- {field}: {count}\n")
        
        f.write("\n## Part 3: Quality Scores\n\n")
        f.write("See JSON report for detailed scores.\n\n")
        
        f.write("## Part 4: Recommendations\n\n")
        f.write("| Category | Action | Confidence | Count | Priority |\n")
        f.write("|----------|--------|-----------|-------|----------|\n")
        for rec in data['recommendations']:
            f.write(f"| {rec['category']} | {rec['action']} | {rec['confidence']} | {rec['count']} | {rec['priority']} |\n")


def write_json_report(data: Dict):
    """Write structured JSON report."""
    with open('NARRATIVE_QUALITY_AUDIT.json', 'w') as f:
        json.dump(data, f, indent=2, default=str)
