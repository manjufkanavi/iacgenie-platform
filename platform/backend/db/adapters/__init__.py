"""

Database adapters package

Provides implementations for different database providers

"""

from .base import IDatabaseAdapter

from .postgres_adapter import PostgreSQLAdapter

__all__ = ["IDatabaseAdapter", "PostgreSQLAdapter"]
