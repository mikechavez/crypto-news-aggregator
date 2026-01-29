"""
Selective Article Processing
Implements smart filtering to reduce LLM API calls by ~50%:
1. Premium sources always get LLM processing
2. Mid-tier sources use LLM only for important keywords
3. Low-priority sources always use regex extraction
"""

import re
from typing import List, Dict, Any, Set, Optional
from datetime import datetime
from bson import ObjectId


class SelectiveArticleProcessor:
    """
    Intelligently decides which articles need full LLM processing
    vs simple keyword extraction
    """
    
    # Premium sources - ALWAYS use LLM
    PREMIUM_SOURCES = {
        'coindesk',
        'cointelegraph', 
        'decrypt',
        'theblock',
        'bloomberg',
        'reuters',
        'cnbc'
    }
    
    # Low-priority sources - NEVER use LLM
    SKIP_LLM_SOURCES = {
        'bitcoinmagazine',
        'cryptoslate',
        'cryptopotato',
        'newsbtc'
    }
    
    # Keywords that indicate important/breaking news
    IMPORTANT_KEYWORDS = {
        # Major cryptos
        'bitcoin', 'btc', 'ethereum', 'eth', 'solana', 'sol',
        
        # Regulation & legal
        'sec', 'regulation', 'lawsuit', 'ban', 'cftc', 'law',
        
        # Security events
        'hack', 'hacked', 'exploit', 'breach', 'vulnerability',
        
        # Market movements
        'crash', 'surge', 'plunge', 'soar', 'rally', 'dump',
        'all-time high', 'ath', 'record', 'milestone',
        
        # Institutional
        'institutional', 'etf', 'approval', 'wall street',
        
        # Technology
        'fork', 'upgrade', 'launch', 'mainnet', 'testnet',
        
        # Business
        'partnership', 'acquisition', 'merger', 'investment',
        'bankruptcy', 'collapse', 'liquidation'
    }
    
    # Entity mapping for regex extraction (top 20+ cryptos)
    ENTITY_MAPPING = {
        "Bitcoin": ["btc", "$btc", "bitcoin", "xbt"],
        "Ethereum": ["eth", "$eth", "ethereum", "ether"],
        "Solana": ["sol", "$sol", "solana"],
        "BNB": ["bnb", "$bnb", "binance coin"],
        "XRP": ["xrp", "$xrp", "ripple"],
        "Cardano": ["ada", "$ada", "cardano"],
        "Dogecoin": ["doge", "$doge", "dogecoin"],
        "Polygon": ["matic", "$matic", "polygon"],
        "Polkadot": ["dot", "$dot", "polkadot"],
        "Avalanche": ["avax", "$avax", "avalanche"],
        "Chainlink": ["link", "$link", "chainlink"],
        "Uniswap": ["uni", "$uni", "uniswap"],
        "Litecoin": ["ltc", "$ltc", "litecoin"],
        "Cosmos": ["atom", "$atom", "cosmos"],
        "Tron": ["trx", "$trx", "tron"],
        "Stellar": ["xlm", "$xlm", "stellar"],
        "Monero": ["xmr", "$xmr", "monero"],
        "Algorand": ["algo", "$algo", "algorand"],
        "VeChain": ["vet", "$vet", "vechain"],
        "Filecoin": ["fil", "$fil", "filecoin"],
        "Shiba Inu": ["shib", "$shib", "shiba inu"],
        "Arbitrum": ["arb", "$arb", "arbitrum"],
        "Optimism": ["op", "$op", "optimism"],
        "Aptos": ["apt", "$apt", "aptos"]
    }
    
    def __init__(self, db):
        """Initialize selective processor with database connection"""
        self.db = db
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for fast entity extraction"""
        self.entity_patterns = {}
        
        for canonical, variants in self.ENTITY_MAPPING.items():
            # Create pattern that matches any variant (case-insensitive, word boundaries)
            pattern = r'\b(' + '|'.join(re.escape(v) for v in variants) + r')\b'
            self.entity_patterns[canonical] = re.compile(pattern, re.IGNORECASE)
    
    def should_use_llm(self, article: Dict) -> bool:
        """
        Decide if article should get full LLM processing
        
        Decision tree:
        1. Premium source? → Always LLM
        2. Skip LLM source? → Never LLM
        3. Mid-tier source? → LLM if important keywords in title
        
        Args:
            article: Article dict with 'source' and 'title'
        
        Returns:
            True if should use LLM, False if regex extraction sufficient
        """
        source = article.get('source', '').lower()
        title = article.get('title', '').lower()
        
        # Premium sources always get LLM
        if source in self.PREMIUM_SOURCES:
            return True
        
        # Skip LLM for low-priority sources
        if source in self.SKIP_LLM_SOURCES:
            return False
        
        # For mid-tier sources, check keywords
        return self._has_important_keywords(title)
    
    def _has_important_keywords(self, text: str) -> bool:
        """
        Check if text contains important keywords
        
        Args:
            text: Text to check (usually article title)
        
        Returns:
            True if contains important keywords
        """
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.IMPORTANT_KEYWORDS)
    
    async def extract_entities_simple(
        self,
        article_id: ObjectId,
        article: Dict
    ) -> List[Dict]:
        """
        Extract entities using regex/keyword matching (no LLM)
        
        Fast, free, but lower confidence than LLM extraction.
        
        Args:
            article_id: MongoDB ObjectId of article
            article: Article dictionary with 'title' and 'text'
        
        Returns:
            List of entity mention dictionaries
        """
        text = f"{article.get('title', '')} {article.get('text', '')}".lower()
        
        entities = []
        seen_entities = set()
        
        # Match entities using compiled regex patterns
        for canonical, pattern in self.entity_patterns.items():
            if pattern.search(text):
                if canonical not in seen_entities:
                    entities.append({
                        "entity": canonical,
                        "entity_type": "cryptocurrency",
                        "article_id": article_id,
                        "is_primary": False,
                        "confidence": 0.7,  # Lower confidence for regex
                        "source": article.get('source', 'unknown'),
                        "created_at": datetime.utcnow()
                    })
                    seen_entities.add(canonical)
        
        # Try to identify primary entity (first mentioned in title)
        title_lower = article.get('title', '').lower()
        for canonical, pattern in self.entity_patterns.items():
            if pattern.search(title_lower):
                # Mark first title mention as primary
                for entity in entities:
                    if entity['entity'] == canonical:
                        entity['is_primary'] = True
                        entity['confidence'] = 0.85  # Higher confidence for title
                        break
                break
        
        return entities
    
    async def process_article(
        self,
        article: Dict,
        llm_client
    ) -> Dict[str, Any]:
        """
        Process article with appropriate method (LLM or simple)
        
        Args:
            article: Article dictionary (must include '_id')
            llm_client: OptimizedAnthropicLLM instance from Task 3
        
        Returns:
            Dict with:
                - article_id: ObjectId
                - entities: List of entity mention dicts
                - method: "llm" or "regex"
                - model: Model name or None
        """
        article_id = article['_id']
        
        # Decide processing method
        use_llm = self.should_use_llm(article)
        
        if use_llm:
            # Full LLM processing (uses Task 3's optimized client)
            entity_result = await llm_client.extract_entities_batch([article])
            entities = entity_result[0].get('entities', [])
            
            # Convert to entity mention format
            entity_mentions = [
                {
                    "entity": e['name'],
                    "entity_type": e['type'],
                    "article_id": article_id,
                    "is_primary": e.get('is_primary', False),
                    "confidence": e.get('confidence', 0.9),
                    "source": article.get('source', 'unknown'),
                    "created_at": datetime.utcnow()
                }
                for e in entities
            ]
            
            return {
                "article_id": article_id,
                "entities": entity_mentions,
                "method": "llm",
                "model": llm_client.HAIKU_MODEL
            }
        else:
            # Simple regex extraction (free, fast)
            entity_mentions = await self.extract_entities_simple(article_id, article)
            
            return {
                "article_id": article_id,
                "entities": entity_mentions,
                "method": "regex",
                "model": None
            }
    
    async def batch_process_articles(
        self,
        articles: List[Dict],
        llm_client
    ) -> Dict[str, Any]:
        """
        Process multiple articles efficiently
        
        Separates articles by processing method and batches LLM calls.
        
        Args:
            articles: List of article dictionaries (with '_id')
            llm_client: OptimizedAnthropicLLM instance
        
        Returns:
            Summary dict with counts and all entity mentions
        """
        llm_articles = []
        simple_articles = []
        
        # Separate articles by processing method
        for article in articles:
            if self.should_use_llm(article):
                llm_articles.append(article)
            else:
                simple_articles.append(article)
        
        results = {
            "total_articles": len(articles),
            "llm_processed": len(llm_articles),
            "simple_processed": len(simple_articles),
            "entity_mentions": []
        }
        
        # Process LLM articles in batch
        if llm_articles:
            entity_results = await llm_client.extract_entities_batch(llm_articles)
            
            for article, entity_result in zip(llm_articles, entity_results):
                entities = entity_result.get('entities', [])
                
                for e in entities:
                    mention = {
                        "entity": e['name'],
                        "entity_type": e['type'],
                        "article_id": article['_id'],
                        "is_primary": e.get('is_primary', False),
                        "confidence": e.get('confidence', 0.9),
                        "source": article.get('source', 'unknown'),
                        "created_at": datetime.utcnow()
                    }
                    results["entity_mentions"].append(mention)
        
        # Process simple articles
        for article in simple_articles:
            entity_mentions = await self.extract_entities_simple(
                article['_id'],
                article
            )
            results["entity_mentions"].extend(entity_mentions)
        
        # Insert all entity mentions to database
        if results["entity_mentions"]:
            await self.db.entity_mentions.insert_many(results["entity_mentions"])
        
        return results
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get statistics about processing decisions
        
        Returns:
            Dict with source tier information and counts
        """
        return {
            "premium_sources": sorted(list(self.PREMIUM_SOURCES)),
            "premium_count": len(self.PREMIUM_SOURCES),
            "skip_llm_sources": sorted(list(self.SKIP_LLM_SOURCES)),
            "skip_llm_count": len(self.SKIP_LLM_SOURCES),
            "important_keywords_count": len(self.IMPORTANT_KEYWORDS),
            "tracked_entities": len(self.ENTITY_MAPPING),
            "expected_llm_percentage": "~50%"
        }


# Helper function
def create_processor(db) -> SelectiveArticleProcessor:
    """
    Create a SelectiveArticleProcessor instance
    
    Args:
        db: MongoDB database instance
    
    Returns:
        SelectiveArticleProcessor instance
    """
    return SelectiveArticleProcessor(db)
