from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional
from app.models.response import ApiResponse
from app.services.predefined_bill_service import predefined_bill_service

router = APIRouter()

@router.get("/predefined-bills", response_model=ApiResponse)
async def get_all_predefined_bills():
    """Tüm predefined bills listesi (public)"""
    try:
        data = await predefined_bill_service.get_all()
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
        )

@router.get("/predefined-bills/popular", response_model=ApiResponse)
async def get_popular_predefined_bills():
    """Popüler predefined bills (public, cache'li)"""
    try:
        data = await predefined_bill_service.get_popular()
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
        )

@router.get("/predefined-bills/search", response_model=ApiResponse)
async def search_predefined_bills(q: str = Query(..., min_length=1)):
    """Predefined bills arama (public)"""
    try:
        data = await predefined_bill_service.search(q)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
        )