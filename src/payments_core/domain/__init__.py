"""Domain layer - Core business logic, entities, and rules.

This layer contains:
- Entities: Objects with identity and lifecycle (e.g., Payment)
- Value Objects: Immutable objects defined by their attributes (e.g., Money, PaymentId)
- Domain Services: Stateless operations on domain objects
- Domain Exceptions: Business rule violations

The domain layer has NO dependencies on external frameworks or infrastructure.
"""
