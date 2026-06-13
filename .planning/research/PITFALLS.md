# Pitfalls Research

**Domain:** Graph-native AGM/Hansson belief-revision core (standalone Kumiho impl) over an embedded property graph (LadybugDB/Cypher), append-only revision chains, formal property testing with Hypothesis
**Researched:** 2026-06-13
**Confidence:** HIGH for ladybugdb/Kùzu concurrency, UUID7, Hypothesis facts (verified against docs); HIGH for AGM/Hansson facts (grounded in provided design docs + Flouris impossibility result); MEDIUM where the recommendation is a design judgement rather than a verifiable external fact.

> **Key verified facts driving this analysis:**
> - **LadybugDB is a fork of Kùzu** (started 2025). Its concurrency model is Kùzu's: **single writer, multiple readers, read-committed isolation, serializable ACID transactions.** You can have *either* one `READ_WRITE` Database *or* multiple `READ_ONLY` Databases on a path — never both — enforced by a file lock (`"Could not set lock on file"`), across processes *and* within a process. Multiple `Connection`s from one `READ_WRITE` `Database` are the supported intra-process parallelism path. **In-memory databases (`":memory:"`) are `READ_WRITE`-only and lost on process exit.** (Sources below.)
> - **UUID7 intra-millisecond ordering is implementation-dependent.** RFC 9562 §6.2 makes monotonic-within-ms ordering *optional*; plain random-fill UUID7s sharing a 48-bit timestamp sort in arbitrary order. Python 3.14's stdlib `uuid.uuid7()` *does* guarantee it (42-bit counter); many third-party libs do not. The core receives event ids as **opaque inputs from the caller** and therefore cannot assume generation-side monotonicity.
> - **Hypothesis stateful testing** flags "flaky" when a failing program does not reproduce, and `assume()` inside rules starves the state machine — use `@precondition` instead.

---

## Critical Pitfalls

### Pitfall 1: `query_scope(query: str)` leaks triple/proposition structure into a domain-agnostic core

**What goes wrong:**
The recovered Protocol has `query_scope(scope_id, query: str, include_deprecated=False)`. The moment `query` is interpreted as "match on subject/predicate/object" or as a Cypher fragment over value internals, the core has learned that values are triples — the exact narrative-semantics leak the seam exists to prevent. Conversely, if `query` means *nothing*, the method is useless and NVM routes around the Protocol with raw Cypher, breaking tenancy (R19) and the DI seam.

**Why it happens:**
"Make the query parameter flexible" is the path of least resistance; a `str` invites string-templating into Cypher. The design doc itself flags this as the "underspecified corner of the recovered Protocol" (memory-core §10.1).

**How to avoid:**
- The core must treat `value: Any` as fully opaque. Define `query_scope`'s `query` as operating **only on structure the core legitimately owns**: `scope_id`, `belief_id`, deprecated/superseded status, edge presence/type, event-id ordering. The cleanest resolution is to *replace the free `str`* with a typed, closed filter object (e.g. a Pydantic `ScopeQuery` over fields the core owns) or to make `query_scope` return all current states for a scope and push value-predicate filtering up to NVM. **Decide this before any implementation** — it is an API-shape question, not an impl detail.
- If a `belief_id` predicate is needed, note `belief_id` is a core-owned opaque key — filtering on it is *not* a leak. Filtering on value *contents* is.
- Never accept caller-supplied Cypher. Never `f"...{query}..."` into a query string (also an injection vector — see Security).
- Encode "core never inspects value" as a test: a property test that runs the full suite with `value` set to opaque sentinels (random bytes / UUIDs) and asserts every operation still passes. If any operation needs to look inside `value`, the test breaks and the leak is caught mechanically.

**Warning signs:**
- Any `import` of an NVM/triple/Pydantic-triple type in core code.
- Cypher in the core referencing `value.subject`, `value.predicate`, JSON-path into value, or string-matching value contents.
- `query_scope` signature drifting toward accepting raw Cypher or a DSL that names predicates.
- NVM PRs that bypass the Protocol and hit the DB directly because `query_scope` "wasn't enough."

**Phase to address:** **Protocol/API-design phase (earliest).** This is a signature decision that constrains everything downstream; it is the #1 open question in PROJECT.md. Lock it before the storage layer.

---

### Pitfall 2: `CURRENT_STATE` uniqueness violated — two current states per belief, or zero

