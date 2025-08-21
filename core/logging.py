from __future__ import annotations

import json
import sys
import time
from typing import Any, Dict, Optional

from loguru import logger


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
	logger.bind(audit=True).info(
		json.dumps(
			{
				"event": event,
				"actor": actor,
				"status": status,
				"details": details,
				"timestamp": int(time.time() * 1000),
			}
		)
	)