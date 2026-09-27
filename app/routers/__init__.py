import importlib
import pkgutil
from typing import List

from fastapi import APIRouter


def get_routers() -> List[APIRouter]:
    """라우터 모듈을 순회하며 APIRouter 인스턴스를 모읍니다."""
    routers: List[APIRouter] = []
    for module_info in pkgutil.iter_modules(__path__, prefix=f"{__name__}."):
        # __init__ 자체는 스킵
        if module_info.name.endswith(".__init__"):
            continue
        module = importlib.import_module(module_info.name)
        module_router = getattr(module, "router", None)
        if isinstance(module_router, APIRouter):
            routers.append(module_router)
    return routers
