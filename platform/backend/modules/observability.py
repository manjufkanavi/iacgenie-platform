"""Backward-compat stub: modules.observability re-exports from observability/ package."""
from observability.audit_logger import AuditLogger

log_info = AuditLogger().log_event
log_error = AuditLogger().log_error
