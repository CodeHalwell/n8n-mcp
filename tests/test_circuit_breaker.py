"""Test circuit breaker functionality."""
import pytest
import time
from core.circuit_breaker import CircuitBreaker, CircuitBreakerOpen, CircuitState


def test_circuit_breaker_starts_closed():
    """Test that circuit breaker starts in CLOSED state."""
    cb = CircuitBreaker("test-service")
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_circuit_breaker_allows_success():
    """Test that successful calls keep circuit closed."""
    cb = CircuitBreaker("test-service", failure_threshold=3)

    # Make successful calls
    for _ in range(10):
        result = cb.call(lambda: "success")
        assert result == "success"

    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_circuit_breaker_opens_after_failures():
    """Test that circuit opens after reaching failure threshold."""
    cb = CircuitBreaker("test-service", failure_threshold=3)

    # Make 3 failing calls
    for i in range(3):
        try:
            cb.call(lambda: 1 / 0)  # Raises ZeroDivisionError
        except ZeroDivisionError:
            pass

    # Circuit should now be OPEN
    assert cb.state == CircuitState.OPEN
    assert cb.failure_count == 3


def test_circuit_breaker_blocks_when_open():
    """Test that circuit breaker blocks requests when open."""
    cb = CircuitBreaker("test-service", failure_threshold=2)

    # Make 2 failing calls to open circuit
    for _ in range(2):
        try:
            cb.call(lambda: 1 / 0)
        except ZeroDivisionError:
            pass

    assert cb.state == CircuitState.OPEN

    # Next call should be blocked with CircuitBreakerOpen
    with pytest.raises(CircuitBreakerOpen) as exc_info:
        cb.call(lambda: "should not execute")

    assert "test-service" in str(exc_info.value)


def test_circuit_breaker_half_open_after_timeout():
    """Test that circuit enters HALF_OPEN state after recovery timeout."""
    cb = CircuitBreaker(
        "test-service",
        failure_threshold=2,
        recovery_timeout=0.1,  # 100ms
    )

    # Open the circuit
    for _ in range(2):
        try:
            cb.call(lambda: 1 / 0)
        except ZeroDivisionError:
            pass

    assert cb.state == CircuitState.OPEN

    # Wait for recovery timeout
    time.sleep(0.15)

    # Next successful call should transition to HALF_OPEN
    result = cb.call(lambda: "success")
    assert result == "success"
    assert cb.state == CircuitState.HALF_OPEN


def test_circuit_breaker_closes_after_success_threshold():
    """Test that circuit closes after reaching success threshold in HALF_OPEN."""
    cb = CircuitBreaker(
        "test-service",
        failure_threshold=2,
        recovery_timeout=0.1,
        success_threshold=2,
    )

    # Open the circuit
    for _ in range(2):
        try:
            cb.call(lambda: 1 / 0)
        except ZeroDivisionError:
            pass

    assert cb.state == CircuitState.OPEN

    # Wait for recovery timeout
    time.sleep(0.15)

    # Make 2 successful calls (success_threshold)
    for _ in range(2):
        cb.call(lambda: "success")

    # Circuit should be CLOSED now
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_circuit_breaker_reopens_on_half_open_failure():
    """Test that circuit reopens if a call fails in HALF_OPEN state."""
    cb = CircuitBreaker(
        "test-service",
        failure_threshold=2,
        recovery_timeout=0.1,
    )

    # Open the circuit
    for _ in range(2):
        try:
            cb.call(lambda: 1 / 0)
        except ZeroDivisionError:
            pass

    assert cb.state == CircuitState.OPEN

    # Wait for recovery timeout
    time.sleep(0.15)

    # Make one successful call to enter HALF_OPEN
    cb.call(lambda: "success")
    assert cb.state == CircuitState.HALF_OPEN

    # Fail the next call
    try:
        cb.call(lambda: 1 / 0)
    except ZeroDivisionError:
        pass

    # Circuit should be OPEN again
    assert cb.state == CircuitState.OPEN


def test_circuit_breaker_reset():
    """Test manual reset of circuit breaker."""
    cb = CircuitBreaker("test-service", failure_threshold=2)

    # Open the circuit
    for _ in range(2):
        try:
            cb.call(lambda: 1 / 0)
        except ZeroDivisionError:
            pass

    assert cb.state == CircuitState.OPEN

    # Reset the circuit
    cb.reset()

    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0
    assert cb.success_count == 0


def test_circuit_breaker_get_stats():
    """Test circuit breaker statistics reporting."""
    cb = CircuitBreaker(
        "my-service",
        failure_threshold=5,
        recovery_timeout=60.0,
        success_threshold=3,
    )

    stats = cb.get_stats()

    assert stats["service_name"] == "my-service"
    assert stats["state"] == "closed"
    assert stats["failure_count"] == 0
    assert stats["success_count"] == 0
    assert stats["failure_threshold"] == 5
    assert stats["recovery_timeout"] == 60.0
    assert stats["success_threshold"] == 3
    assert stats["last_failure_time"] is None


def test_circuit_breaker_invalid_config():
    """Test that invalid configuration raises errors."""
    with pytest.raises(ValueError, match="failure_threshold must be positive"):
        CircuitBreaker("test", failure_threshold=0)

    with pytest.raises(ValueError, match="recovery_timeout must be positive"):
        CircuitBreaker("test", recovery_timeout=0)

    with pytest.raises(ValueError, match="success_threshold must be positive"):
        CircuitBreaker("test", success_threshold=0)
