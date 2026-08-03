"""

Database package for Iacgenie AI

Provides modular database adapters for different providers

"""

from .db_provider import DatabaseProvider

from .adapters.base import IDatabaseAdapter

from .adapters.postgres_adapter import PostgreSQLAdapter

__all__ = ["DatabaseProvider", "IDatabaseAdapter", "PostgreSQLAdapter"]
