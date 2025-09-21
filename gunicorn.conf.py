"""Gunicorn configuration file."""

import os
import multiprocessing

# Gunicorn config variables
loglevel = os.environ.get("LOG_LEVEL", "info")

# Use WEB_CONCURRENCY if set, otherwise calculate based on CPU cores
workers = int(os.environ.get("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))

# The address to bind to
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Use the Uvicorn worker class
worker_class = "uvicorn.workers.UvicornWorker"

# Preload the application before starting the workers
preload_app = True

# Set a timeout for workers
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))

# Set a graceful timeout for workers to finish requests
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", 120))

# For debugging purposes, print the configuration
print("--- Gunicorn Configuration ---")
print(f"Log level: {loglevel}")
print(f"Workers: {workers}")
print(f"Bind: {bind}")
print(f"Timeout: {timeout}")
print(f"Preload App: {preload_app}")
print("----------------------------")
