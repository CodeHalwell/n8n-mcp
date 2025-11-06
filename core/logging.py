from __future__ import annotations

import copy
import json
import sys
import time
from typing import Any, Dict, Optional

from loguru import logger


# Sensitive field names to redact in audit logs
SENSITIVE_FIELDS = {
	"password",
	"api_key",
	"apiKey",
	"secret",
	"token",
	"accessToken",
	"refreshToken",
	"privateKey",
	"clientSecret",
	"data",  # Credential data field
	"nodesAccess",  # May contain sensitive info
}


def _sanitize_dict(obj: Any, depth: int = 0) -> Any:
	"""
	Recursively sanitize a dictionary by redacting sensitive fields.

	Args:
		obj: The object to sanitize (dict, list, or primitive)
		depth: Current recursion depth (prevents infinite recursion)

	Returns:
		A sanitized copy of the object
	"""
	# Prevent excessive recursion
	if depth > 10:
		return "[MAX_DEPTH_EXCEEDED]"

	if isinstance(obj, dict):
		sanitized = {}
		for key, value in obj.items():
			if key in SENSITIVE_FIELDS:
				sanitized[key] = "[REDACTED]"
			else:
				sanitized[key] = _sanitize_dict(value, depth + 1)
		return sanitized
	elif isinstance(obj, list):
		return [_sanitize_dict(item, depth + 1) for item in obj]
	else:
		return obj


def configure_logging(level: str = "info", audit_log_path: Optional[str] = None) -> None:
	logger.remove()
	logger.add(sys.stdout, level=level.upper(), serialize=True, enqueue=True)
	if audit_log_path:
		# Separate sink for audit logs; filter by "audit" record flag
		logger.add(
			audit_log_path,
			level=level.upper(),
			serialize=True,
			enqueue=True,
			filter=lambda record: record["extra"].get("audit", False),
		)


def audit_log(event: str, actor: str, details: Dict[str, Any], status: str = "ok") -> None:
	"""
	Log an audit event with sensitive data redacted.

	Args:
		event: The event name (e.g., "create_credential")
		actor: The actor performing the action (e.g., "mcp")
		details: Event details (will be sanitized before logging)
		status: Status of the operation (default: "ok")
	"""
	# Sanitize details to prevent logging sensitive data
	sanitized_details = _sanitize_dict(copy.deepcopy(details))

	logger.bind(audit=True).info(
		json.dumps(
			{
				"event": event,
				"actor": actor,
				"status": status,
				"details": sanitized_details,
				"timestamp": int(time.time() * 1000),
			}
		)
	)