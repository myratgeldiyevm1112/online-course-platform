from fastapi import HTTPException, status


class AppException(Exception):
    """Base domain exception."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class UserAlreadyExistsError(AppException):
    pass

class UserNotFoundError(AppException):
    pass

class InvalidCredentialsError(AppException):
    pass

class InactiveUserError(AppException):
    pass

class InvalidTokenError(AppException):
    pass


# HTTP exception helpers
def raise_400(detail: str):
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

def raise_401(detail: str = "Unauthorized"):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

def raise_403(detail: str = "Forbidden"):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

def raise_404(detail: str = "Not found"):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)