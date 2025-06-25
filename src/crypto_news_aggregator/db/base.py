from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Export Base explicitly
__all__ = ['Base']