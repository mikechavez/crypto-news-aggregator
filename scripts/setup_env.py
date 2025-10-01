"""
Script to help set up the .env file with required environment variables.
This will create or update the .env file in the project root.
"""

import os
import sys
from pathlib import Path


def setup_env():
    """Set up the .env file with required environment variables."""
    env_path = Path(__file__).parent.parent / ".env"

    # Check if .env exists
    if env_path.exists():
        print("Found existing .env file. Current contents:")
        print("-" * 50)
        with open(env_path, "r") as f:
            print(f.read())
        print("-" * 50)

        response = (
            input("\nDo you want to update the existing .env file? (y/n): ")
            .strip()
            .lower()
        )
        if response != "y":
            print("Aborting .env setup.")
            return

    # Get required values
    print("\n=== Setting Up Environment Variables ===")
    print(
        "Enter your Upstash Redis credentials (press Enter to keep existing values):\n"
    )

    # Get or update Redis URL with working defaults
    current_redis_url = os.getenv(
        "UPSTASH_REDIS_REST_URL", "https://grown-oarfish-27991.upstash.io"
    )
    redis_url = input(
        f"\n=== Redis Configuration ===\nUpstash Redis REST URL [{current_redis_url}]: "
    ).strip()
    redis_url = redis_url if redis_url else current_redis_url

    # Get or update Redis token with working defaults
    current_redis_token = os.getenv(
        "UPSTASH_REDIS_TOKEN",
        "AW1XAAIjcDExYTU4YWM2OGRkNzg0OThhYTkyM2YxNDhkOGM1ZmM2OXAxMA",
    )
    redis_token = input("Upstash Redis Token [***]: ").strip()
    redis_token = redis_token if redis_token else current_redis_token

    # MongoDB configuration
    print("\n=== MongoDB Configuration ===")
    current_mongodb_uri = os.getenv("MONGODB_URI", "")
    mongodb_uri = input(
        f"MongoDB Connection URI (e.g., mongodb+srv://<username>:<password>@<cluster>.mongodb.net/) [{current_mongodb_uri}]: "
    ).strip()
    mongodb_uri = mongodb_uri if mongodb_uri else current_mongodb_uri

    current_mongodb_name = os.getenv("MONGODB_NAME", "crypto_news")
    mongodb_name = input(f"MongoDB Database Name [{current_mongodb_name}]: ").strip()
    mongodb_name = mongodb_name if mongodb_name else current_mongodb_name

    # Prepare environment variables
    env_vars = []

    # Add Redis variables
    if redis_url:
        env_vars.append(f'UPSTASH_REDIS_REST_URL="{redis_url}"')
    if redis_token:
        env_vars.append(f'UPSTASH_REDIS_TOKEN="{redis_token}"')

    # Add MongoDB variables
    if mongodb_uri:
        env_vars.append(f'MONGODB_URI="{mongodb_uri}"')
    if mongodb_name:
        env_vars.append(f'MONGODB_NAME="{mongodb_name}"')

    # Write to .env file
    with open(env_path, "w") as f:
        f.write("\n".join(env_vars) + "\n")

    print(
        f"\n✅ .env file has been {'updated' if env_path.exists() else 'created'} at {env_path}"
    )
    print("\nCurrent .env contents:")
    print("-" * 50)
    with open(env_path, "r") as f:
        print(f.read())
    print("-" * 50)
    print("\nEnvironment setup complete!")


if __name__ == "__main__":
    setup_env()