**What goes wrong:**
The invariant "exactly one `CURRENT_STATE` per `Belief`" silently breaks. Classic mechanisms: a `revise` creates the new `BeliefState` and the new `CURRENT_STATE` edge but fails to delete the old edge (now two currents); or deletes the old before creating the new and crashes between (zero currents); or two concurrent writers both re-point. Every downstream query (`query_scope`, `get_scope_at`, irony join) then returns duplicated or missing beliefs, and the AGM postulates become untestable because "the current belief set" is ill-defined.

**Why it happens:**
Re-pointing a mutable edge is a read-modify-write. If it is not done inside a single transaction, or if the "delete old + create new" ordering isn't atomic, the window exists. `MATCH ... CREATE` patterns in Cypher are easy to write non-atomically.

**How to avoid:**
- Do the entire re-point inside **one transaction**: in one statement, `MATCH` the existing `CURRENT_STATE`, `DELETE` it, `CREATE` the new `BeliefState` and the new `CURRENT_STATE`. Read-committed isolation + single-writer (Kùzu/LadybugDB) means a single transaction is your serialization boundary — use it.
- **Lean on the single-writer constraint deliberately** (the design calls this "enforces write serialization for free"): route every write through one `READ_WRITE` connection. Do not architect multi-writer.
- Make uniqueness a **structural-invariant property test** run after *every* operation in a Hypothesis state machine: `COUNT((b:Belief)-[:CURRENT_STATE]->()) == 1` for every belief that has any revision. This is explicitly an M0 exit-gate invariant.
- Consider asserting the invariant as a post-condition inside the write method in debug builds (count check before commit).

**Warning signs:**
- `query_scope` returns the same `belief_id` twice.
- A revision chain whose head has no `CURRENT_STATE` pointer.
- The state-machine test fails the uniqueness invariant only on longer sequences (indicates an interleaving/ordering bug, not a logic bug).

**Phase to address:** **Core write-operations phase** (`revise`/`expand`/`contract` implementation). Invariant test lands in the same phase, not deferred to a "testing phase."

---

### Pitfall 3: Append-only discipline broken — accidental deletes/rewrites; world-scope `contract()` not an error

**What goes wrong:**
`BeliefState` nodes or `HAS_REVISION` edges get deleted or mutated (rewriting history), violating the no-retcon contract and breaking `get_scope_at`/`get_revision_chain`. The specific named trap: **`contract()` on the world scope must raise an error** (canon supersedes, never vanishes — memory-core §6.2); if it silently succeeds, the whole "world scope is canonical truth" semantics collapses and NVM's irony join becomes meaningless.

**Why it happens:**
Cypher's `DELETE`/`DETACH DELETE` and `SET` are always available; nothing in the DB enforces append-only. Contraction is *conceptually* "removing a belief," so the naive implementation reaches for `DELETE`. The world-scope special case is an easy omission because `contract()` looks uniform across scopes.

**How to avoid:**
- **Contraction marks, never deletes.** `contract` creates a new `BeliefState` with a retracted/deprecated status and re-points `CURRENT_STATE` (or removes the *current* pointer while leaving the chain intact — design which, and write it down). The only mutable element is the `CURRENT_STATE` edge.
- Make world-scope `contract()` an explicit guard at the top of the method: if `scope_id == world_scope`, raise. Cover with a dedicated test asserting it raises. (memory-core §6.2 calls this the no-retcon "mechanical enforcement point.")
- **Audit for forbidden operations mechanically:** a test (or a grep/AST lint in CI) that fails if `DELETE`, `DETACH DELETE`, or `SET` against `:BeliefState`/`HAS_REVISION` appears anywhere in core Cypher. Append-only is a property you can lint for.
- Chain-immutability property test: snapshot the full revision chain of a belief, run arbitrary further operations, assert the prefix is byte-identical (an M0 exit-gate invariant).

**Warning signs:**
- Any `DELETE`/`DETACH DELETE` touching `:BeliefState` or `HAS_REVISION`.
- `get_revision_chain` length decreasing across operations.
- World-scope contraction returning `None` instead of raising.

**Phase to address:** **Core write-operations phase** (define contraction semantics + world-scope guard). Append-only lint in **CI/tooling phase**.

---

### Pitfall 4: Implementing over deductively-closed belief SETS instead of finite belief BASES

**What goes wrong:**
Treating the stored beliefs as a logically-closed theory (or adding any OWL/DL/entailment inference in the graph layer) is **formally impossible to make AGM-compliant** — the Flouris et al. impossibility result, cited directly in the Kumiho recommendations (§1). The property suite would then be asserting postulates that *cannot* hold, and you'd chase phantom failures forever.

