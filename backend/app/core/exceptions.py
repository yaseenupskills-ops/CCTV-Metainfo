class AppError(Exception):
    """Base class for application-level errors."""

    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ConflictError(AppError):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, status_code=409)


class ValidationError(AppError):
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, status_code=422)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, status_code=403)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401)


class RateLimitError(AppError):
    def __init__(self, message: str = "Too many requests. Try again later."):
        super().__init__(message, status_code=429)


class StorageError(AppError):
    def __init__(self, message: str = "Storage operation failed", *, status_code: int = 500):
        super().__init__(message, status_code=status_code)


class AnalysisError(AppError):
    def __init__(self, message: str = "Media analysis failed", *, status_code: int = 500):
        super().__init__(message, status_code=status_code)
