"""Endpoint to list roles that have an ingested knowledge base."""
from fastapi import APIRouter
from typing import List

from app.schemas import RoleInfo
from app.rag.vector_store import get_vector_store

router = APIRouter(prefix="/api/roles", tags=["roles"])


def _display_name(role_slug: str) -> str:
    return role_slug.replace("-", " ").replace("_", " ").title()


@router.get("", response_model=List[RoleInfo])
def list_roles():
    store = get_vector_store()
    roles = store.list_roles()
    return [
        RoleInfo(
            role=role,
            display_name=_display_name(role),
            document_count=store.collection_count(role),
        )
        for role in roles
    ]
