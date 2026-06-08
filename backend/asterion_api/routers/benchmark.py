from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from asterion_api.dependencies import get_benchmark_service
from asterion_api.schemas import BenchmarkResponse, BenchmarkRunRequest
from asterion_api.services.benchmark_service import BenchmarkService

router = APIRouter(prefix="/api/benchmark", tags=["benchmark"])


@router.post("/run", response_model=BenchmarkResponse)
async def run_benchmark(
    request: BenchmarkRunRequest,
    service: BenchmarkService = Depends(get_benchmark_service),
) -> BenchmarkResponse:
    if request.runs_per_model < 1 or request.runs_per_model > 10:
        raise HTTPException(status_code=400, detail="runs_per_model must be 1-10")
    if request.max_tokens < 8 or request.max_tokens > 512:
        raise HTTPException(status_code=400, detail="max_tokens must be 8-512")

    results = await service.run(
        models=request.models or [],
        prompt=request.prompt,
        max_tokens=request.max_tokens,
        runs_per_model=request.runs_per_model,
    )
    return BenchmarkResponse(
        results=results,
        benchmark_prompt=request.prompt,
        runs_per_model=request.runs_per_model,
    )


@router.get("/cache")
async def get_cache(
    service: BenchmarkService = Depends(get_benchmark_service),
) -> dict[str, object]:
    return {"cached_models": service.get_state()["cached_models"],
            "cache_entries": service.get_state()["cache_entries"]}


@router.delete("/cache")
async def clear_cache(
    service: BenchmarkService = Depends(get_benchmark_service),
) -> dict[str, bool]:
    service.clear_cache()
    return {"cleared": True}


@router.get("/model/{model_name}")
async def get_model_cached_result(
    model_name: str,
    service: BenchmarkService = Depends(get_benchmark_service),
) -> dict[str, object]:
    cached = service.get_cached(model_name)
    if cached is None:
        raise HTTPException(status_code=404, detail="No cached benchmark for this model")
    return cached
