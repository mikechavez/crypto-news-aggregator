web: gunicorn --pythonpath src -c gunicorn.conf.py crypto_news_aggregator.main:app
worker: python src/crypto_news_aggregator/worker.py