**Why it happens:**
AGM is classically taught over deductively-closed sets, so a faithful reader reaches for closure. "It would be nice if contracting a premise also contracted its consequences" invites entailment into the core.

**How to avoid:**
- Model belief state as a **finite set of explicit ground assertions** (Hansson belief bases). One belief per `Belief` node (granularity strategy (ii) — recommendations §3): partial updates are trivial and contraction targets exactly the explicit node.
- **No inference, no closure, no DL** in the core. Contraction reaches downstream beliefs *only* via explicit `DEPENDS_ON`/`DERIVED_FROM` edges (`get_impact`), never via logical entailment. "Contraction by joint entailment is outside the scope of the formal operator" (recommendations §8) — if NVM wants a derived conclusion contractible, NVM stores it as an explicit `INFERRED_FROM` node.
- Write the property suite over **bases**: generate sequences of explicit assertions and assert the base-level postulates (success, inclusion, vacuity, consistency, extensionality), not closure-level ones.

**Warning signs:**
- Any reasoner / entailment / "compute consequences" code in core.
- Postulate tests that only pass if you assume closure.
- A `value` being interpreted as a logical formula rather than an opaque atom.

**Phase to address:** **Data-model / first-principles phase** (decide bases-not-sets before any storage). It is a foundational modeling decision; getting it wrong is a rewrite.

---

### Pitfall 5: The recovery-exclusion test trap — asserting the recovery postulate against correct code

**What goes wrong:**
The AGM contraction postulates include **recovery** (`K ⊆ (K ÷ p) + p`). doxastica **deliberately excludes recovery** because it is incompatible with immutable versioning (superseded chains are the better semantics — PROJECT.md, recommendations §5, memory-core §8). If the property suite encodes the *standard textbook* postulate set, it will include recovery, and the test will **fail against correctly-implemented code** — then someone "fixes" the code to satisfy recovery, reintroducing retcon and destroying the core's whole value proposition. This is the single most dangerous trap because the failure *looks* like a real bug.

**Why it happens:**
Recovery is one of the six classic AGM contraction postulates; any property suite copied from a textbook or a generic AGM library will include it. The exclusion is a *project-specific* deviation that a fresh implementer (or an LLM generating the suite) will not know to omit.

**How to avoid:**
- **Explicitly enumerate the asserted postulate set in code and docs**, with recovery conspicuously *absent and commented*: success, inclusion, vacuity, consistency, extensionality (the M0 exit-gate list — milestones §M0). Add a named, skipped/xfail test `test_recovery_deliberately_not_asserted` that documents *why* it is excluded and links the rationale, so the absence is loud rather than silent.
- Encode the *positive* replacement: a property test that the superseded chain is preserved (contract-then-expand yields a *new* state with a new event id, not a return to the prior state — recommendations §5). This is the behaviour that *replaces* recovery; testing it prevents anyone "restoring" recovery.
- Put a comment at the top of the postulate module: "RECOVERY IS INTENTIONALLY EXCLUDED. Asserting it will fail correct code. See PROJECT.md."

**Warning signs:**
- A test named `test_recovery` or `test_levi_identity`-derived recovery checks.
- A failing contraction postulate that "proves" the implementation is wrong when the implementation is append-only-correct.
- Any PR that re-points `CURRENT_STATE` *back* to a prior state to "pass" a contraction round-trip.

**Phase to address:** **Property-test-suite phase**, but the *decision* is foundational — flag it in the data-model phase and the postulate module from line one.

---

### Pitfall 6: `get_scope_at` time-travel relies on UUID7 ordering that isn't guaranteed

**What goes wrong:**
`get_scope_at(scope, as_of_event_id)` answers "what did this scope hold as of event E" by ordering `BeliefState`s by their opaque event id. This is **correct only if event ids are totally and monotonically ordered**. But: (a) UUID7s sharing a 48-bit millisecond timestamp are *not* guaranteed to sort in creation order unless the generator is monotonic (RFC 9562 §6.2 makes this optional), and (b) **the core receives event ids as opaque caller inputs** — it has no control over how they were generated. If NVM (or a test) supplies two ids in the same millisecond from a non-monotonic generator, `get_scope_at` can return a state that didn't exist yet, or skip one — a silent correctness bug in the marquee time-travel feature.

**Why it happens:**
"UUID7 is time-sortable" is repeated everywhere without the monotonicity caveat. The opacity contract ("the core never interprets event ids") tempts you to also assume "...but I can still ORDER BY them," which smuggles in an interpretation (a total temporal order) the contract doesn't license.

