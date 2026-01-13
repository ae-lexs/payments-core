"""Infrastructure layer - Concrete implementations of ports.

This layer contains:
- Persistence: Database repositories and ORM models
- External Services: Implementations of external service ports
- Time Provider: Clock abstraction for testability
- Locking: Distributed locking mechanisms

Infrastructure adapters implement the ports defined in the application layer.
"""
