from fastapi import APIRouter

router = APIRouter()

@router.get("/news/latest")
def get_latest_news():
    return {"news": []}  # Placeholder for latest news endpoint
