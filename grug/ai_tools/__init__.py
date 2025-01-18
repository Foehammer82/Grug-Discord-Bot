import importlib
import inspect
import pkgutil

from langchain_core.tools import StructuredTool

from grug.settings import settings

all_ai_tools: list[StructuredTool] = []

if settings.ai_enable_duckduckgo_search:
    from langchain_community.tools import DuckDuckGoSearchResults

    all_ai_tools.append(DuckDuckGoSearchResults())

_package_name = "grug.ai_tools"
for _, module_name, _ in pkgutil.iter_modules(importlib.import_module(_package_name).__path__):  # type: ignore
    for name, obj in inspect.getmembers(importlib.import_module(f"{_package_name}.{module_name}")):
        if isinstance(obj, StructuredTool):
            all_ai_tools.append(obj)

__all__ = ["all_ai_tools"]
