"""
Narrative deduplication service for merging similar stories.

This service identifies and merges narratives that share significant entity overlap,
reducing redundancy in narrative detection.
"""

import logging
from typing import List, Dict, Any, Set, Tuple

logger = logging.getLogger(__name__)


def calculate_similarity(narrative_a: Dict[str, Any], narrative_b: Dict[str, Any]) -> float:
    """
    Calculate entity overlap similarity between two narratives using Jaccard similarity.
    
    Jaccard similarity = |intersection| / |union|
    Returns a score between 0.0 (no overlap) and 1.0 (identical entity sets).
    
    Args:
        narrative_a: First narrative dict with 'entities' key
        narrative_b: Second narrative dict with 'entities' key
    
    Returns:
        Similarity score (0.0 to 1.0)
    """
    entities_a = set(narrative_a.get("entities", []))
    entities_b = set(narrative_b.get("entities", []))
    
    # Handle empty entity sets
    if not entities_a or not entities_b:
        return 0.0
    
    # Calculate Jaccard similarity
    intersection = entities_a & entities_b
    union = entities_a | entities_b
    
    if not union:
        return 0.0
    
    similarity = len(intersection) / len(union)
    return similarity


def merge_similar_narratives(
    narratives: List[Dict[str, Any]], 
    threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Merge narratives with high entity overlap.
    
    Groups narratives by similarity threshold, keeps the narrative with the most
    articles in each group, and merges article lists. Duplicates are removed.
    
    Args:
        narratives: List of narrative dicts with 'entities', 'article_count', 'theme', 'story'
        threshold: Minimum Jaccard similarity to consider narratives as duplicates (default 0.7)
    
    Returns:
        Deduplicated list of narratives
    """
    if not narratives:
        return []
    
    # Track which narratives have been merged
    merged_indices = set()
    deduplicated = []
    
    for i, narrative_a in enumerate(narratives):
        if i in merged_indices:
            continue
        
        # Find all narratives similar to narrative_a
        similar_group = [narrative_a]
        similar_indices = {i}
        
        for j, narrative_b in enumerate(narratives[i+1:], start=i+1):
            if j in merged_indices:
                continue
            
            similarity = calculate_similarity(narrative_a, narrative_b)
            
            if similarity >= threshold:
                similar_group.append(narrative_b)
                similar_indices.add(j)
                logger.debug(
                    f"Found similar narratives (similarity={similarity:.2f}): "
                    f"'{narrative_a.get('theme')}' and '{narrative_b.get('theme')}'"
                )
        
        # Mark all similar narratives as merged
        merged_indices.update(similar_indices)
        
        # If we found duplicates, merge them
        if len(similar_group) > 1:
            merged_narrative = _merge_narrative_group(similar_group)
            deduplicated.append(merged_narrative)
            logger.info(
                f"Merged {len(similar_group)} similar narratives into: '{merged_narrative.get('theme')}'"
            )
        else:
            # No duplicates, keep original
            deduplicated.append(narrative_a)
    
    return deduplicated


def _merge_narrative_group(narratives: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merge a group of similar narratives into one.
    
    Strategy:
    - Keep the narrative with the highest article_count as the base
    - Merge all unique entities from the group
    - Sum article counts (assuming article lists would be merged in practice)
    
    Args:
        narratives: List of similar narrative dicts
    
    Returns:
        Merged narrative dict
    """
    # Sort by article_count (descending) to pick the strongest narrative
    sorted_narratives = sorted(
        narratives, 
        key=lambda n: n.get("article_count", 0), 
        reverse=True
    )
    
    # Use the narrative with most articles as the base
    base_narrative = sorted_narratives[0].copy()
    
    # Merge all unique entities
    all_entities: Set[str] = set()
    total_article_count = 0
    
    for narrative in sorted_narratives:
        all_entities.update(narrative.get("entities", []))
        total_article_count += narrative.get("article_count", 0)
    
    # Update the merged narrative
    base_narrative["entities"] = sorted(list(all_entities))  # Sort for consistency
    base_narrative["article_count"] = total_article_count
    
    return base_narrative


def deduplicate_narratives(
    narratives: List[Dict[str, Any]], 
    threshold: float = 0.7
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Main entry point for narrative deduplication.
    
    Args:
        narratives: List of narrative dicts
        threshold: Similarity threshold for merging (default 0.7)
    
    Returns:
        Tuple of (deduplicated_narratives, num_merged)
    """
    original_count = len(narratives)
    
    if original_count == 0:
        return [], 0
    
    deduplicated = merge_similar_narratives(narratives, threshold=threshold)
    num_merged = original_count - len(deduplicated)
    
    return deduplicated, num_merged
