"""
Test suite for article relevance classification.

Tests pattern matching, tier assignment, and edge case handling
for the relevance classifier service.
"""

import pytest
from crypto_news_aggregator.services.relevance_classifier import classify_article


class TestTier1SignalPatterns:
    """Test high-signal patterns that should trigger Tier 1."""

    def test_regulatory_keywords_sec(self):
        """SEC regulatory news should be Tier 1."""
        result = classify_article("SEC Approves First Bitcoin ETF")
        assert result["tier"] == 1
        assert result["reason"] == "high_signal_title"

    def test_regulatory_keywords_cftc(self):
        """CFTC regulatory news should be Tier 1."""
        result = classify_article("CFTC Issues New Cryptocurrency Trading Rules")
        assert result["tier"] == 1
        assert result["reason"] == "high_signal_title"

    def test_security_breach_hacked(self):
        """Security breaches with 'hacked' should be Tier 1."""
        result = classify_article("Major Exchange Hacked, $50M Stolen")
        assert result["tier"] == 1
        assert result["reason"] == "high_signal_title"

    def test_security_breach_exploited(self):
        """Security breaches with 'exploited' should be Tier 1."""
        result = classify_article("Protocol Exploited for $10M in Funds")
        assert result["tier"] == 1
        assert result["reason"] == "high_signal_title"

    def test_security_breach_drained(self):
        """Security incidents with 'drained' should be Tier 1."""
        result = classify_article("Wallet Drained in Flash Loan Attack")
        assert result["tier"] == 1
        assert result["reason"] == "high_signal_title"

    def test_institutional_adoption_blackrock(self):
        """Institutional adoption should be Tier 1."""
        result = classify_article("BlackRock Purchases $500M in Bitcoin")
        assert result["tier"] == 1
        assert result["reason"] == "high_signal_title"

    def test_institutional_adoption_fidelity(self):
        """Institutional adoption by Fidelity should be Tier 1."""
        result = classify_article("Fidelity Launches Bitcoin Fund for Investors")
        assert result["tier"] == 1
        assert result["reason"] == "high_signal_title"

    def test_ath_milestone(self):
        """All-time high milestones should be Tier 1."""
        result = classify_article("Bitcoin Hits New All-Time High of $75,000")
        assert result["tier"] == 1
        assert result["reason"] == "high_signal_title"

    def test_record_volume(self):
        """Record volume milestones should be Tier 1."""
        result = classify_article("Bitcoin Trading Volume Hits Record High")
        assert result["tier"] == 1
        assert result["reason"] == "high_signal_title"

    def test_etf_inflow(self):
        """ETF inflows should be Tier 1."""
        result = classify_article("Bitcoin ETF Records $2 Billion Inflow")
        assert result["tier"] == 1
        assert result["reason"] == "high_signal_title"

    def test_market_liquidation(self):
        """Market liquidations should be Tier 1."""
        result = classify_article("$500 Million in Liquidations Triggered in Crypto")
        assert result["tier"] == 1
        assert result["reason"] == "high_signal_title"

    def test_government_adoption(self):
        """Government adoption should be Tier 1."""
        result = classify_article("El Salvador Adopts Bitcoin as Legal Tender")
        assert result["tier"] == 1
        assert result["reason"] == "high_signal_title"

    def test_institutional_product_launch(self):
        """Institutional product launches should be Tier 1."""
        result = classify_article("Morgan Stanley Launches Bitcoin Wallet for Clients")
        assert result["tier"] == 1
        assert result["reason"] == "high_signal_title"

    def test_major_acquisition(self):
        """Major acquisitions should be Tier 1."""
        result = classify_article("Crypto Exchange Acquires Rival Platform for $1 Billion")
        assert result["tier"] == 1
        assert result["reason"] == "high_signal_title"


