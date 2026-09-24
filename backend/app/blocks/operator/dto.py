"""B0-only response/request DTOs for its own routes.

`backend/app/contracts/models.py` is frozen and read-only (AGENTS.md п.2): it does not define
these shapes, so B0 keeps them in its own allowed path instead of touching the shared file.
"""

from typing import Literal

from pydantic import BaseModel

from app.contracts.models import Cluster, Priority, Report


class ClusterOut(Cluster):
    """B0 response; unavailable scoring is explicit, never a fabricated zero."""

    priority: Priority | None = None


class ClusterDetail(ClusterOut):
    reports: list[Report]


class ClusterReview(BaseModel):
    decision: Literal["accept", "reject"]


class OperatorRunRequest(BaseModel):
    trigger: Literal["manual"] = "manual"
