from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import List, Optional
from decimal import Decimal
from uuid import UUID

from app.core.supabase import get_supabase_admin_client
from app.models.response import ApiResponse
from app.models.services import (
    ServiceReadBasic,
    ServicePlanReadBasic,
    ServiceReadWithPlans,
    Service,
    ServicePlan,
)
from app.api.deps import get_current_user

router = APIRouter()


def _to_service_basic(row: dict) -> ServiceReadBasic:
    """Convert raw Supabase row to ServiceReadBasic."""
    return ServiceReadBasic.model_validate(row)


def _to_plan_basic(row: dict) -> ServicePlanReadBasic:
    """Convert raw Supabase row to ServicePlanReadBasic."""
    # Ensure Decimal coercion when present
    if row.get("cached_price") is not None and not isinstance(row["cached_price"], Decimal):
        try:
            row["cached_price"] = Decimal(str(row["cached_price"]))
        except Exception:
            pass
    return ServicePlanReadBasic.model_validate(row)


@router.get("/", response_model=List[ServiceReadBasic])
async def search_or_popular_services(
    search: Optional[str] = Query(None, min_length=1),
    user=Depends(get_current_user),
):
    """Servis arama veya popüler liste (korumalı)."""
    try:
        supabase = get_supabase_admin_client()

        # Arama varsa: name/display_name ILIKE veya keywords contains (exact) kombinasyonu
        if search:
            q = search.strip()
            # name/display_name ILIKE
            base_q = (
                supabase.table("services")
                .select("*")
                .or_(f"name.ilike.%{q}%,display_name.ilike.%{q}%")
                .limit(15)
            )
            base_res = base_q.execute()
            rows = base_res.data or []

            # keywords contains exact match (yakınsak destek; ilike array için yok)
            kw_rows: List[dict] = []
            try:
                kw_q = (
                    supabase.table("services")
                    .select("*")
                    .contains("keywords", [q.lower()])
                    .limit(15)
                )
                kw_res = kw_q.execute()
                kw_rows = kw_res.data or []
            except Exception:
                kw_rows = []

            # ID bazında birleştir ve uniq yap
            by_id = {}
            for r in rows + kw_rows:
                by_id[r.get("id")] = r
            uniq_rows = list(by_id.values())
            return [_to_service_basic(r) for r in uniq_rows]

        # Arama yoksa: popüler servisler
        result = (
            supabase.table("services")
            .select("*")
            .eq("is_popular", True)
            .order("display_name")
            .execute()
        )
        rows = result.data or []
        return [_to_service_basic(r) for r in rows]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_ERROR", "message": str(e)},
        )


@router.get("/popular", response_model=ApiResponse)
async def popular_services():
    """Popüler servisleri listele (salt-okunur)."""
    try:
        supabase = get_supabase_admin_client()
        result = supabase.table("services").select("*").eq("is_popular", True).order("display_name").execute()
        rows = result.data or []
        data: List[ServiceReadBasic] = [_to_service_basic(r).model_dump() for r in rows]
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {"code": "INTERNAL_ERROR", "message": str(e)},
            },
        )


@router.get("/search", response_model=ApiResponse)
async def search_services(q: str = Query(..., min_length=1)):
    """Servis arama: name, display_name üzerinde ilike (salt-okunur)."""
    try:
        supabase = get_supabase_admin_client()
        query = (
            supabase.table("services")
            .select("*")
            .or_(f"name.ilike.%{q}%,display_name.ilike.%{q}%")
            .limit(10)
        )
        result = query.execute()
        rows = result.data or []
        data: List[ServiceReadBasic] = [_to_service_basic(r).model_dump() for r in rows]
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {"code": "INTERNAL_ERROR", "message": str(e)},
            },
        )


@router.get("/{service_id}", response_model=ApiResponse)
async def get_service_with_plans(service_id: str):
    """Tek servisi ve ilişkili aktif planlarını getir (salt-okunur)."""
    try:
        supabase = get_supabase_admin_client()
        svc_res = supabase.table("services").select("*").eq("id", service_id).single().execute()
        svc_row = svc_res.data
        if not svc_row:
            return {"success": False, "message": "Service not found", "data": None}

        plans_res = (
            supabase.table("service_plans")
            .select("*")
            .eq("service_id", service_id)
            .eq("is_active", True)
            .order("plan_name")
            .execute()
        )
        plans_rows = plans_res.data or []
        plans: List[ServicePlanReadBasic] = [_to_plan_basic(r).model_dump() for r in plans_rows]

        svc_basic = _to_service_basic(svc_row).model_dump()
        svc_full = {**svc_basic, "service_plans": plans}
        return {"success": True, "data": svc_full}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {"code": "INTERNAL_ERROR", "message": str(e)},
            },
        )


@router.get("/{service_id}/plans", response_model=List[ServicePlanReadBasic])
async def list_service_plans(service_id: UUID, user=Depends(get_current_user)):
    """Bir servisin aktif planlarını listele (korumalı)."""
    try:
        supabase = get_supabase_admin_client()
        result = (
            supabase.table("service_plans")
            .select("*")
            .eq("service_id", str(service_id))
            .eq("is_active", True)
            .order("plan_name")
            .execute()
        )
        rows = result.data or []
        return [_to_plan_basic(r) for r in rows]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_ERROR", "message": str(e)},
        )


@router.get("/plans/{plan_id}", response_model=ApiResponse)
async def get_plan_by_id(plan_id: str):
    """Plan detayını ID ile getir (salt-okunur)."""
    try:
        supabase = get_supabase_admin_client()
        res = supabase.table("service_plans").select("*").eq("id", plan_id).single().execute()
        row = res.data
        if not row:
            return {"success": False, "message": "Plan not found", "data": None}
        data = _to_plan_basic(row).model_dump()
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {"code": "INTERNAL_ERROR", "message": str(e)},
            },
        )


@router.get("/plans/by-identifier/{plan_identifier}", response_model=ApiResponse)
async def get_plans_by_identifier(plan_identifier: str):
    """Planları plan_identifier ile getir (birden fazla serviste olabilir)."""
    try:
        supabase = get_supabase_admin_client()
        result = (
            supabase.table("service_plans")
            .select("*")
            .eq("plan_identifier", plan_identifier)
            .eq("is_active", True)
            .order("created_at", desc=False)
            .execute()
        )
        rows = result.data or []
        data: List[ServicePlanReadBasic] = [_to_plan_basic(r).model_dump() for r in rows]
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": {"code": "INTERNAL_ERROR", "message": str(e)},
            },
        )