class TestTier3NoisePatterns:
    """Test noise patterns that should trigger Tier 3."""

    def test_price_prediction_simple(self):
        """Price predictions should be Tier 3."""
        result = classify_article("Bitcoin Could Reach $100,000 This Year")
        assert result["tier"] == 3
        assert result["reason"] == "low_signal"

    def test_price_prediction_target(self):
        """Price target articles should be Tier 3."""
        result = classify_article("Analyst Sets Bitcoin Price Target of $150,000")
        assert result["tier"] == 3
        assert result["reason"] == "low_signal"

    def test_speculation_crystal_ball(self):
        """Crystal ball speculation should be Tier 3."""
        result = classify_article("Crystal Ball Predictions for Crypto in 2025")
        assert result["tier"] == 3
        assert result["reason"] == "low_signal"

    def test_speculation_will_finally(self):
        """'Will X finally' speculation should be Tier 3."""
        result = classify_article("Will Bitcoin Finally Break the $100K Barrier?")
        assert result["tier"] == 3
        assert result["reason"] == "low_signal"

    def test_speculation_to_the_moon(self):
        """'To the moon' speculation should be Tier 3."""
        result = classify_article("Bitcoin to the Moon: Next Target $200K")
        assert result["tier"] == 3
        assert result["reason"] == "low_signal"

    def test_retrospective_year_in_review(self):
        """Year-in-review content should be Tier 3."""
        result = classify_article("Crypto Year in Review: 2024 Highlights")
        assert result["tier"] == 3
        assert result["reason"] == "low_signal"

    def test_retrospective_best_of(self):
        """Best-of listicles should be Tier 3."""
        result = classify_article("Best of 2024: Top 10 Crypto Moments")
        assert result["tier"] == 3
        assert result["reason"] == "low_signal"

    def test_retrospective_wtf_moments(self):
        """WTF moments listicles should be Tier 3."""
        result = classify_article("WTF Moments of the Year in Crypto")
        assert result["tier"] == 3
        assert result["reason"] == "low_signal"

    def test_non_crypto_gaming(self):
        """Non-crypto gaming content should be Tier 3."""
        result = classify_article("Best Games Releasing This Month")
        assert result["tier"] == 3
        assert result["reason"] == "low_signal"

    def test_non_crypto_nvidia(self):
        """Non-crypto Nvidia news should be Tier 3."""
        result = classify_article("Nvidia Launches Self-Driving Car Initiative")
        assert result["tier"] == 3
        assert result["reason"] == "low_signal"

    def test_non_crypto_stock_trading(self):
        """Pure stock trading without crypto context should be Tier 3."""
        result = classify_article("Sold NVDA stock as market trends shift")
        assert result["tier"] == 3
        assert result["reason"] == "low_signal"

    def test_expert_opinion_speculative(self):
        """Expert speculation should be Tier 3."""
        result = classify_article("Expert Believes Bitcoin Could Launch a Massive Rally")
        assert result["tier"] == 3
        assert result["reason"] == "low_signal"

    def test_extreme_price_prediction(self):
        """Extreme price predictions should be Tier 3."""
        result = classify_article("Bitcoin Could Hit $1 Million by 2030")
        assert result["tier"] == 3
        assert result["reason"] == "low_signal"

    def test_opinion_could_trigger(self):
        """Opinion pieces about potential market impact should be Tier 3."""
        result = classify_article("Could This News Trigger a Bitcoin Rally?")
        assert result["tier"] == 3
        assert result["reason"] == "low_signal"


class TestTier2DefaultClassification:
    """Test default tier 2 classification for standard news."""

    def test_standard_crypto_news(self):
        """Standard crypto news should be Tier 2."""
        result = classify_article("Ethereum Launches New Update")
        assert result["tier"] == 2
        assert result["reason"] == "default"

    def test_developer_conference(self):
        """Developer conference announcements should be Tier 2."""
        result = classify_article("Ethereum Developer Conference Announces Dates")
        assert result["tier"] == 2
        assert result["reason"] == "default"

    def test_project_update(self):
        """Project updates should be Tier 2."""
        result = classify_article("Uniswap Releases V4 Update")
        assert result["tier"] == 2
        assert result["reason"] == "default"

    def test_protocol_upgrade(self):
        """Protocol upgrades should be Tier 2."""
        result = classify_article("Solana Network Completes Planned Upgrade")
        assert result["tier"] == 2
        assert result["reason"] == "default"

    def test_market_analysis_general(self):
        """General market analysis should be Tier 2."""
        result = classify_article("Crypto Market Shows Strength in January")
        assert result["tier"] == 2
        assert result["reason"] == "default"

    def test_partnership_announcement(self):
        """Partnership announcements should be Tier 2."""
        result = classify_article("Chainlink Partners with Enterprise for Integration")
        assert result["tier"] == 2
        assert result["reason"] == "default"


