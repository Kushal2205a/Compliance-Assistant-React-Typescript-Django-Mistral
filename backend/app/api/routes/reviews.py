from fastapi import APIRouter

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.get("")
def list_reviews():
    return {"reviews": []}
