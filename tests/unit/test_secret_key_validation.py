"""Unit tests for JWT SECRET_KEY fail-fast validation (security P0 #3)."""
import pytest

from api.auth import validate_secret_key, MIN_SECRET_KEY_LENGTH


@pytest.mark.parametrize(
    "bad_secret",
    [
        None,
        "",
        "change-me-in-production",
        "change-me-in-production-use-long-random-string",  # the .env.example default
        "short",
        "x" * (MIN_SECRET_KEY_LENGTH - 1),
    ],
)
def test_weak_or_default_secret_is_rejected(bad_secret):
    with pytest.raises(RuntimeError):
        validate_secret_key(bad_secret)


def test_strong_secret_is_accepted():
    # A 48-char random-looking key passes.
    validate_secret_key("k" + "9aZ" * 16)


def test_exactly_min_length_is_accepted():
    validate_secret_key("a" * MIN_SECRET_KEY_LENGTH)
