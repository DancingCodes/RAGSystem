from ..data.schemas import ApiResponse


def ok(data=None, msg: str = "ok") -> dict:
    return ApiResponse(code=200, data=data, msg=msg).model_dump()


def fail(msg: str, code: int = 500) -> dict:
    return ApiResponse(code=code, data=None, msg=msg).model_dump()
