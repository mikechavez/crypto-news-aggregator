from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import event

# Create the base declarative class
Base = declarative_base()

# Export Base explicitly
__all__ = ['Base']