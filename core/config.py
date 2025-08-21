from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Settings:
	"""Environment-driven configuration for the service."""

	# n8n
	n8n_api_url: str
	n8n_api_key: str
	n8n_version: Optional[str]

	# ops
	log_level: str = "info"
	audit_log_path: Optional[str] = None
	rate_limit_per_minute: int = 60
	max_payload_bytes: int = 1_048_576
	enable_ui: bool = False
	optional_webhook_test_url: Optional[str] = None

	@staticmethod
	def load_from_env() -> "Settings":
		n8n_api_url = os.getenv("N8N_API_URL", "").rstrip("/")
		n8n_api_key = os.getenv("N8N_API_KEY", "")
		n8n_version = os.getenv("N8N_VERSION")

		if not n8n_api_url or not n8n_api_key:
			raise RuntimeError("N8N_API_URL and N8N_API_KEY must be set in environment")

		log_level = os.getenv("LOG_LEVEL", "info")
		audit_log_path = os.getenv("AUDIT_LOG_PATH")
		rate_limit = int(os.getenv("RATE_LIMIT", "60"))
		max_payload = int(os.getenv("MAX_PAYLOAD_BYTES", str(1_048_576)))
		enable_ui = os.getenv("ENABLE_UI", "false").lower() == "true"
		optional_webhook_test_url = os.getenv("OPTIONAL_WEBHOOK_TEST_URL")

		return Settings(
			n8n_api_url=n8n_api_url,
			n8n_api_key=n8n_api_key,
			n8n_version=n8n_version,
			log_level=log_level,
			audit_log_path=audit_log_path,
			rate_limit_per_minute=rate_limit,
			max_payload_bytes=max_payload,
			enable_ui=enable_ui,
			optional_webhook_test_url=optional_webhook_test_url,
		)