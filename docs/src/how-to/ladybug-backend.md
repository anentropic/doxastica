---
title: How to Use the LadybugDB Backend
description: Install the ladybug extra and run a doxastica core on durable LadybugDB graph storage, on disk or in memory.
---

# How to Use the LadybugDB Backend

This guide shows you how to run [`MemoryCore`](../reference/doxastica/core.md#doxastica.core.MemoryCore) on the LadybugDB reference backend instead of the zero-dependency in-memory one, so your belief store is durable and graph-native.

The AGM semantics are identical across backends. Switching is a one-line change to how you build the backend.

## Requirements

- doxastica installed **with the ladybug extra**:

    ```bash
    pip install "doxastica[ladybug]"
    ```

    The base `pip install doxastica` does **not** include LadybugDB. The extra pulls in the `ladybug` package (a Kùzu fork, imported as `ladybug`).

- Familiarity with constructing a `MemoryCore` via dependency injection. See [Your First Belief Store](../tutorials/first-belief-store.md).

## Open a file-backed or in-memory backend

[`LadybugBackend`](../reference/doxastica/backends/ladybug.md#doxastica.backends.ladybug.LadybugBackend) lives in `doxastica.backends.ladybug` and is **not** re-exported from the package root. Import it explicitly:

```python
from uuid import uuid7

from doxastica import BeliefFilter, MemoryCore
from doxastica.backends.ladybug import LadybugBackend  # (1)!

backend = LadybugBackend.open("beliefs.db")  # (2)!
```

1. Always import `LadybugBackend` from its module; it is deliberately not on the package root.
2. `open` constructs and **owns** its own connection; `close()` will close it.

The argument to [`open`](../reference/doxastica/backends/ladybug.md#doxastica.backends.ladybug.LadybugBackend.open) is the database path. Pass `":memory:"` (or `""`) for a transient in-memory LadybugDB instead of a file:

=== "On disk"

    ```python
    backend = LadybugBackend.open("beliefs.db")
    ```

=== "In memory"

    ```python
    backend = LadybugBackend.open(":memory:")
    ```

`open` accepts an optional `namespace` keyword (default `"dx"`). The namespace prefixes the backend's tables so it can coexist with other tenants in a shared database; you only need it when leasing a shared connection. See [How to Lease a Shared LadybugDB Connection](lease-shared-connection.md).

## Inject it into MemoryCore

Construction is pure dependency injection: build the backend, then pass it to `MemoryCore`. This is the only line that differs from the in-memory setup.

```python
core = MemoryCore(backend)

# From here, the API is identical to the in-memory core.
core.revise("mission-control", "satellite-status", "nominal", source_event_id=uuid7())

base = core.query_scope("mission-control", BeliefFilter())
print({b.belief_id: b.value for b in base})  # {'satellite-status': 'nominal'}
```

!!! tip "Swapping backends is a one-liner"
    Because `MemoryCore` never names a backend, moving from `MemoryCore(InMemoryBackend())` to `MemoryCore(LadybugBackend.open("beliefs.db"))` changes exactly one argument. Your call sites stay the same. Why the core is backend-blind is covered in [The Two Seams](../explanation/beliefstore-vs-backendport.md).

## Close the backend when you own the connection

Because you opened the connection with `open`, the backend **owns** it and you should close it when done:

```python
backend.close()
```

[`close`](../reference/doxastica/backends/ladybug.md#doxastica.backends.ladybug.LadybugBackend.close) closes the connection only when the backend owns it. A backend built from an injected connection (via `from_connection`) leaves the connection open: it is the tenant's handle, and the core never closes someone else's connection. That ownership model is the subject of [How to Lease a Shared Ladybug Connection](lease-shared-connection.md).

## Verification

Reopen the file-backed database in a fresh process and confirm the belief persisted:

```python
from doxastica import BeliefFilter, MemoryCore
from doxastica.backends.ladybug import LadybugBackend

core = MemoryCore(LadybugBackend.open("beliefs.db"))
base = core.query_scope("mission-control", BeliefFilter())
print({b.belief_id: b.value for b in base})  # {'satellite-status': 'nominal'}
```

Seeing the belief you wrote earlier confirms durable storage is working.

## Troubleshooting

**Problem:** `BackendDependencyError` raised on `from doxastica.backends.ladybug import LadybugBackend`.

**Cause:** The optional `ladybug` driver is not installed. doxastica raises a friendly [`BackendDependencyError`](../reference/doxastica/errors.md#doxastica.errors.BackendDependencyError) (rather than a raw `ModuleNotFoundError`) the moment you import the ladybug backend module without the driver present.

**Solution:** Install the extra:

```bash
pip install "doxastica[ladybug]"
```

`BackendDependencyError` subclasses both `DoxasticaError` and the stdlib `ImportError`, so you can catch it as either if you want to fall back to the in-memory backend:

```python
from doxastica import InMemoryBackend, MemoryCore

try:
    from doxastica.backends.ladybug import LadybugBackend

    backend = LadybugBackend.open("beliefs.db")
except ImportError:  # BackendDependencyError is an ImportError
    backend = InMemoryBackend()

core = MemoryCore(backend)
```

## Related guides

- [How to Lease a Shared LadybugDB Connection (Tenant Mode)](lease-shared-connection.md)
- [The Two Seams: BeliefStore vs BackendPort](../explanation/beliefstore-vs-backendport.md)
