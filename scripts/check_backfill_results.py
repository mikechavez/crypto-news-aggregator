"""Check the results of the narrative backfill operation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto_news_aggregator.db.mongodb import mongo_manager

def main():
    # Get synchronous database connection
    db = mongo_manager.get_database()

    # Total articles
    total_articles = db.articles.count_documents({})

    # Articles with narrative data (new format)
    articles_with_narrative_summary = db.articles.count_documents({
        'narrative_summary': {'$exists': True, '$ne': None, '$ne': ''}
    })
    
    articles_with_actors = db.articles.count_documents({
        'actors': {'$exists': True, '$ne': None, '$ne': []}
    })
    
    articles_with_nucleus = db.articles.count_documents({
        'nucleus_entity': {'$exists': True, '$ne': None, '$ne': ''}
    })

    # Articles with entities (old format)
    articles_with_entities = db.articles.count_documents({
        'entities': {'$exists': True, '$ne': None, '$ne': []}
    })

    # Articles with narrative_id (cluster assignment)
    articles_with_narratives = db.articles.count_documents({
        'narrative_id': {'$exists': True, '$ne': None}
    })

    # Total narratives (clusters)
    total_narratives = db.narratives.count_documents({})

    # Count unique narrative_ids in articles
    unique_narratives_in_use = len(db.articles.distinct('narrative_id', {'narrative_id': {'$ne': None}}))

    print('=' * 70)
    print('DATABASE STATE AFTER BACKFILL')
    print('=' * 70)
    print(f'Total articles in database:           {total_articles:>6}')
    print()
    print('NARRATIVE DATA (Article-level):')
    print(f'  Articles with narrative_summary:    {articles_with_narrative_summary:>6}')
    print(f'  Articles with actors:               {articles_with_actors:>6}')
    print(f'  Articles with nucleus_entity:       {articles_with_nucleus:>6}')
    print()
    print('ENTITY DATA (Legacy):')
    print(f'  Articles with entities extracted:   {articles_with_entities:>6}')
    print()
    print('NARRATIVE CLUSTERS:')
    print(f'  Total narrative clusters:           {total_narratives:>6}')
    print(f'  Articles assigned to clusters:      {articles_with_narratives:>6}')
    print(f'  Clusters with articles:             {unique_narratives_in_use:>6}')
    print('=' * 70)

    # Get top narratives by article count
    print()
    print('TOP 10 NARRATIVES BY ARTICLE COUNT:')
    print('-' * 60)

    pipeline = [
        {'$match': {'narrative_id': {'$ne': None}}},
        {'$group': {'_id': '$narrative_id', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': 10}
    ]

    top_narrative_ids = list(db.articles.aggregate(pipeline))

    for i, item in enumerate(top_narrative_ids, 1):
        narrative = db.narratives.find_one({'_id': item['_id']})
        if narrative:
            title = narrative.get('title', 'Unknown')
            print(f'{i}. {title[:50]}... ({item["count"]} articles)')

if __name__ == '__main__':
    main()