**How to avoid:**
- **Define the ordering contract explicitly.** The core must state precisely what ordering it assumes: lexicographic/byte order of the event id. Document that **the caller is responsible for supplying ids whose byte order matches intended causal order** (this is a Protocol precondition, and it belongs in the docstring + the README's "opaque event ids" claim).
- Do **not** rely on insertion order or `CREATE` order in the DB; rely on the explicit ordered field. If you need a tie-breaker, add a core-owned monotonic sequence number per write (a thing the core *does* own and control), and order by `(event_id, seq)` — this makes `get_scope_at` well-defined even if two ids collide on timestamp. Decide whether the contract is "ids are authoritative" or "core seq is authoritative" — do not leave it ambiguous.
- **Test the boundary explicitly.** Generate event ids with Hypothesis including same-millisecond and out-of-order cases; assert `get_scope_at(scope, E)` equals a reference replay (fold operations up to and including E). This is the M0 "`get_scope_at` ≡ replay" invariant — make the replay reference independent of UUID7's internal ordering (replay by the same key the core orders on).
- For the project's *own* id generation (standalone mode / tests), use Python 3.14 stdlib `uuid.uuid7()` (monotonic, 42-bit counter) or a library that documents intra-ms monotonicity (e.g. `uuid_utils`); never a plain random-fill v7.

**Warning signs:**
- `ORDER BY` on a timestamp extracted from the value rather than the event id.
- `get_scope_at` flaking only under fast/batched test generation (same-ms ids).
- Replay-equivalence test passing with sleep() between operations but failing without it (the tell-tale of a timestamp-resolution dependence).

**Phase to address:** **`get_scope_at`/time-travel phase**, with the ordering-contract decision made in the **data-model phase** (it co-determines whether you add a core sequence number).

---

### Pitfall 7: `get_impact` cascade — unbounded traversal or silent truncation at the depth boundary

**What goes wrong:**
`get_impact(belief_state_id, depth=5)` traverses dependency edges. Two failure modes: (a) **cycles** in `DEPENDS_ON`/`DERIVED_FROM` cause unbounded traversal / runaway queries if depth isn't strictly enforced; (b) at the depth boundary, the result is **silently truncated** — NVM receives an impact set that *looks* complete but isn't, and contraction-cascade policy acts on a partial picture. The design explicitly flags `depth=5` as "a sketch number" with "truncation policy undesigned" (memory-core §10.3, PROJECT.md open question).

**Why it happens:**
A bare `*1..5` variable-length Cypher pattern silently stops at depth 5 and returns whatever it found, with no signal that more existed. Cycles in a graph are easy to create via `add_edge` (the core does not police edge semantics — that's NVM's job).

**How to avoid:**
- **Make truncation observable, not silent.** Either: return a structured result that flags whether the boundary was hit (`truncated: bool`, or include the frontier nodes), *or* detect cycles and over-depth and surface them. "Bounded mechanism, NVM owns policy" (memory-core §3) means the core must give NVM enough signal to *have* a policy.
- **Always enforce the bound** (Cypher `*1..N` upper bound, never unbounded `*`). Decide and document the default; `depth=5` is fine as a default if the truncation is signalled.
- **De-duplicate visited nodes** so a diamond/cycle doesn't explode or loop. Cypher path semantics can revisit nodes — return distinct `BeliefState`s.
- Property-test with Hypothesis-generated dependency graphs **including cycles and depth > default**; assert (1) the call terminates, (2) the returned set is exactly the reachable-within-depth set, (3) the truncation flag is correct.

**Warning signs:**
- A `get_impact` query with no upper bound on the variable-length pattern.
- Query latency growing super-linearly with graph size in tests.
- NVM logic that assumes `get_impact` is exhaustive.

**Phase to address:** **`get_impact`/edge-traversal phase.** The truncation-signalling API decision is part of the **Protocol/API-design phase** (it changes the return type).

---

### Pitfall 8: Test isolation against an embedded single-writer DB — lock contention and leaked state

**What goes wrong:**
LadybugDB/Kùzu enforces **one `READ_WRITE` per database path, process-wide and cross-process, via a file lock.** Tests that (a) open a shared on-disk path, (b) run pytest with `-n` (xdist parallelism), or (c) leak a `Database` object between tests will hit `"Could not set lock on file"` or — worse — see state bleed between tests, producing flaky postulate failures that look like belief-revision bugs but are test-harness bugs. In-memory DBs (`":memory:"`) are `READ_WRITE`-only and vanish on process exit, which is *good* for isolation but means you cannot share one across a reader/writer split.

**Why it happens:**
The design says tests use "private throwaway databases," but the *mechanics* (fresh path or `:memory:` per test, explicit close, no parallel writers to one path) are easy to get subtly wrong. xdist parallelism is a common default that collides with single-writer.

**How to avoid:**
- **One fresh database per test** — either `":memory:"` (preferred: fast, auto-isolated, no cleanup) or a unique `tmp_path` file per test via a pytest fixture. Never a module-global shared writable DB.
- **Explicitly close** `Database`/`Connection` in fixture teardown so the file lock is released before the next test (especially with on-disk paths). A leaked handle = lock error in the next test.
- If using pytest-xdist, ensure each worker/test gets its own path (`:memory:` makes this automatic).
- Route all writes through **one connection** per test, matching production's single-writer discipline — don't spawn competing writers in tests.
- Verify the **injected-connection vs. open-own** connection model (PROJECT.md research target) against this: in injected mode the *caller* owns the lock; tests for standalone mode must not also try to open the same path.

**Warning signs:**
- `"Could not set lock on file"` in CI.
- Postulate tests passing in isolation but failing under the full suite / parallel run.
- Tests that pass on a clean checkout but fail on re-run (leaked on-disk DB files).

**Phase to address:** **Test-harness / fixtures phase** (very early — the fixture shape gates every subsequent test). Connection-model design in the **storage-layer phase**.

---

### Pitfall 9: Connection-model design (injected vs. open-own) breaks tenancy or the single-writer guarantee

**What goes wrong:**
The core must support both an **injected** `READ_WRITE` connection (NVM owns the handle, leases under label tenancy — R19) *and* opening/managing its own connection (standalone). Get this wrong and either: the core opens a *second* `READ_WRITE` Database on a path NVM already holds → file-lock error or corruption; or the core writes outside its label families (`:Scope`/`:Belief`/`:BeliefState`) and tramples NVM's entity/topology nodes.

**Why it happens:**
Two connection lifecycles (own vs. borrowed) is genuinely fiddly. The single-writer constraint means "open my own connection" is *unsafe* if anyone else holds `READ_WRITE` on that path — but that's invisible until runtime.

**How to avoid:**
- **Never open a `Database` when given an injected connection** — accept the connection (or Database) object and use it; ownership/lifecycle stays with the caller. Only open (and close) a `Database` in standalone mode where the core *is* the sole writer.
- Confine all core writes to its owned label families and edge types; namespace via the `namespace_prefix`. The core subgraph is *closed* (no outbound graph refs — memory-core §9a): entity mentions live as opaque values, never as edges to NVM nodes.
- Document the precondition: standalone mode assumes exclusive `READ_WRITE` ownership of the path; injected mode assumes the caller has serialized access.
- Test both modes; for injected mode, simulate NVM by creating the Database in the test and passing the connection in.

**Warning signs:**
- The core calling `lb.Database(...)` in a code path that also accepts an injected connection.
- Lock errors only in integration (NVM-side) but not unit tests.
- Core Cypher writing labels it doesn't own.

**Phase to address:** **Storage-layer / connection-model phase.** This is the named research target in PROJECT.md — design it explicitly, don't infer it.

---

### Pitfall 10: Hypothesis stateful tests — `assume()` starvation, false-flaky failures, and weak shrinking

**What goes wrong:**
The AGM suite is "Hypothesis over operation sequences" — a `RuleBasedStateMachine` is the natural fit. Three specific failures: (a) using `assume()` *inside* rules (e.g. "only contract a belief that exists") starves the machine — runs where the assumption fails are wasted and few/no rules fire; (b) **"flaky" errors** when a failed sequence doesn't reproduce — caused by hidden non-determinism (wall-clock, random UUID7 generation inside the test, un-reset DB state, dict ordering); (c) poor shrinking that yields huge unreadable counterexamples because the model/`Bundle` structure doesn't let Hypothesis minimize.

**Why it happens:**
`assume()` is the obvious tool but the wrong one for stateful preconditions. Non-determinism is easy to introduce (generating ids with a random source, or sharing a DB between examples). Without `Bundle`s and a parallel model, shrinking has nothing to shrink toward.

**How to avoid:**
- Use **`@precondition`**, not `assume()`, to gate rules (e.g. `@precondition(lambda self: self.beliefs)` before `contract`). Hypothesis filters inapplicable rules *before* running them — verified in the docs.
- **Eliminate non-determinism inside examples:** fresh `:memory:` DB per example (state-machine `__init__`), event ids drawn from Hypothesis strategies (so they're part of the shrinkable input and reproducible) rather than from a live random generator, and a deterministic seed where needed. If Hypothesis reports "flaky," treat it as a real non-determinism bug, not a Hypothesis quirk.
- Maintain a **parallel in-memory model** of the expected belief base and assert it against the DB after each rule (the classic model-based testing pattern). This both finds bugs and gives shrinking a clean target.
- Use **`Bundle`s** to carry created `belief_id`s/`event_id`s between rules so generated sequences reference real prior state (and shrink well).
- Add `@invariant()` methods for the structural invariants (CURRENT_STATE uniqueness, chain immutability) so they're checked after every step automatically.

**Warning signs:**
- "Hypothesis is flaky" in CI logs.
- Counterexamples that are hundreds of operations long (shrinking failure).
- Rules that mostly no-op because their `assume()` rarely passes.

**Phase to address:** **Property-test-suite phase**, but seed the `:memory:`-per-example + model-based pattern in the **test-harness phase** so it's the default from the first test.

---

### Pitfall 11: Deprecated vs. superseded conflated — the structural distinction collapses

**What goes wrong:**
The core owns a *structural* distinction: **superseded** = a newer `BeliefState` exists in the chain (`SUPERSEDES` edge); **deprecated** = excluded from default retrieval (the `include_deprecated` query flag). If these are conflated (e.g. treating "has a successor" as "deprecated", or using one flag for both), `query_scope(include_deprecated=...)` returns the wrong set, and NVM's forgotten-vs-revised meaning (layered on top) becomes inexpressible.

**Why it happens:**
Both concepts gesture at "not the live belief," so a single boolean feels sufficient. The recommendations doc (§2) explicitly warns these are distinct and that conflation causes superseded states to wrongly rank/surface.

**How to avoid:**
- Keep them orthogonal: superseded is **derived from chain position** (there is a later state); deprecated is an **explicit status/flag** set by `contract`. A state can be current-and-not-deprecated, superseded-but-retrievable, or deprecated.
- `query_scope` default returns current, non-deprecated states; `include_deprecated=True` widens to deprecated; `get_revision_chain` returns the full (including superseded) chain regardless.
- Test the matrix: assert each of the four (current/superseded × deprecated/active) combinations is queryable exactly as specified.

**Warning signs:**
- A single boolean serving both "is old" and "is forgotten."
- Superseded historical states appearing in default `query_scope` output.

**Phase to address:** **Retrieval phase** (`query_scope` / `get_revision_chain`), with the status model decided in the **data-model phase**.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| `query: str` as free-form / Cypher passthrough in `query_scope` | Ships a "flexible" retrieval API fast | Triple structure leaks into core; injection risk; tenancy bypass; reopens the #1 design question | **Never** — resolve the signature before impl |
| Non-atomic `CURRENT_STATE` re-point (delete-then-create across statements) | Simpler Cypher | Uniqueness invariant breaks under any interruption | **Never** — must be one transaction |
| `*` unbounded or unsignalled `*1..5` traversal in `get_impact` | One-line Cypher | Runaway on cycles / silent truncation; NVM acts on partial impact | **Never** for unbounded; bounded-without-signal only as a temporary spike |
| `assume()` instead of `@precondition` in state-machine rules | Familiar API | Rule starvation, weak coverage of the actual postulates | Only in a throwaway exploratory test |
| On-disk shared DB across tests | "Realistic" | Lock contention, flaky cross-test bleed | Only for an explicit persistence/round-trip test that opens+closes its own path |
| Plain random-fill UUID7 in tests/standalone | Any uuid7 lib works | Same-ms ordering bug surfaces as `get_scope_at` flakiness | Only if the core orders on a self-owned sequence number, not the id |
| Skip the recovery-exclusion comment/xfail marker | Less ceremony | A future contributor "fixes" correct code to satisfy recovery | **Never** — the loud marker is the safeguard |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| LadybugDB connection (injected) | Core opens its own `Database` on an injected path | Use the supplied connection; only open/close in standalone mode |
| LadybugDB writes | Spawning multiple `READ_WRITE` Databases / processes | One `READ_WRITE` Database; multiple `Connection`s if intra-process parallelism is ever needed |
| LadybugDB in-memory | Expecting `:memory:` data to persist or be openable READ_ONLY | `:memory:` is `READ_WRITE`-only and lost on exit — for ephemeral tests only |
| LadybugDB Cypher params | String-interpolating `value`/`query` into Cypher | Parameterized queries (`$param`) exclusively |
| LadybugDB (Kùzu lineage) | Assuming Neo4j-identical Cypher/behaviour | It's a Kùzu fork — verify Cypher dialect, schema-declaration requirements (Kùzu requires explicit node/rel table schemas), and transaction semantics against LadybugDB docs, not Neo4j |
| Caller-supplied event ids | Assuming they're monotonic / collision-free in order | Treat as opaque; define byte-order contract; add core sequence tie-breaker |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Unbounded/cyclic `get_impact` traversal | Latency explodes; query hangs | Hard depth bound + distinct nodes + cycle handling | As soon as `add_edge` creates a cycle or a deep chain |
| Re-querying full chain to find current state | Slow `query_scope` as chains grow | Read `CURRENT_STATE` pointer directly; don't scan `HAS_REVISION` | Chains of dozens+ revisions |
| Missing schema/index on `belief_id`/`scope_id` lookup | Linear scans in Cypher | Declare Kùzu/LadybugDB node-table primary keys / indexes for lookup fields | Hundreds+ beliefs per scope |
| Per-operation transaction overhead in bulk tests | Slow Hypothesis runs | Acceptable — correctness > speed here; use `:memory:` to keep it fast | Large generated sequences (mitigated, not a prod concern) |

*Note: NVM's stated scale is modest (tens to low-hundreds of beliefs per actor — recommendations §3). Do not over-engineer for scale; correctness and boundedness matter more than throughput.*

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Interpolating `query`/`value` into Cypher strings | Cypher injection; arbitrary graph read/write | Parameterized queries only; closed typed filter for `query_scope` |
| Core trusting caller event ids for ordering authority | A malicious/buggy caller reorders history via crafted ids | Document the byte-order precondition; optionally pin authority to a core-owned sequence |
| Standalone mode opening a DB another process holds RW | Lock error or corruption | Single-writer discipline; document exclusive-ownership precondition |

## UX Pitfalls

*(Library/API-DX, not end-user UX.)*

| Pitfall | Consumer Impact | Better Approach |
|---------|-----------------|-----------------|
| Silent `get_impact` truncation | NVM acts on incomplete cascade, can't tell | Return a truncation/frontier signal |
| Ambiguous event-id ordering contract | NVM can't reason about `get_scope_at` correctness | Document the ordering precondition explicitly in the Protocol docstrings |
| `query_scope` returning duplicates on invariant break | NVM dedups defensively, masking core bugs | Enforce CURRENT_STATE uniqueness; let it be a hard invariant |
| `contract()` on world scope returning None | NVM silently retcons canon | Raise a typed error; document it as part of the contract |

## "Looks Done But Isn't" Checklist

- [ ] **AGM postulate suite:** Often missing — recovery *correctly excluded* AND a positive superseded-chain test in its place. Verify recovery is conspicuously absent with rationale, not silently dropped.
- [ ] **`get_scope_at`:** Often missing — the same-millisecond / out-of-order event-id boundary test. Verify it equals a reference replay under colliding ids.
- [ ] **`get_impact`:** Often missing — cycle handling and truncation signalling. Verify it terminates on a cyclic dependency graph and reports boundary hits.
- [ ] **`contract`:** Often missing — the world-scope error path. Verify a test asserts it raises.
- [ ] **Append-only:** Often missing — a mechanical lint/test that no `DELETE`/`SET` touches `:BeliefState`/`HAS_REVISION`. Verify CI fails if one is added.
- [ ] **CURRENT_STATE uniqueness:** Often missing — checked after *every* op in the state machine, not just once. Verify it's an `@invariant`.
- [ ] **Connection model:** Often missing — the injected path that does NOT open its own Database. Verify both modes are tested.
- [ ] **Value opacity:** Often missing — a test running the suite with opaque sentinel values. Verify no core code inspects `value`.
- [ ] **Test isolation:** Often missing — fresh `:memory:`/tmp DB per test with explicit teardown. Verify the suite passes under `-p no:randomly` AND parallel/repeat runs.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| `query_scope` leaked triple structure | HIGH | Redesign the query parameter to a closed filter; rip out value introspection; re-verify opacity test — touches the Protocol and every consumer |
| Recovery postulate asserted, code "fixed" to satisfy it | HIGH | Revert the retcon "fix"; remove the recovery assertion; re-add superseded-chain test; audit `CURRENT_STATE` re-pointing for back-pointing |
| CURRENT_STATE uniqueness broken | MEDIUM | Wrap re-point in one transaction; add `@invariant`; backfill a repair query to dedup existing pointers |
| Append-only violated (history rewritten) | HIGH | Data is gone if deletes ran — restore from a known-good DB; add the lint; this is why the lint is non-negotiable |
| UUID7 ordering bug in `get_scope_at` | MEDIUM | Add core sequence tie-breaker; order on `(event_id, seq)`; re-run replay-equivalence boundary test |
| Test-harness lock/bleed flakiness | LOW | Switch fixtures to `:memory:`-per-test with teardown; remove shared writable paths |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1. `query_scope` structure leak | Protocol/API-design (earliest) | Opaque-value sentinel test passes; no triple imports in core |
| 4. Belief bases not sets | Data-model / first-principles | Postulate suite green over bases; no reasoner in core |
| 5. Recovery-exclusion trap | Data-model decision → Property-test-suite | Named xfail/comment present; superseded-chain test green |
| 6. UUID7 ordering contract | Data-model (decide seq) → time-travel | `get_scope_at` ≡ replay under colliding/out-of-order ids |
| 2. CURRENT_STATE uniqueness | Core write-operations | `@invariant` count==1 after every op |
| 3. Append-only + world-scope contract | Core write-operations (+ CI lint) | World-scope contract raises; no DELETE/SET on chain; chain-immutability test |
| 7. `get_impact` cascade | Edge-traversal (+ API return shape) | Terminates on cycles; truncation flag correct; distinct nodes |
| 11. Deprecated vs superseded | Data-model → Retrieval | Four-cell query matrix test |
| 9. Connection model | Storage-layer / connection-model | Both injected + standalone modes tested; no double-open |
| 8. Test isolation (single-writer) | Test-harness / fixtures (early) | Suite green under parallel + repeat runs; no lock errors |
| 10. Hypothesis stateful pitfalls | Test-harness → Property-test-suite | No "flaky" reports; `@precondition` used; small shrunk counterexamples; model-based |

**Phase-ordering implication for the roadmap:** the three *decision* pitfalls (1 query semantics, 4 bases-not-sets, 6 ordering contract) and 5 (recovery exclusion) must be settled in an early **data-model / Protocol-design phase before storage code exists** — they are signature/modeling decisions whose reversal is a rewrite. The **test-harness fixture shape (8, 10)** must land before the first property test. Write-operation invariants (2, 3) and traversal/retrieval correctness (7, 11) are per-feature and verified in their own phase. The connection-model research (9) gates the storage phase.

## Sources

- LadybugDB — Python API (connection/transaction, `:memory:` vs on-disk, async): https://docs.ladybugdb.com/client-apis/python/ (HIGH)
- LadybugDB — homepage / overview (embedded, Cypher, serializable ACID, fork lineage): https://docs.ladybugdb.com/ , https://github.com/LadybugDB/ladybug (HIGH)
- Kùzu — concurrency model (single-writer, READ_WRITE/READ_ONLY exclusivity, file lock, read-committed, in-memory caveats) — LadybugDB is a Kùzu fork, so this is authoritative for the engine: https://kuzudb.github.io/docs/concurrency/ (HIGH)
- Kùzu provenance / LadybugDB-as-fork: https://thedataquarry.com/blog/embedded-db-2/ , https://dbdb.io/db/ladybugdb (MEDIUM — corroborating)
- Hypothesis — stateful testing (`@precondition` vs `assume()`, flaky semantics, shrinking, Bundles, invariants): https://hypothesis.readthedocs.io/en/latest/stateful.html , https://github.com/HypothesisWorks/hypothesis/blob/master/hypothesis-python/docs/stateful.rst (HIGH)
- RFC 9562 §6.2 monotonicity (UUID7 intra-ms ordering optional) + Python 3.14 stdlib `uuid.uuid7()` 42-bit counter: https://docs.python.org/3/library/uuid.html , https://www.authgear.com/post/time-sortable-identifiers-uuidv7-ulid-snowflake/ (HIGH for stdlib behaviour; HIGH for RFC optionality)
- AGM/Hansson belief bases, Flouris impossibility, recovery rejection, granularity, UUID7 lineage: doxastica design docs — `narrative-vm/_design/v2/17-kumiho-nvm-recommendations.md` §§1–5, `05-nvm-memory-core.md` §§2,3,6,8,9a,10, `15-nvm-milestones.md` §M0 (HIGH — project-internal spec)

---
*Pitfalls research for: graph-native AGM belief-revision core (doxastica / Kumiho impl)*
*Researched: 2026-06-13*
