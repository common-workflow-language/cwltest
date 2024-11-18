from _typeshed import Incomplete
import apiclient.errors

class ApiError(apiclient.errors.HttpError):
    def _get_reason(self) -> str: ...
