from fastapi import status

def response_message(message: str = "Success", data: dict = None, code: int = status.HTTP_200_OK):
    return {
        "status": code,
        "message": message,
        "data": data
    }
def error_message(message: str = "Success", data: dict | None = None, code: int = status.HTTP_200_OK, error: bool = False):
    return {
        "status": code,
        "error": error,
        "message": message,
        "data": data
    }