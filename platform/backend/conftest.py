"""Root conftest - shared mocks for all tests."""

import sys

from unittest.mock import MagicMock

# Mock problematic opentelemetry modules to avoid version mismatch import errors

sys.modules["opentelemetry.exporter.otlp.proto.grpc.trace_exporter"] = MagicMock()

sys.modules["opentelemetry.exporter.otlp.proto.grpc.exporter"] = MagicMock()
