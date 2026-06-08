from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from asterion_api.dependencies import get_privacy_analyzer
from asterion_api.schemas import PrivacyAnalyzeRequest, PrivacyReport
from asterion_api.services.privacy_analyzer import PrivacyAnalyzer

router = APIRouter(prefix="/api/privacy", tags=["privacy"])


@router.post("/analyze", response_model=PrivacyReport)
async def analyze_privacy(
    request: PrivacyAnalyzeRequest,
    analyzer: PrivacyAnalyzer = Depends(get_privacy_analyzer),
) -> PrivacyReport:
    try:
        return analyzer.analyze(**request.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Privacy analysis failed: {exc}")