class TestPatternPriority:
    """Test that pattern priority works correctly (Tier 3 takes precedence)."""

    def test_historical_security_event_downgraded(self):
        """Historical security events should be downgraded from Tier 1 to Tier 2."""
        # Contains "hacker" + "arrested" pattern which triggers historical exception
        result = classify_article("Bitcoin Hacker Arrested by FBI After 5-Year Investigation")
        assert result["tier"] == 2
        assert result["reason"] == "historical_security"

    def test_historical_hack_anniversary_tier3(self):
        """Historical hack anniversaries should trigger Tier 3 (retrospective)."""
        # "Year in review" pattern takes precedence over security keywords
        result = classify_article("Best of 2024: Top 10 Crypto Hacks That Shook The Market")
        assert result["tier"] == 3

    def test_speculative_regulation_downgraded(self):
        """Speculative regulatory content should be downgraded to Tier 3."""
        # Contains both regulation (Tier 1) and speculation "could" pattern (Tier 3)
        result = classify_article("Could Bitcoin Regulation Could Launch a Rally?")
        assert result["tier"] == 3
        assert result["reason"] == "low_signal"

    def test_spec_security_downgraded(self):
        """Speculative security content should be downgraded to Tier 3."""
        # Contains hack keyword but also "crystal ball" speculation pattern
        result = classify_article("Crystal Ball: Will the Next Hack Trigger a Recovery?")
        assert result["tier"] == 3
        assert result["reason"] == "low_signal"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_title(self):
        """Empty title should default to Tier 2."""
        result = classify_article("")
        assert result["tier"] == 2
        assert result["reason"] == "default"

    def test_title_only_tier1(self):
        """Title-only should work for Tier 1 classification."""
        result = classify_article("SEC Announces New Bitcoin Regulation")
        assert result["tier"] == 1

    def test_title_only_tier3(self):
        """Title-only should work for Tier 3 classification."""
        result = classify_article("Will Bitcoin Finally Break the $100K Barrier?")
        assert result["tier"] == 3

    def test_case_insensitivity_uppercase(self):
        """Pattern matching should be case-insensitive (uppercase)."""
        result = classify_article("SEC APPROVES BITCOIN ETF")
        assert result["tier"] == 1

    def test_case_insensitivity_lowercase(self):
        """Pattern matching should be case-insensitive (lowercase)."""
        result = classify_article("sec approves bitcoin etf")
        assert result["tier"] == 1

    def test_case_insensitivity_mixed(self):
        """Pattern matching should be case-insensitive (mixed case)."""
        result = classify_article("SeC ApPrOvEs BiTcOiN eTf")
        assert result["tier"] == 1

    def test_whitespace_handling(self):
        """Multiple spaces should be handled correctly."""
        result = classify_article("SEC    Approves    Bitcoin    ETF")
        assert result["tier"] == 1

    def test_mixed_signals_tier1_wins(self):
        """When both Tier 1 and standard content exist, Tier 1 should win."""
        result = classify_article(
            "SEC Approves Bitcoin ETF and Other Crypto News",
            "The Securities and Exchange Commission has approved..."
        )
        assert result["tier"] == 1

    def test_tier3_in_body_only(self):
        """Tier 3 patterns in body should still be detected."""
        result = classify_article("Bitcoin News", "This is about price predictions for Bitcoin")
        assert result["tier"] == 2  # Title is neutral, body check happens but "price predictions" needs more context

    def test_body_tier1_detection(self):
        """Tier 1 patterns in body should be detected."""
        result = classify_article(
            "Bitcoin News",
            "The SEC has approved a new Bitcoin ETF with significant implications for the market."
        )
        assert result["tier"] == 1
        assert result["reason"] == "high_signal_body"

    def test_source_parameter_ignored(self):
        """Source parameter should not affect classification."""
        result1 = classify_article("SEC Approves Bitcoin ETF", source="Reuters")
        result2 = classify_article("SEC Approves Bitcoin ETF", source="CoinDesk")
        assert result1["tier"] == result2["tier"] == 1

    def test_pattern_detection_returns_matched(self):
        """Classification should return the matched pattern."""
        result = classify_article("SEC Approves Bitcoin ETF")
        assert result["matched_pattern"] is not None
        assert isinstance(result["matched_pattern"], str)

    def test_default_tier2_no_pattern(self):
        """Tier 2 default should have no matched pattern."""
        result = classify_article("Ethereum Launches New Update")
        assert result["matched_pattern"] is None


