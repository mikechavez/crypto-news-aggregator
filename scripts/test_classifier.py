#!/usr/bin/env python3
"""Test script for relevance classifier."""

import sys
sys.path.insert(0, '/Users/mc/dev-projects/crypto-news-aggregator')

# Import directly from the module file to avoid __init__ issues
import importlib.util
spec = importlib.util.spec_from_file_location(
    "relevance_classifier",
    "/Users/mc/dev-projects/crypto-news-aggregator/src/crypto_news_aggregator/services/relevance_classifier.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

classify_article = module.classify_article

# Test articles - format: (title, expected_tier)
# Tier 1 = high signal, Tier 2 = medium, Tier 3 = low/exclude
test_articles = [
    # Expected HIGH SIGNAL (Tier 1)
    ("Anti-Crypto Commissioner Exits SEC, Signaling Pro-Innovation Shift for Digital Assets", 1),
    ("'Hundreds' of EVM wallets drained in mysterious attack: ZachXBT", 1),
    ("Tether just bought 8,888 Bitcoin, exposing a mechanical profit engine", 1),
    ("Turkmenistan Legalizes Crypto Mining and Exchanges Under Tight State Control", 1),
    ("Bitcoin ETFs lose record $4.57 billion in two months", 1),
    ("Ethereum daily transactions hit all-time high, surpassing 2021 NFT boom", 1),
    ("SEC's Crenshaw set to depart, leaving US financial watchdog all Republican", 1),
    ("$110 billion in crypto left South Korea in 2025", 1),

    # Expected LOW SIGNAL (Tier 3)
    ("Crypto Crystal Ball 2026: Will Ethereum Finally Start Going Parabolic?", 3),
    ("The Biggest Games Releasing in January 2026", 3),
    ("The Most Anticipated Games of 2026", 3),
    ("Why Billionaire Peter Thiel Sold NVDA, TSLA for Apple (AAPL) Stock", 3),
    ("Alphabet 2026 Stock Prediction: Waymo to Send GOOGL Higher?", 3),
    ("Tesla Stock Climbs Despite Q4 Earnings Miss: TSLA Unstoppable?", 3),
    ("Ripple XRP: Could a Revival in Open Interest Launch 50% Rally?", 3),
    ("Can Bitcoin Reclaim $100K by the End of January? 8 AI Chatbots Offer Starkly Different Predictions", 3),
    ("Price predictions 1/2: BTC, ETH, BNB, XRP, SOL, DOGE, ADA, BCH, LINK, ZEC", 3),
    ("How Many Coins Need To Be Burned For Shiba Inu To Hit $0.001?", 3),
    ("XRP Was $0.002 in 2014: What's a $1000 Investment Today?", 3),
    ("Dogecoin Jumps 8.6% in 1 Day: Is It Entering A Recovery Phase?", 3),
    ("13 WTF Moments of the Year: 2025 Crypto Edition", 3),

    # Expected MEDIUM SIGNAL (Tier 2) - standard crypto news
    ("Fedi to Go Open Source on Bitcoin Genesis Anniversary", 2),
    ("Aave Labs moves to ease governance tensions with non-protocol revenue sharing", 2),
    ("BitMine stock up 14% as Tom Lee asks shareholders to approve share increase", 2),
    ("Coinbase Targeting Stablecoin Growth, Onchain Adoption in 2026: Brian Armstrong", 2),
    ("Crypto Markets Move Higher After Holidays, Memecoins Outperform", 2),
    ("The Block Research's Analysts: 2026 Predictions", 2),
    ("PEPE leads memecoin gains amid post-holiday crypto market altcoin rally", 2),
    ("Bitfinex hacker Ilya Lichtenstein credits Trump's First Step Act for early prison release", 2),
    ("Iran accepts cryptocurrency as payment for advanced weapons", 2),
]

print("=" * 80)
print("RELEVANCE CLASSIFIER TEST RESULTS")
print("=" * 80)

correct = 0
incorrect = []

for title, expected_tier in test_articles:
    result = classify_article(title)
    tier = result["tier"]

    is_correct = tier == expected_tier
    if is_correct:
        correct += 1
    else:
        incorrect.append((title, expected_tier, tier, result["reason"], result["matched_pattern"]))

    tier_label = {1: "HIGH", 2: "MED ", 3: "LOW "}[tier]
    status = "✓" if is_correct else "✗"
    display = f"{title[:60]}..." if len(title) > 60 else title
    print(f"{status} [{tier_label}] {display}")

    if not is_correct:
        print(f"   Expected: Tier {expected_tier}, Got: Tier {tier} ({result['reason']})")
        if result["matched_pattern"]:
            print(f"   Pattern: {result['matched_pattern'][:50]}")

print()
print("=" * 80)
print(f"ACCURACY: {correct}/{len(test_articles)} ({100*correct/len(test_articles):.1f}%)")
print("=" * 80)

if incorrect:
    print()
    print("MISCLASSIFIED:")
    for title, expected, got, reason, pattern in incorrect:
        exp_label = {1: "HIGH", 2: "MED", 3: "LOW"}[expected]
        got_label = {1: "HIGH", 2: "MED", 3: "LOW"}[got]
        print(f"  [{exp_label}->{got_label}] {title[:55]}...")
