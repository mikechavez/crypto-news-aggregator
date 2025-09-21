web: gunicorn --pythonpath src --preload -w 1 -k uvicorn.workers.UvicornWorker crypto_news_aggregator.main:app --bind 0.0.0.0:$PORT --timeout 120
worker: python src/crypto_news_aggregator/worker.py
