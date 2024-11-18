from _typeshed import Incomplete
from typing import Any, Mapping
from .keep import KeepClient

class ThreadSafeAPIClient:
    keep: KeepClient

def api(version: str | None = None, cache: bool = True, host: str | None = None, token: str | None = None, insecure: bool = False, request_id: str | None = None, timeout: int = ..., *, discoveryServiceUrl: str | None = None, **kwargs: Any) -> ThreadSafeAPIClient: ...
