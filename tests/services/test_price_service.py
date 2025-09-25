from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from src.crypto_news_aggregator.services.price_service import price_service


@pytest.mark.asyncio
async def test_generate_market_analysis_commentary_enriched_sections(monkeypatch):
    """Ensure enriched commentary includes volume, volatility, momentum, and news sections."""
    target_coin_id = 'bitcoin'
    competitor_coin_id = 'ethereum'
    now = datetime.now(timezone.utc)

    target_data = {
        'name': 'Bitcoin',
        'market_cap_rank': 1,
        'price_change_percentage_1h_in_currency': 1.2,
        'price_change_percentage_24h_in_currency': 3.4,
        'price_change_percentage_7d_in_currency': -1.5,
        'current_price': 42850.75,
        'total_volume': 2.1e10,
        'high_24h': 44000.0,
        'low_24h': 41000.0,
    }

    competitor_data = {
        'name': 'Ethereum',
        'price_change_percentage_24h_in_currency': 1.1,
    }

    market_data = {
        target_coin_id: target_data,
        competitor_coin_id: competitor_data,
    }

    historical_prices = {
        'prices': [
            ( (now - timedelta(days=idx)).timestamp() * 1000, 40000 + idx * 250 )
            for idx in reversed(range(8))
        ],
        'volumes': [
            ( (now - timedelta(days=idx)).timestamp() * 1000, 1.5e10 + idx * 1e9 )
            for idx in reversed(range(8))
        ],
    }

    related_news = [
        {
            'title': 'ETF inflows accelerate',
            'source': 'Cointelegraph',
            'sentiment_score': 0.35,
            'sentiment_label': 'Positive',
            'keywords': ['ETF', 'inflows', 'institutional'],
        },
        {
            'title': 'Mining difficulty climbs',
            'source': 'Decrypt',
            'sentiment_score': 0.1,
            'sentiment_label': 'Neutral',
            'keywords': ['mining', 'hashrate'],
        },
    ]

    monkeypatch.setattr(
        price_service,
        'get_markets_data',
        AsyncMock(return_value=market_data),
    )
    monkeypatch.setattr(
        price_service,
        'get_global_market_data',
        AsyncMock(return_value={
            'market_cap_percentage': {'btc': 47.2},
            'market_cap_change_percentage_24h_usd': 0.8,
        }),
    )
    monkeypatch.setattr(
        price_service,
        'get_historical_prices',
        AsyncMock(return_value=historical_prices),
    )
    monkeypatch.setattr(
        price_service,
        '_fetch_related_news',
        AsyncMock(return_value=related_news),
    )

    commentary = await price_service.generate_market_analysis_commentary(target_coin_id)

    assert 'Volume watch:' in commentary
    assert 'Volatility lens:' in commentary
    assert 'Momentum check:' in commentary
    assert 'News drivers:' in commentary
    assert 'Developing narratives:' in commentary
    assert 'Cointelegraph' in commentary
    assert 'Key peer check' in commentary
    assert "Bitcoin's market dominance" in commentary


@pytest.mark.asyncio
async def test_generate_market_analysis_commentary_handles_missing_data(monkeypatch):
    """Commentary should gracefully handle missing history and news."""
    target_coin_id = 'ethereum'

    monkeypatch.setattr(
        price_service,
        'get_markets_data',
        AsyncMock(return_value={
            target_coin_id: {
                'name': 'Ethereum',
                'market_cap_rank': 2,
                'price_change_percentage_1h_in_currency': None,
                'price_change_percentage_24h_in_currency': None,
                'price_change_percentage_7d_in_currency': None,
                'current_price': None,
                'total_volume': None,
                'high_24h': None,
                'low_24h': None,
            },
            'bitcoin': {
                'name': 'Bitcoin',
                'price_change_percentage_24h_in_currency': 0.5,
            },
        }),
    )
    monkeypatch.setattr(
        price_service,
        'get_global_market_data',
        AsyncMock(return_value={}),
    )
    monkeypatch.setattr(
        price_service,
        'get_historical_prices',
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        price_service,
        '_fetch_related_news',
        AsyncMock(return_value=[]),
    )

    commentary = await price_service.generate_market_analysis_commentary(target_coin_id)

    assert commentary.startswith('Ethereum')
    assert 'Volume data unavailable' in commentary or 'Volume watch:' in commentary
    assert 'Volatility lens:' in commentary
    assert 'Momentum check:' in commentary
    assert 'No high-signal news surfaced' in commentary
    assert 'Bitcoin' not in commentary.split('Developing narratives')[1]
