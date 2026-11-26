class ServiceError(Exception):
    status = 400

    def __init__(self, message=""):
        super().__init__(message)
        self.message = message


class BadRequest(ServiceError):
    status = 400


class Unauthorized(ServiceError):
    status = 401


class Forbidden(ServiceError):
    status = 403


class NotFound(ServiceError):
    status = 404


class Conflict(ServiceError):
    status = 409


class TooLarge(ServiceError):
    status = 413


class TooManyRequests(ServiceError):
    status = 429


class UpstreamError(ServiceError):
    status = 502


class Unavailable(ServiceError):
    status = 503
