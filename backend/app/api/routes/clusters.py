"""Роуты блока B0. Контракт: docs/contracts/B0_*.md."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user, require_roles
from app.blocks import operator
from app.contracts.models import ClusterDetail, ClusterOut, ClusterReview

router = APIRouter(
    prefix="/clusters", tags=["clusters"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=list[ClusterOut])
def read_clusters(
    _sort: Annotated[Literal["priority"], Query(alias="sort")] = "priority",
    category: str | None = None,
    min_score: Annotated[float | None, Query(ge=0, le=100)] = None,
) -> list[ClusterOut]:
    try:
        return operator.get_clusters(category, min_score)
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=503, detail="Operator dependencies are not ready"
        ) from exc


@router.get("/{cluster_id}", response_model=ClusterDetail)
def read_cluster(cluster_id: str) -> ClusterDetail:
    try:
        row = operator.get_cluster(cluster_id)
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=503, detail="Operator dependencies are not ready"
        ) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return row


@router.post(
    "/{cluster_id}/review",
    response_model=ClusterDetail,
    dependencies=[Depends(require_roles("supervisor"))],
)
def review_cluster(cluster_id: str, body: ClusterReview) -> ClusterDetail:
    try:
        row = operator.review_cluster(cluster_id, body.decision)
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=503, detail="Operator dependencies are not ready"
        ) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return row
