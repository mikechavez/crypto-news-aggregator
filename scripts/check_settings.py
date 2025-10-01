import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from crypto_news_aggregator.core.config import Settings

s = Settings()
print("MONGODB_URI:", getattr(s, "MONGODB_URI", None))
print("All fields:", s.model_dump())
