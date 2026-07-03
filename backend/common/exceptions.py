"""Shared base exceptions for backend services."""


class ServiceError(Exception):
    """Base class for domain service errors."""

    pass


class ExternalAPIError(ServiceError):
    """Raised when an external HTTP dependency fails."""

    pass
