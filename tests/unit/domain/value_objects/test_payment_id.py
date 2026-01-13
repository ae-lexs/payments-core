from uuid import UUID

import pytest

from payments_core.domain.value_objects.payment_id import PaymentId


class TestPaymentIdGenerate:
    def test_generate_creates_valid_payment_id(self) -> None:
        payment_id = PaymentId.generate()

        assert isinstance(payment_id, PaymentId)
        assert isinstance(payment_id.value, UUID)

    def test_generate_creates_unique_ids(self) -> None:
        payment_id_1 = PaymentId.generate()
        payment_id_2 = PaymentId.generate()

        assert payment_id_1 != payment_id_2
        assert payment_id_1.value != payment_id_2.value


class TestPaymentIdFromString:
    def test_from_string_parses_valid_uuid(self) -> None:
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"

        payment_id = PaymentId.from_string(uuid_str)

        assert payment_id.value == UUID(uuid_str)

    def test_from_string_parses_uppercase_uuid(self) -> None:
        uuid_str = "550E8400-E29B-41D4-A716-446655440000"

        payment_id = PaymentId.from_string(uuid_str)

        assert payment_id.value == UUID(uuid_str.lower())

    def test_from_string_parses_uuid_without_hyphens(self) -> None:
        uuid_str = "550e8400e29b41d4a716446655440000"

        payment_id = PaymentId.from_string(uuid_str)

        assert payment_id.value == UUID("550e8400-e29b-41d4-a716-446655440000")

    def test_from_string_raises_for_invalid_uuid(self) -> None:
        with pytest.raises(ValueError):
            PaymentId.from_string("not-a-valid-uuid")

    def test_from_string_raises_for_empty_string(self) -> None:
        with pytest.raises(ValueError):
            PaymentId.from_string("")

    def test_from_string_raises_for_too_short_uuid(self) -> None:
        with pytest.raises(ValueError):
            PaymentId.from_string("550e8400-e29b-41d4-a716")


class TestPaymentIdImmutability:
    def test_payment_id_is_frozen(self) -> None:
        payment_id = PaymentId.generate()

        with pytest.raises(AttributeError):
            payment_id.value = UUID("550e8400-e29b-41d4-a716-446655440000")  # type: ignore[misc]


class TestPaymentIdEquality:
    def test_equal_payment_ids_are_equal(self) -> None:
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        payment_id_1 = PaymentId.from_string(uuid_str)
        payment_id_2 = PaymentId.from_string(uuid_str)

        assert payment_id_1 == payment_id_2

    def test_different_payment_ids_are_not_equal(self) -> None:
        payment_id_1 = PaymentId.from_string("550e8400-e29b-41d4-a716-446655440000")
        payment_id_2 = PaymentId.from_string("660e8400-e29b-41d4-a716-446655440000")

        assert payment_id_1 != payment_id_2

    def test_payment_id_not_equal_to_raw_uuid(self) -> None:
        uuid_val = UUID("550e8400-e29b-41d4-a716-446655440000")
        payment_id = PaymentId(value=uuid_val)

        assert payment_id != uuid_val  # type: ignore[comparison-overlap]


class TestPaymentIdHashability:
    def test_payment_id_can_be_used_as_dict_key(self) -> None:
        payment_id = PaymentId.generate()
        data = {payment_id: "test_value"}

        assert data[payment_id] == "test_value"

    def test_equal_payment_ids_have_same_hash(self) -> None:
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        payment_id_1 = PaymentId.from_string(uuid_str)
        payment_id_2 = PaymentId.from_string(uuid_str)

        assert hash(payment_id_1) == hash(payment_id_2)

    def test_payment_id_can_be_added_to_set(self) -> None:
        payment_id_1 = PaymentId.generate()
        payment_id_2 = PaymentId.generate()

        payment_set = {payment_id_1, payment_id_2}

        assert len(payment_set) == 2
        assert payment_id_1 in payment_set
        assert payment_id_2 in payment_set

    def test_duplicate_payment_ids_deduplicated_in_set(self) -> None:
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        payment_id_1 = PaymentId.from_string(uuid_str)
        payment_id_2 = PaymentId.from_string(uuid_str)

        payment_set = {payment_id_1, payment_id_2}

        assert len(payment_set) == 1
