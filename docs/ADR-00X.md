# ADR-00X: [Title]

<!--
TEMPLATE INSTRUCTIONS (delete this block when creating a new ADR)

Naming: ADR-NNN where NNN is zero-padded sequential number.

Title: Concise, describes the decision (not the problem).
  Good: "Lock Provider Interface and In-Memory Implementation"
  Bad:  "How to Handle Locking"

To create a new ADR:
1. Copy this file to ADR-NNN.md
2. Delete all HTML comments
3. Fill in each section
4. Add entry to README.md ADR table
-->

## Status

<!--
One of:
- Proposed:   Under discussion, not yet approved
- Accepted:   Approved and ready for implementation
- Superseded: Replaced by another ADR (link to replacement)
- Deprecated: No longer recommended (explain why)
-->

Proposed

## Context

<!--
Problem statement and requirements. Answer:
- What problem are we solving?
- What are the constraints?
- What prior ADRs does this build upon?
- Why is this decision needed now?

Keep factual and objective. This section sets up the "why".
-->

[Describe the problem, forces, and constraints.]

## Decision

<!--
Structure as numbered sections (### 1. Title).

Common patterns from existing ADRs:

  ### N. Location / Structure
  Where code lives (application/ports vs infrastructure).

  ### N. Interface Definition
  ABC with docstring contract. Use Python type hints.

  ### N. Why [Pattern/Choice]
  Compare alternatives in a table, explain rejections.

  ### N. Implementation Details
  Concrete code with comments for non-obvious parts.

  ### N. Invariants / Contract
  Explicit rules that must hold.

  ### N. Usage
  How other code consumes this component.

Include:
- Code examples with type hints
- Tables for comparisons
- Rationale for rejected alternatives
- References to related ADRs
-->

### 1. [First Major Decision]

```python
# Code example
```

### 2. [Comparison of Alternatives]

| Option | Pros | Cons |
|--------|------|------|
| A      | ...  | ...  |
| B      | ...  | ...  |

**Chosen**: Option A because [rationale].

### 3. [Implementation]

```python
class Example:
    """Docstring with contract."""
    pass
```

## Consequences

### Positive

- **[Benefit]**: [Explanation]

### Negative

- **[Limitation]**: [Explanation]

### Related ADRs

- [ADR-001](ADR-001.md): [Relationship to this ADR]

### Future Work

- [Deferred decision or known gap]
