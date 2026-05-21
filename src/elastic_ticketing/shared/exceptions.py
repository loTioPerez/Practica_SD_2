class ElasticTicketingError(Exception):
    """Base class for project-specific exceptions."""


class ConfigurationError(ElasticTicketingError):
    """Raised when runtime configuration is missing or malformed."""


class DependencyUnavailableError(ElasticTicketingError):
    """Raised when an optional runtime dependency has not been installed."""


class PersistenceError(ElasticTicketingError):
    """Raised when a persistence adapter cannot satisfy its contract."""
