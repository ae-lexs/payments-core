"""Application layer - Use cases and port definitions.

This layer contains:
- Use Cases: Application-specific business rules and orchestration
- Ports: Abstract interfaces (protocols) for external dependencies
- DTOs: Data transfer objects for use case input/output

The application layer depends only on the domain layer.
Infrastructure implementations are injected via ports.
"""
