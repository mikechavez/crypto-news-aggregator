"""News source-related API endpoints."""
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

router = APIRouter()

# Temporary models - will be moved to models.py later
class SourceBase(BaseModel):
    """Base source model."""
    name: str
    url: str
    is_active: bool = True

class Source(SourceBase):
    """Source model with ID."""
    id: int
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)

# Temporary data storage - will be replaced with database
sources_db = {}

@router.get("/", response_model=List[Source])
async def list_sources(active_only: bool = True) -> List[Source]:
    """
    List all available news sources.
    """
    sources = list(sources_db.values())
    if active_only:
        sources = [s for s in sources if s.is_active]
    return sources

@router.get("/{source_id}", response_model=Source)
async def get_source(source_id: int) -> Source:
    """Get details about a specific news source."""
    if source_id not in sources_db:
        raise HTTPException(status_code=404, detail="Source not found")
    return sources_db[source_id]
