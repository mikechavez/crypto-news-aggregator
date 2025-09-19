web: gunicorn --pythonpath src -w 2 -k uvicorn.workers.UvicornWorker crypto_news_aggregator.main:app --bind 0.0.0.0:$PORT
worker: python src/crypto_news_aggregator/worker.py
