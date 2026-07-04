---
title: How to Lease a Shared LadybugDB Connection (Tenant Mode)
description: Inject an existing LadybugDB connection into doxastica under a namespace so the core shares a database as a tenant and never closes a handle it does not own.
---

# How to Lease a Shared LadybugDB Connection (Tenant Mode)

This guide shows you how to run doxastica on a LadybugDB connection that **someone else owns**, for example a host application that opens one database and leases it to several subsystems. doxastica acts as a *tenant*: it writes only its own namespaced tables and never closes the connection.

## Requirements

- doxastica installed with the ladybug extra:

    ```bash
    pip install "doxastica[ladybug]"
    ```

- An existing `ladybug` connection that your application opened and manages. If you only need a standalone database, use [`LadybugBackend.open`](../reference/doxastica/backends/ladybug.md#doxastica.backends.ladybug.LadybugBackend.open) instead. See [How to Use the LadybugDB Backend](ladybug-backend.md).

## Inject the connection with from_connection and a namespace

Your application owns the connection. Build the backend with [`from_connection`](../reference/doxastica/backends/ladybug.md#doxastica.backends.ladybug.LadybugBackend.from_connection), passing a `namespace` that scopes doxastica's tables:

```python
from uuid import uuid7

import ladybug as lb

from doxastica import BeliefFilter, MemoryCore
from doxastica.backends.ladybug import LadybugBackend

# The host application opens and owns this connection.
db = lb.Database("app.db")
conn = lb.Connection(db)

# doxastica leases it as a tenant under its own namespace.
backend = LadybugBackend.from_connection(conn, namespace="beliefs")  # (1)!
core = MemoryCore(backend)

core.revise("mission-control", "satellite-status", "nominal", source_event_id=uuid7())
```

1. `from_connection` records the connection as **not owned**. The backend bootstraps its `beliefs_*` tables idempotently and will never close `conn`.

The namespace prefixes every table doxastica creates (`beliefs_Scope`, `beliefs_BeliefState`, and so on), so the belief subgraph cannot collide with tables other tenants own in the same database.

## Why the core never closes a leased handle

When you build a backend with `from_connection`, the backend marks the connection as injected. Calling [`close`](../reference/doxastica/backends/ladybug.md#doxastica.backends.ladybug.LadybugBackend.close) is then a no-op: the core must never close a connection it did not open, because the host application is still using it.

```python
backend.close()  # no-op for a leased connection — conn stays open
```

The host stays responsible for the connection's lifecycle:

```python
conn.close()  # the owner closes it, when the owner is done
```

!!! warning "Ownership is determined by how you built the backend"
    `LadybugBackend.open(path)` **owns** its connection and closes it on `close()`. `LadybugBackend.from_connection(conn)` does **not** own the connection and never closes it. Pick the constructor that matches who owns the handle; there is no flag to override this after construction.

## Namespace rules

The namespace is interpolated into table-creation statements, so it is validated as a bare identifier before use. It must match `^[A-Za-z_][A-Za-z0-9_]*$`: a letter or underscore followed by letters, digits, or underscores. An invalid namespace raises `ValueError`.

```python
LadybugBackend.from_connection(conn, namespace="beliefs")  # ok
LadybugBackend.from_connection(conn, namespace="host_core")  # ok
LadybugBackend.from_connection(conn, namespace="my-beliefs")  # ValueError: hyphen not allowed
LadybugBackend.from_connection(conn, namespace="1beliefs")  # ValueError: cannot start with a digit
```

Belief data itself never goes through interpolation; only the namespace identifier does, and only after validation. If you omit `namespace`, it defaults to `"dx"`.

## Verification

Confirm doxastica wrote its data and the connection is still usable by the owner afterward:

```python
base = core.query_scope("mission-control", BeliefFilter())
print({b.belief_id: b.value for b in base})  # {'satellite-status': 'nominal'}

backend.close()  # no-op for the leased connection

# The owner's connection still works — the tenant never closed it.
again = core.query_scope("mission-control", BeliefFilter())
print({b.belief_id: b.value for b in again})  # {'satellite-status': 'nominal'}
```

If the second query still returns the belief after `backend.close()`, the tenant correctly left the connection open.

## Troubleshooting

**Problem:** `ValueError: namespace must match ...`

**Cause:** The namespace contains a character outside the bare-identifier set (a hyphen, a leading digit, a dot, or whitespace).

**Solution:** Use only letters, digits, and underscores, starting with a letter or underscore, for example `app_beliefs`.

**Problem:** [`BackendDependencyError`](../reference/doxastica/errors.md#doxastica.errors.BackendDependencyError) on `import ladybug` or on importing the backend.

**Cause:** The ladybug driver is not installed.

**Solution:** `pip install "doxastica[ladybug]"`. See the [LadybugDB backend guide](ladybug-backend.md#troubleshooting) for the full fallback pattern.

## Related guides

- [How to Use the LadybugDB Backend](ladybug-backend.md)
- [The Two Seams: BeliefStore vs BackendPort](../explanation/beliefstore-vs-backendport.md)
