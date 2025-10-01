import os
import sys

# Add the 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from crypto_news_aggregator.main import app

# The app object is now exposed for a WSGI server like uvicorn
