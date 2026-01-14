import pytest

from payments_core.domain.exceptions import InvalidIdempotencyKeyError
from payments_core.domain.value_objects import IdempotencyKey


class TestIdempotencyKeyCreation:
    def test_creates_valid_idempotency_key(self) -> None:
        key = IdempotencyKey(value="request-123")

        assert isinstance(key, IdempotencyKey)
        assert key.value == "request-123"

    def test_creates_key_with_max_length(self) -> None:
        max_length_value = "a" * 64

        key = IdempotencyKey(value=max_length_value)

        assert key.value == max_length_value
        assert len(key.value) == 64

    def test_creates_key_with_all_allowed_characters(self) -> None:
        key = IdempotencyKey(value="aZ09-_:./")

        assert key.value == "aZ09-_:./"


class TestIdempotencyKeyNormalization:
    def test_trims_leading_whitespace(self) -> None:
        key = IdempotencyKey(value="  request-123")

        assert key.value == "request-123"

    def test_trims_trailing_whitespace(self) -> None:
        key = IdempotencyKey(value="request-123  ")

        assert key.value == "request-123"

    def test_trims_both_leading_and_trailing_whitespace(self) -> None:
        key = IdempotencyKey(value="  request-123  ")

        assert key.value == "request-123"

    def test_raises_for_whitespace_only(self) -> None:
        with pytest.raises(InvalidIdempotencyKeyError):
            IdempotencyKey(value="   ")


class TestIdempotencyKeyValidation:
    def test_raises_for_empty_string(self) -> None:
        with pytest.raises(InvalidIdempotencyKeyError):
            IdempotencyKey(value="")

    def test_raises_for_string_exceeding_max_length(self) -> None:
        too_long_value = "a" * 65

        with pytest.raises(InvalidIdempotencyKeyError):
            IdempotencyKey(value=too_long_value)

    def test_raises_for_much_longer_string(self) -> None:
        very_long_value = "a" * 1000

        with pytest.raises(InvalidIdempotencyKeyError):
            IdempotencyKey(value=very_long_value)

    def test_raises_for_space_in_middle(self) -> None:
        with pytest.raises(InvalidIdempotencyKeyError):
            IdempotencyKey(value="request 123")

    def test_raises_for_unicode_characters(self) -> None:
        with pytest.raises(InvalidIdempotencyKeyError):
            IdempotencyKey(value="request-123-é")

    def test_raises_for_emoji(self) -> None:
        with pytest.raises(InvalidIdempotencyKeyError):
            IdempotencyKey(value="request-🔑")

    def test_raises_for_newline(self) -> None:
        with pytest.raises(InvalidIdempotencyKeyError):
            IdempotencyKey(value="request\n123")


class TestIdempotencyKeyImmutability:
    def test_idempotency_key_is_frozen(self) -> None:
        key = IdempotencyKey(value="request-123")

        with pytest.raises(AttributeError):
            key.value = "modified-value"  # type: ignore[misc]


class TestIdempotencyKeyEquality:
    def test_equal_keys_are_equal(self) -> None:
        key_1 = IdempotencyKey(value="request-123")
        key_2 = IdempotencyKey(value="request-123")

        assert key_1 == key_2

    def test_different_keys_are_not_equal(self) -> None:
        key_1 = IdempotencyKey(value="request-123")
        key_2 = IdempotencyKey(value="request-456")

        assert key_1 != key_2

    def test_idempotency_key_not_equal_to_raw_string(self) -> None:
        key = IdempotencyKey(value="request-123")

        assert key != "request-123"  # type: ignore[comparison-overlap]


class TestIdempotencyKeyHashability:
    def test_idempotency_key_can_be_used_as_dict_key(self) -> None:
        key = IdempotencyKey(value="request-123")
        data = {key: "test_value"}

        assert data[key] == "test_value"

    def test_equal_keys_have_same_hash(self) -> None:
        key_1 = IdempotencyKey(value="request-123")
        key_2 = IdempotencyKey(value="request-123")

        assert hash(key_1) == hash(key_2)

    def test_idempotency_key_can_be_added_to_set(self) -> None:
        key_1 = IdempotencyKey(value="request-123")
        key_2 = IdempotencyKey(value="request-456")

        key_set = {key_1, key_2}

        assert len(key_set) == 2
        assert key_1 in key_set
        assert key_2 in key_set

    def test_duplicate_keys_deduplicated_in_set(self) -> None:
        key_1 = IdempotencyKey(value="request-123")
        key_2 = IdempotencyKey(value="request-123")

        key_set = {key_1, key_2}

        assert len(key_set) == 1
