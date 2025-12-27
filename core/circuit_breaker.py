"""Circuit breaker pattern for preventing cascading failures."""
from __future__ import annotations

import time
from enum import Enum
from typing import Callable, TypeVar, Generic, cast

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit is open, blocking requests
    HALF_OPEN = "half_open"  # Testing if service has recovered


class CircuitBreakerOpen(RuntimeError):
    """Raised when the circuit breaker is open and requests are blocked."""

    def __init__(self, service_name: str):
        super().__init__(f"Circuit breaker is OPEN for {service_name}. Service is unavailable.")
        self.service_name = service_name


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents cascading failures by temporarily blocking requests to a failing service.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests are blocked immediately
    - HALF_OPEN: Testing if service has recovered (allows limited requests)

    Parameters:
    - failure_threshold: Number of failures before opening circuit (default: 5)
    - recovery_timeout: Seconds before attempting to close circuit (default: 60)
    - success_threshold: Number of successes to close circuit from half-open (default: 2)
    """

    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
    ):
        if failure_threshold <= 0:
            raise ValueError("failure_threshold must be positive")
        if recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be positive")
        if success_threshold <= 0:
            raise ValueError("success_threshold must be positive")

        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0.0

    @property
    def state(self) -> CircuitState:
        """Get the current circuit state."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Get the current failure count."""
        return self._failure_count

    @property
    def success_count(self) -> int:
        """Get the current success count (in half-open state)."""
        return self._success_count

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt resetting the circuit."""
        return (
            self._state == CircuitState.OPEN
            and time.time() - self._last_failure_time >= self.recovery_timeout
        )

    def call(self, func: Callable[[], T]) -> T:
        """
        Execute a function through the circuit breaker.

        Args:
            func: The function to execute

        Returns:
            The result of the function call

        Raises:
            CircuitBreakerOpen: If the circuit is open
            Exception: Any exception raised by the function
        """
        # Check if we should attempt recovery
        if self._should_attempt_reset():
            self._state = CircuitState.HALF_OPEN
            self._success_count = 0

        # Block requests if circuit is open
        if self._state == CircuitState.OPEN:
            raise CircuitBreakerOpen(self.service_name)

        # Try to execute the function
        try:
            result = func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self) -> None:
        """Handle a successful request."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                # Service has recovered, close the circuit
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success in closed state
            self._failure_count = 0

    def _on_failure(self) -> None:
        """Handle a failed request."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # Failed during recovery attempt, reopen circuit
            self._state = CircuitState.OPEN
            self._success_count = 0
        elif (
            self._state == CircuitState.CLOSED
            and self._failure_count >= self.failure_threshold
        ):
            # Too many failures, open the circuit
            self._state = CircuitState.OPEN

    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0

    def get_stats(self) -> dict:
        """Get current circuit breaker statistics."""
        return {
            "service_name": self.service_name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "success_threshold": self.success_threshold,
            "last_failure_time": self._last_failure_time if self._last_failure_time > 0 else None,
        }
