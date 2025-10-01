"""
Service for calculating price correlations between cryptocurrencies.
"""

import logging
from typing import Optional, Dict, List, Tuple
from functools import lru_cache
import numpy as np
import asyncio

from .price_service import get_price_service

logger = logging.getLogger(__name__)


class CorrelationService:
    """Service to calculate price correlations."""

    def __init__(self):
        self.price_service = get_price_service()

    async def calculate_correlation(
        self, base_coin_id: str, target_coin_ids: List[str], days: int = 90
    ) -> Dict[str, Optional[float]]:
        """
        Calculate the Pearson correlation between a base coin and a list of target coins.

        Args:
            base_coin_id: The CoinGecko ID of the base coin (e.g., 'bitcoin').
            target_coin_ids: A list of CoinGecko IDs for target coins (e.g., ['ethereum', 'solana']).
            days: The number of days of historical data to use for calculation.

        Returns:
            A dictionary mapping each target coin ID to its correlation coefficient with the base coin.
        """
        # Fetch all required historical data concurrently
        all_coin_ids = [base_coin_id] + target_coin_ids
        price_tasks = [
            self.price_service.get_historical_prices(coin_id, days)
            for coin_id in all_coin_ids
        ]
        all_price_data = await asyncio.gather(*price_tasks)

        historical_prices = {
            coin_id: data for coin_id, data in zip(all_coin_ids, all_price_data)
        }

        base_prices_raw = historical_prices.get(base_coin_id)
        if not base_prices_raw:
            logger.warning(
                f"Could not retrieve historical data for base coin {base_coin_id}."
            )
            return {target_id: None for target_id in target_coin_ids}

        # Create a dictionary of dates to prices for the base coin for easy lookup
        base_price_map = {ts.date(): price for ts, price in base_prices_raw}

        correlations = {}
        for target_id in target_coin_ids:
            target_prices_raw = historical_prices.get(target_id)
            if not target_prices_raw:
                correlations[target_id] = None
                continue

            # Align data by date
            aligned_base_prices = []
            aligned_target_prices = []

            for ts, price in target_prices_raw:
                if ts.date() in base_price_map:
                    aligned_base_prices.append(base_price_map[ts.date()])
                    aligned_target_prices.append(price)

            # Ensure we have enough overlapping data points to calculate correlation
            if len(aligned_base_prices) < 2:
                correlations[target_id] = None
                continue

            # Calculate Pearson correlation
            try:
                correlation_matrix = np.corrcoef(
                    aligned_base_prices, aligned_target_prices
                )
                # The correlation coefficient is at [0, 1] (or [1, 0]) in the matrix
                correlation = correlation_matrix[0, 1]
                correlations[target_id] = (
                    correlation if np.isfinite(correlation) else None
                )
            except Exception as e:
                logger.error(
                    f"Could not calculate correlation between {base_coin_id} and {target_id}: {e}"
                )
                correlations[target_id] = None

        return correlations


# Factory function for dependency injection
@lru_cache()
def get_correlation_service() -> CorrelationService:
    return CorrelationService()
