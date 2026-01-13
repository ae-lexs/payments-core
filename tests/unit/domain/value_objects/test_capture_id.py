from uuid import UUID

import pytest

from payments_core.domain.value_objects.capture_id import CaptureId


class TestCaptureIdGenerate:
    def test_generate_creates_valid_capture_id(self) -> None:
        capture_id = CaptureId.generate()

        assert isinstance(capture_id, CaptureId)
        assert isinstance(capture_id.value, UUID)

    def test_generate_creates_unique_ids(self) -> None:
        capture_id_1 = CaptureId.generate()
        capture_id_2 = CaptureId.generate()
        assert capture_id_1 != capture_id_2
        assert capture_id_1.value != capture_id_2.value


class TestCaptureIdFromString:
    def test_from_string_parses_valid_uuid(self) -> None:
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"

        capture_id = CaptureId.from_string(uuid_str)

        assert capture_id.value == UUID(uuid_str)

    def test_from_string_parses_uppercase_uuid(self) -> None:
        uuid_str = "550E8400-E29B-41D4-A716-446655440000"

        capture_id = CaptureId.from_string(uuid_str)

        assert capture_id.value == UUID(uuid_str.lower())

    def test_from_string_parses_uuid_without_hyphens(self) -> None:
        uuid_str = "550e8400e29b41d4a716446655440000"

        capture_id = CaptureId.from_string(uuid_str)

        assert capture_id.value == UUID("550e8400-e29b-41d4-a716-446655440000")

    def test_from_string_raises_for_invalid_uuid(self) -> None:
        with pytest.raises(ValueError):
            CaptureId.from_string("not-a-valid-uuid")

    def test_from_string_raises_for_empty_string(self) -> None:
        with pytest.raises(ValueError):
            CaptureId.from_string("")

    def test_from_string_raises_for_too_short_uuid(self) -> None:
        with pytest.raises(ValueError):
            CaptureId.from_string("550e8400-e29b-41d4-a716")


class TestCaptureIdImmutability:
    def test_capture_id_is_frozen(self) -> None:
        capture_id = CaptureId.generate()

        with pytest.raises(AttributeError):
            capture_id.value = UUID("550e8400-e29b-41d4-a716-446655440000")  # type: ignore[misc]


class TestCaptureIdEquality:
    def test_equal_capture_ids_are_equal(self) -> None:
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        capture_id_1 = CaptureId.from_string(uuid_str)
        capture_id_2 = CaptureId.from_string(uuid_str)
        assert capture_id_1 == capture_id_2

    def test_different_capture_ids_are_not_equal(self) -> None:
        capture_id_1 = CaptureId.from_string("550e8400-e29b-41d4-a716-446655440000")
        capture_id_2 = CaptureId.from_string("660e8400-e29b-41d4-a716-446655440000")

        assert capture_id_1 != capture_id_2

    def test_capture_id_not_equal_to_raw_uuid(self) -> None:
        uuid_val = UUID("550e8400-e29b-41d4-a716-446655440000")
        capture_id = CaptureId(value=uuid_val)

        assert capture_id != uuid_val  # type: ignore[comparison-overlap]


class TestCaptureIdHashability:
    def test_capture_id_can_be_used_as_dict_key(self) -> None:
        capture_id = CaptureId.generate()
        data = {capture_id: "test_value"}

        assert data[capture_id] == "test_value"

    def test_equal_capture_ids_have_same_hash(self) -> None:
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        capture_id_1 = CaptureId.from_string(uuid_str)
        capture_id_2 = CaptureId.from_string(uuid_str)

        assert hash(capture_id_1) == hash(capture_id_2)

    def test_capture_id_can_be_added_to_set(self) -> None:
        capture_id_1 = CaptureId.generate()
        capture_id_2 = CaptureId.generate()

        capture_set = {capture_id_1, capture_id_2}

        assert len(capture_set) == 2
        assert capture_id_1 in capture_set
        assert capture_id_2 in capture_set

    def test_duplicate_capture_ids_deduplicated_in_set(self) -> None:
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        capture_id_1 = CaptureId.from_string(uuid_str)
        capture_id_2 = CaptureId.from_string(uuid_str)

        capture_set = {capture_id_1, capture_id_2}

        assert len(capture_set) == 1
