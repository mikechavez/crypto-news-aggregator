"""
Entity normalization service for mapping ticker variants to canonical names.

This service ensures consistent entity naming across the system by:
- Mapping ticker variants (BTC, $BTC, btc) to canonical names (Bitcoin)
- Providing case-insensitive lookups
- Supporting both full names and ticker symbols
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Canonical entity mapping: canonical_name -> list of variants
ENTITY_MAPPING = {
    "Bitcoin": ["BTC", "$BTC", "btc", "bitcoin", "Bitcoin"],
    "Ethereum": ["ETH", "$ETH", "eth", "ethereum", "Ethereum"],
    "Solana": ["SOL", "$SOL", "sol", "solana", "Solana"],
    "Dogecoin": ["DOGE", "$DOGE", "doge", "dogecoin", "Dogecoin"],
    "Litecoin": ["LTC", "$LTC", "ltc", "litecoin", "Litecoin"],
    "Cardano": ["ADA", "$ADA", "ada", "cardano", "Cardano"],
    "Polkadot": ["DOT", "$DOT", "dot", "polkadot", "Polkadot"],
    "Avalanche": ["AVAX", "$AVAX", "avax", "avalanche", "Avalanche"],
    "Chainlink": ["LINK", "$LINK", "link", "chainlink", "Chainlink"],
    "Polygon": ["MATIC", "$MATIC", "matic", "polygon", "Polygon"],
    "Ripple": ["XRP", "$XRP", "xrp", "ripple", "Ripple"],
    "Binance Coin": ["BNB", "$BNB", "bnb", "binance coin", "Binance Coin"],
    "Uniswap": ["UNI", "$UNI", "uni", "uniswap", "Uniswap"],
    "Shiba Inu": ["SHIB", "$SHIB", "shib", "shiba inu", "Shiba Inu"],
    "Tron": ["TRX", "$TRX", "trx", "tron", "Tron"],
    "Cosmos": ["ATOM", "$ATOM", "atom", "cosmos", "Cosmos"],
    "Stellar": ["XLM", "$XLM", "xlm", "stellar", "Stellar"],
    "Monero": ["XMR", "$XMR", "xmr", "monero", "Monero"],
    "EOS": ["EOS", "$EOS", "eos"],
    "Tezos": ["XTZ", "$XTZ", "xtz", "tezos", "Tezos"],
    "Aave": ["AAVE", "$AAVE", "aave", "Aave"],
    "Algorand": ["ALGO", "$ALGO", "algo", "algorand", "Algorand"],
    "VeChain": ["VET", "$VET", "vet", "vechain", "VeChain"],
    "Filecoin": ["FIL", "$FIL", "fil", "filecoin", "Filecoin"],
    "Internet Computer": ["ICP", "$ICP", "icp", "internet computer", "Internet Computer"],
    "The Graph": ["GRT", "$GRT", "grt", "the graph", "The Graph"],
    "Hedera": ["HBAR", "$HBAR", "hbar", "hedera", "Hedera"],
    "Elrond": ["EGLD", "$EGLD", "egld", "elrond", "Elrond"],
    "Theta": ["THETA", "$THETA", "theta", "Theta"],
    "ApeCoin": ["APE", "$APE", "ape", "apecoin", "ApeCoin"],
    "Decentraland": ["MANA", "$MANA", "mana", "decentraland", "Decentraland"],
    "The Sandbox": ["SAND", "$SAND", "sand", "the sandbox", "The Sandbox"],
    "Axie Infinity": ["AXS", "$AXS", "axs", "axie infinity", "Axie Infinity"],
    "Fantom": ["FTM", "$FTM", "ftm", "fantom", "Fantom"],
    "Near Protocol": ["NEAR", "$NEAR", "near", "near protocol", "Near Protocol"],
    "Arbitrum": ["ARB", "$ARB", "arb", "arbitrum", "Arbitrum"],
    "Optimism": ["OP", "$OP", "op", "optimism", "Optimism"],
    "Aptos": ["APT", "$APT", "apt", "aptos", "Aptos"],
    "Sui": ["SUI", "$SUI", "sui", "Sui"],
    "Pepe": ["PEPE", "$PEPE", "pepe", "Pepe"],
    "Injective": ["INJ", "$INJ", "inj", "injective", "Injective"],
    "Stacks": ["STX", "$STX", "stx", "stacks", "Stacks"],
    "Render": ["RNDR", "$RNDR", "rndr", "render", "Render"],
    "Immutable": ["IMX", "$IMX", "imx", "immutable", "Immutable"],
    "Kaspa": ["KAS", "$KAS", "kas", "kaspa", "Kaspa"],
    "Celestia": ["TIA", "$TIA", "tia", "celestia", "Celestia"],
    "Sei": ["SEI", "$SEI", "sei", "Sei"],
    "Lido DAO": ["LDO", "$LDO", "ldo", "lido dao", "Lido DAO", "Lido"],
    "Maker": ["MKR", "$MKR", "mkr", "maker", "Maker", "MakerDAO"],
    "Compound": ["COMP", "$COMP", "comp", "compound", "Compound"],
}

# Build reverse lookup: variant -> canonical_name
_VARIANT_TO_CANONICAL = {}
for canonical, variants in ENTITY_MAPPING.items():
    for variant in variants:
        # Store both original case and lowercase for case-insensitive lookup
        _VARIANT_TO_CANONICAL[variant] = canonical
        _VARIANT_TO_CANONICAL[variant.lower()] = canonical


def normalize_entity_name(entity_name: str) -> str:
    """
    Returns canonical name for any variant.
    
    Args:
        entity_name: The entity name or ticker to normalize
    
    Returns:
        Canonical entity name, or original if unknown
    
    Examples:
        >>> normalize_entity_name("BTC")
        "Bitcoin"
        >>> normalize_entity_name("$btc")
        "Bitcoin"
        >>> normalize_entity_name("ethereum")
        "Ethereum"
        >>> normalize_entity_name("Unknown Token")
        "Unknown Token"
    """
    if not entity_name:
        return entity_name
    
    # Try exact match first
    if entity_name in _VARIANT_TO_CANONICAL:
        canonical = _VARIANT_TO_CANONICAL[entity_name]
        if entity_name != canonical:
            logger.debug(f"Normalized '{entity_name}' -> '{canonical}'")
        return canonical
    
    # Try case-insensitive match
    lower_name = entity_name.lower()
    if lower_name in _VARIANT_TO_CANONICAL:
        canonical = _VARIANT_TO_CANONICAL[lower_name]
        logger.debug(f"Normalized '{entity_name}' -> '{canonical}' (case-insensitive)")
        return canonical
    
    # Return original if no mapping found
    logger.debug(f"No normalization mapping found for '{entity_name}'")
    return entity_name


def get_canonical_names() -> list[str]:
    """
    Returns list of all canonical entity names.
    
    Returns:
        List of canonical entity names
    """
    return list(ENTITY_MAPPING.keys())


def get_variants(canonical_name: str) -> list[str]:
    """
    Returns all variants for a canonical name.
    
    Args:
        canonical_name: The canonical entity name
    
    Returns:
        List of variants, or empty list if not found
    """
    return ENTITY_MAPPING.get(canonical_name, [])


def is_canonical(entity_name: str) -> bool:
    """
    Check if an entity name is already in canonical form.
    
    Args:
        entity_name: The entity name to check
    
    Returns:
        True if the name is canonical, False otherwise
    """
    return entity_name in ENTITY_MAPPING
