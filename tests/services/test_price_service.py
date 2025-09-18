import pytest
from src.crypto_news_aggregator.services.price_service import price_service

@pytest.mark.asyncio
async def test_generate_market_analysis_commentary():
    """Test that the market analysis commentary is generated correctly."""
    # Ensure the service is in testing mode
    price_service.settings.TESTING_MODE = True

    # Test for Bitcoin
    commentary_btc = await price_service.generate_market_analysis_commentary('bitcoin')
    assert isinstance(commentary_btc, str)
    assert 'Bitcoin' in commentary_btc
    assert 'rank' in commentary_btc
    assert 'outperforming' in commentary_btc or 'underperforming' in commentary_btc
    assert 'volatility' in commentary_btc
    assert 'dominance' in commentary_btc

    # Test for Ethereum
    commentary_eth = await price_service.generate_market_analysis_commentary('ethereum')
    assert isinstance(commentary_eth, str)
    assert 'Ethereum' in commentary_eth
    assert 'rank' in commentary_eth
    assert 'outperforming' in commentary_eth or 'underperforming' in commentary_eth
    assert 'volatility' in commentary_eth
    assert 'dominance' not in commentary_eth  # Dominance is only for BTC

    # Close the session
    await price_service.close()