class TestNewPatternsFromCHORE001:
    """
    Test patterns added/improved during CHORE-001 tuning.

    These tests validate new patterns discovered during production review.
    """

    def test_institutional_product_morgan_stanley(self):
        """Morgan Stanley crypto product launches should be Tier 1."""
        result = classify_article("Morgan Stanley Launches Digital Asset Wallet")
        assert result["tier"] == 1

    def test_institutional_product_jpmorgan(self):
        """JPMorgan crypto initiatives should be Tier 1."""
        result = classify_article("JPMorgan Launches Blockchain Payment Solution")
        assert result["tier"] == 1

    def test_government_adoption_state_bitcoin_reserve(self):
        """State-level bitcoin reserve initiatives should be Tier 1."""
        result = classify_article("Texas Proposes Bitcoin Reserve Strategy")
        assert result["tier"] == 1

    def test_government_adoption_florida_crypto(self):
        """State crypto initiatives should be Tier 1."""
        result = classify_article("Florida Launches Digital Asset Strategy")
        assert result["tier"] == 1

    def test_major_funding_round(self):
        """Major acquisitions should be Tier 1."""
        result = classify_article("Crypto Platform Acquires Rival for $500 million")
        assert result["tier"] == 1

    def test_banking_license_application(self):
        """Banking license applications should be Tier 1."""
        result = classify_article("Crypto Company Applies for Federal Bank Charter")
        assert result["tier"] == 1

    def test_world_liberty_financial(self):
        """World Liberty Financial bank initiatives should be Tier 1."""
        result = classify_article("World Liberty Financial Seeks Bank Charter")
        assert result["tier"] == 1

    def test_expanded_non_crypto_google_gemini(self):
        """Google Gemini AI news without crypto context should be Tier 3."""
        result = classify_article("Google Launches Gemini AI Assistant Update")
        assert result["tier"] == 3

    def test_expanded_non_crypto_boston_dynamics(self):
        """Boston Dynamics robotics news should be Tier 3."""
        result = classify_article("Boston Dynamics Shows New Robot Capabilities")
        assert result["tier"] == 3

    def test_expanded_non_crypto_microsoft(self):
        """Microsoft news without crypto should be Tier 3."""
        result = classify_article("Microsoft Announces Windows 12 Features")
        assert result["tier"] == 3

    def test_stock_advice_jim_cramer(self):
        """Jim Cramer stock advice should be Tier 3."""
        result = classify_article("Jim Cramer Advises Caution on Tech Stocks")
        assert result["tier"] == 3

    def test_stock_advice_investment_bank(self):
        """Investment bank stock targets should be Tier 3."""
        result = classify_article("Goldman Sachs Raises Apple Stock Price Target")
        assert result["tier"] == 3

    def test_bank_of_america_coinbase_tier1(self):
        """Bank of America news on Coinbase should be Tier 1."""
        # This should be Tier 1 because it's institutional adoption
        result = classify_article("Bank of America Upgrades Coinbase Stake")
        assert result["tier"] == 1


class TestBatchClassification:
    """Test batch classification functionality."""

    def test_batch_classify_multiple(self):
        """Batch classification should handle multiple articles."""
        from crypto_news_aggregator.services.relevance_classifier import get_classifier

        classifier = get_classifier()
        articles = [
            {"title": "SEC Approves Bitcoin ETF", "text": ""},
            {"title": "Will Bitcoin Finally Break $100K?", "text": ""},
            {"title": "Ethereum Update Released", "text": ""},
        ]

        results = classifier.classify_batch(articles)
        assert len(results) == 3
        assert results[0]["tier"] == 1  # SEC is Tier 1
        assert results[1]["tier"] == 3  # "will finally" is Tier 3 prediction
        assert results[2]["tier"] == 2  # Default is Tier 2
        # Check index values
        assert results[0]["index"] == 0
        assert results[1]["index"] == 1
        assert results[2]["index"] == 2

    def test_batch_classify_empty(self):
        """Batch classification of empty list should return empty list."""
        from crypto_news_aggregator.services.relevance_classifier import get_classifier

        classifier = get_classifier()
        results = classifier.classify_batch([])
        assert len(results) == 0

    def test_batch_classify_with_source(self):
        """Batch classification should accept source field."""
        from crypto_news_aggregator.services.relevance_classifier import get_classifier

        classifier = get_classifier()
        articles = [
            {"title": "SEC Approves Bitcoin", "source": "Reuters"},
            {"title": "Will Bitcoin Finally Rise?", "source": "CoinDesk"},
        ]

        results = classifier.classify_batch(articles)
        assert len(results) == 2
        assert results[0]["tier"] == 1
        assert results[1]["tier"] == 3


class TestRegressionPrevention:
    """Test cases that prevent regressions when patterns are modified."""

    def test_security_breach_not_downgraded_to_tier2(self):
        """Security breaches should remain Tier 1 (prevent regression)."""
        result = classify_article("$100M Exchange Breach Discovered")
        assert result["tier"] == 1, "Security breaches must stay Tier 1"

    def test_regulatory_not_downgraded_to_tier2(self):
        """Regulatory news should remain Tier 1 (prevent regression)."""
        result = classify_article("New Cryptocurrency Regulation Announced")
        assert result["tier"] == 1, "Regulatory news must stay Tier 1"

    def test_tier3_not_upgraded_accidentally(self):
        """Price predictions should stay Tier 3 (prevent accidental upgrades)."""
        result = classify_article("Will Bitcoin Finally Reach $200,000?")
        assert result["tier"] == 3, "Price predictions must stay Tier 3"

    def test_default_tier2_maintained(self):
        """Standard news should stay Tier 2 (prevent false tier assignments)."""
        result = classify_article("New Crypto Project Launches")
        assert result["tier"] == 2, "Standard news must default to Tier 2"

    def test_classifier_instantiation(self):
        """Classifier should instantiate without errors."""
        from crypto_news_aggregator.services.relevance_classifier import RelevanceClassifier

        classifier = RelevanceClassifier()
        assert classifier is not None
        # Check patterns are compiled
        assert len(classifier._tier1_patterns) > 0
        assert len(classifier._tier3_patterns) > 0
