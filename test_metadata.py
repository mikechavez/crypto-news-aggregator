#!/usr/bin/env python3
import sys
import os

# Add the src directory to Python path for src layout
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, "src")
sys.path.insert(0, src_path)

print("\nTesting model registration...")
print(f"Project root: {project_root}")
print(f"Src path: {src_path}")
print(f"Src path exists: {os.path.exists(src_path)}")

try:
    from crypto_news_aggregator.db import Base, Source, Article, Sentiment, Trend

    print("✓ Base and models imported successfully")

    print("\n\nRegistered Tables:")
    for table_name, table in Base.metadata.tables.items():
        print(f"\nTable: {table_name}")
        print("Columns:")
        for column in table.columns:
            print(f"  {column.name}: {column.type}")

    print("\n\nModel Classes:")
    model_classes = [Source, Article, Sentiment, Trend]
    for model in model_classes:
        print(f"\nModel: {model.__name__}")
        print(f"Table: {model.__table__.name}")
        print("Columns:")
        for column in model.__table__.columns:
            print(f"  {column.name}: {column.type}")

    print("\n\nBase.metadata.tables:")
    print(Base.metadata.tables)

except Exception as e:
    print(f"✗ Failed to import Base or models: {e}")

    # Debug the import issue
    try:
        import crypto_news_aggregator

        print("✓ Main package found")
        print(f"Package location: {crypto_news_aggregator.__file__}")
    except Exception as e2:
        print(f"✗ Main package not found: {e2}")

    try:
        import crypto_news_aggregator.db

        print("✓ DB package found")
    except Exception as e3:
        print(f"✗ DB package not found: {e3}")

    exit(1)

try:
    from crypto_news_aggregator.db import Source, Article, Sentiment, Trend

    print("✓ Models imported successfully")
except Exception as e:
    print(f"✗ Failed to import models: {e}")
    exit(1)

print(f"\nBase: {Base}")
print(f"Base.metadata: {Base.metadata}")
print(f"Tables in metadata: {list(Base.metadata.tables.keys())}")

if not Base.metadata.tables:
    print("ERROR: No tables found in metadata!")
    print("This means models aren't being registered properly.")
else:
    print("✓ Models registered successfully!")

    for table_name, table in Base.metadata.tables.items():
        print(f"\n{table_name}:")
        for col in table.columns:
            print(f"  - {col.name}: {col.type}")
