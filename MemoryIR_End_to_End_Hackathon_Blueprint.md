# MemoryIR — End-to-End Hackathon Build Specification

## 1. What We Are Actually Building

The hackathon MVP should answer one question extremely well:

> **When an agent says it used memory X to make a decision, did X actually influence the decision—and if X was itself derived from older memories, what was the true causal ancestry?**

The whole system becomes:

```text
                         MEMORYIR
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  User                                                       │
│   │                                                         │
│   ▼                                                         │
│  Agent Query                                                │
│   │                                                         │
│   ├──── embed query ──────────────────────────────┐          │
│   │                                              │          │
│   ▼                                              ▼          │
│ AWS Lambda                                CockroachDB        │
│ Agent Runtime                             Vector Index       │
│   │                                              │          │
│   │                                      retrieve M7,M12    │
│   │                                              │          │
│   ◄──────────────────────────────────────────────┘          │
│   │                                                         │
│   ▼                                                         │
│ LLM generates answer + claimed memory provenance            │
│   │                                                         │
│   ├── store trace ───────────────────────────────► CRDB     │
│   │                                                         │
│   ▼                                                         │
│ MemoryIR Intervention Engine                                │
│   │                                                         │
│   ├─ remove M7  → rerun agent                               │
│   ├─ remove M12 → rerun agent                               │
│   └─ inspect derived ancestors                              │
│                                                             │
│                 M1 ─┐                                      │
│                 M2 ─┼──► M7 ───► decision                   │
│                 M3 ─┘      ▲                                │
│                            │                                │
│                      lineage graph                          │
│                                                             │
│   ▼                                                         │
│ Attribution Report                                          │
│                                                             │
│ "Agent claimed M7 + M12.                                    │
│  Only M7 changed the decision.                              │
│  M7's decisive ancestor was M2."                            │
└─────────────────────────────────────────────────────────────┘
```

### CockroachDB Integrations

We explicitly use:

1. **Distributed Vector Indexing**
   - Used for actual persistent-memory retrieval.

2. **CockroachDB Cloud Managed MCP**
   - Used for the MemoryIR forensic investigator.

CockroachDB's vector index performs ANN search directly over `VECTOR` columns, including prefix-indexed search, so we do not need Pinecone, Qdrant, or another vector database.

The managed MCP supports HTTPS, OAuth or API-key authentication, cluster scoping, schema inspection, `SELECT` queries, and other tools, so we can build the investigator against the exact same live memory database.

---

# 2. Recommended Production Stack

Lock the stack as follows:

| Layer | Choice |
|---|---|
| Frontend | React + TypeScript + Vite |
| UI | Tailwind + React Flow |
| Backend | Python 3.12 + FastAPI |
| AWS adapter | Mangum |
| AWS compute | **AWS Lambda** |
| Public endpoint | Lambda Function URL |
| Database | **CockroachDB Cloud Basic** |
| DB driver | psycopg 3 |
| Vector DB | **CockroachDB VECTOR** |
| Embeddings | Bedrock Titan Embeddings V2, 256 dimensions |
| Agent model | Bedrock model behind adapter |
| MCP | CockroachDB Managed MCP |
| Infra | AWS SAM |
| Tests | pytest + Vitest |
| Repo | GitHub |
| License | MIT |

## Why Lambda Function URL Instead of API Gateway + S3 + CloudFront?

For a six-day hackathon build, simplify aggressively.

Package:

```text
React production build
         +
FastAPI backend
         +
Mangum
         ↓
   ONE Lambda
         ↓
Lambda Function URL
```

FastAPI serves `/api/*`.

FastAPI also serves `/assets/*` and `index.html`.

So:

```text
https://xyz.lambda-url.us-east-1.on.aws/

         ↓

MemoryIR complete application
```

No API Gateway.

No CloudFront.

No EC2.

No ECS.

No Kubernetes.

No Redis.

No separate vector database.

This gives the fewest possible things capable of breaking before the deadline.

---

# 3. Repository Structure

Create exactly this:

```text
memoryir/
│
├── README.md
├── LICENSE
├── .env.example
├── template.yaml
├── Makefile
│
├── db/
│   ├── migrations/
│   │   ├── 001_schema.sql
│   │   ├── 002_vector_index.sql
│   │   └── 003_seed_demo.sql
│   └── queries/
│       ├── retrieval.sql
│       ├── ancestry.sql
│       └── trace_report.sql
│
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db.py
│   │   │
│   │   ├── api/
│   │   │   ├── memories.py
│   │   │   ├── consolidate.py
│   │   │   ├── query.py
│   │   │   ├── traces.py
│   │   │   ├── interventions.py
│   │   │   ├── forensics.py
│   │   │   └── evaluation.py
│   │   │
│   │   ├── services/
│   │   │   ├── embeddings.py
│   │   │   ├── llm.py
│   │   │   ├── memory_store.py
│   │   │   ├── retriever.py
│   │   │   ├── consolidator.py
│   │   │   ├── generator.py
│   │   │   ├── lineage.py
│   │   │   ├── interventions.py
│   │   │   ├── attribution.py
│   │   │   └── mcp_investigator.py
│   │   │
│   │   ├── models/
│   │   │   ├── memory.py
│   │   │   ├── trace.py
│   │   │   └── report.py
│   │   │
│   │   └── prompts/
│   │       ├── agent.txt
│   │       ├── consolidation.txt
│   │       └── investigator.txt
│   │
│   └── tests/
│       ├── test_retrieval.py
│       ├── test_lineage.py
│       ├── test_interventions.py
│       └── test_attribution.py
│
├── frontend/
│   ├── package.json
│   └── src/
│       ├── App.tsx
│       ├── api.ts
│       ├── pages/
│       │   ├── Home.tsx
│       │   ├── MemoryLab.tsx
│       │   ├── TraceExplorer.tsx
│       │   ├── Forensics.tsx
│       │   └── Evaluation.tsx
│       └── components/
│           ├── MemoryCard.tsx
│           ├── MemoryGraph.tsx
│           ├── RetrievalPanel.tsx
│           ├── AttributionPanel.tsx
│           ├── InterventionMatrix.tsx
│           └── FaithfulnessScore.tsx
│
└── eval/
    ├── cases/
    │   ├── clean.jsonl
    │   ├── proxy_citation.jsonl
    │   ├── one_hop.jsonl
    │   └── multi_hop.jsonl
    ├── run_eval.py
    └── summarize.py
```

---

# 4. CockroachDB Schema

This should be settled before writing frontend code.

## `agents`

```sql
CREATE TABLE agents (
    agent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name STRING NOT NULL,
    description STRING,
    model_id STRING NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## `sessions`

```sql
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(agent_id),
    title STRING,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## `memory_sources`

Where did a ground memory originally come from?

```sql
CREATE TABLE memory_sources (
    source_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type STRING NOT NULL,
    source_name STRING,
    source_uri STRING,
    trust_label STRING NOT NULL DEFAULT 'unknown',
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Examples:

```text
USER
DOCUMENT
TOOL_OUTPUT
OBSERVATION
SYSTEM
SYNTHETIC_EVAL
```

---

# 5. Core `memories` Table

This is the center of MemoryIR.

Use a **256-dimensional embedding** to keep vectors small. Titan Text Embeddings V2 supports 256, 512, or 1024 dimensional output.

```sql
CREATE TABLE memories (
    memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    agent_id UUID NOT NULL REFERENCES agents(agent_id),
    session_id UUID REFERENCES sessions(session_id),
    source_id UUID REFERENCES memory_sources(source_id),

    memory_type STRING NOT NULL,
    content STRING NOT NULL,

    embedding VECTOR(256),

    generation INT NOT NULL DEFAULT 0,

    content_hash STRING,
    metadata JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

`memory_type`:

```text
raw
derived
consolidated
synthetic
```

`generation` gives us an immediate visual:

```text
M1 generation 0
       │
       ▼
M4 generation 1
       │
       ▼
M9 generation 2
```

---

# 6. Cockroach Distributed Vector Index

Create it while the table is empty.

```sql
CREATE VECTOR INDEX memories_agent_embedding_idx
ON memories (agent_id, embedding);
```

CockroachDB supports prefix columns on vector indexes, which means retrieval can constrain `agent_id` before ANN search.

Retrieval becomes approximately:

```sql
SELECT
    memory_id,
    content,
    memory_type,
    generation,
    embedding <-> $2::VECTOR AS distance
FROM memories
WHERE agent_id = $1
ORDER BY embedding <-> $2::VECTOR
LIMIT $3;
```

This is the first explicit hackathon technology requirement.

---

# 7. `memory_edges`

This creates the actual **memory DAG**.

```sql
CREATE TABLE memory_edges (
    edge_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    parent_memory_id UUID NOT NULL
        REFERENCES memories(memory_id),

    child_memory_id UUID NOT NULL
        REFERENCES memories(memory_id),

    relation_type STRING NOT NULL,

    declared_weight FLOAT8,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(parent_memory_id, child_memory_id, relation_type)
);
```

Example:

```text
M1 ────┐
       │
M2 ────┼────► M7
       │
M3 ────┘
```

Rows:

```text
M1 → M7    consolidated_from
M2 → M7    consolidated_from
M3 → M7    consolidated_from
```

Important distinction:

`declared_weight` is **not causal importance**.

It can represent what the consolidation process claims contributed.

MemoryIR later measures actual interventional influence separately.

That distinction matters scientifically.

---

# 8. `consolidation_runs`

```sql
CREATE TABLE consolidation_runs (
    consolidation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    agent_id UUID NOT NULL REFERENCES agents(agent_id),
    session_id UUID REFERENCES sessions(session_id),

    output_memory_id UUID NOT NULL
        REFERENCES memories(memory_id),

    model_id STRING NOT NULL,
    prompt_version STRING NOT NULL,

    input_count INT NOT NULL,

    latency_ms INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

This gives:

```text
C14
│
├─ inputs: M1,M2,M3
├─ model
├─ prompt version
└─ output: M7
```

---

# 9. `traces`

Every user → agent interaction gets exactly one trace.

```sql
CREATE TABLE traces (
    trace_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    agent_id UUID NOT NULL REFERENCES agents(agent_id),
    session_id UUID REFERENCES sessions(session_id),

    user_query STRING NOT NULL,

    response_text STRING,

    decision_label STRING,

    model_id STRING,
    temperature FLOAT8,

    status STRING NOT NULL DEFAULT 'running',

    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);
```

## `decision_label` Is Extremely Important

Instead of trying to determine whether two paragraphs are "causally different", demo tasks should have a constrained decision:

```text
APPROVE
REJECT
```

or:

```text
POSTGRES
DYNAMODB
COCKROACHDB
```

or:

```text
OPTION_A
OPTION_B
OPTION_C
```

Then the intervention metric can be exact:

```text
baseline = COCKROACHDB

remove M7
        ↓

counterfactual = DYNAMODB

Decision changed = TRUE
```

This is much stronger than asking another LLM whether two essays seem different.

---

# 10. `retrieval_runs`

```sql
CREATE TABLE retrieval_runs (
    retrieval_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    trace_id UUID NOT NULL REFERENCES traces(trace_id),

    query_text STRING NOT NULL,

    top_k INT NOT NULL,
    embedding_model STRING,

    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    latency_ms INT
);
```

---

# 11. `retrieval_items`

```sql
CREATE TABLE retrieval_items (
    retrieval_id UUID NOT NULL
        REFERENCES retrieval_runs(retrieval_id),

    memory_id UUID NOT NULL
        REFERENCES memories(memory_id),

    retrieval_rank INT NOT NULL,
    vector_distance FLOAT8 NOT NULL,

    PRIMARY KEY (retrieval_id, memory_id)
);
```

Now we have **ground retrieval provenance**.

Example:

```text
TRACE T17

Vector retrieval
─────────────────
1   M7     0.113
2   M12    0.181
3   M4     0.226
4   M19    0.303
```

---

# 12. `generation_claims`

This stores what the agent **claims** it relied upon.

```sql
CREATE TABLE generation_claims (
    claim_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    trace_id UUID NOT NULL REFERENCES traces(trace_id),
    memory_id UUID REFERENCES memories(memory_id),

    claim_type STRING NOT NULL,
    claimed_rank INT,

    explanation STRING,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Agent returns structured output:

```json
{
  "answer": "CockroachDB",
  "decision": "COCKROACHDB",
  "memory_attribution": [
    {
      "memory_id": "M7",
      "importance": 1,
      "reason": "Multi-region requirement"
    },
    {
      "memory_id": "M12",
      "importance": 2,
      "reason": "Operational simplicity"
    }
  ]
}
```

Store both claims.

Now compare:

```text
RETRIEVED:
M7 M12 M19

CLAIMED:
M7 M12

ACTUALLY INFLUENTIAL:
M7
```

That is MemoryIR.

---

# 13. `intervention_runs`

```sql
CREATE TABLE intervention_runs (
    intervention_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    trace_id UUID NOT NULL REFERENCES traces(trace_id),

    intervention_type STRING NOT NULL,

    target_memory_id UUID
        REFERENCES memories(memory_id),

    target_depth INT DEFAULT 0,

    baseline_decision STRING,
    counterfactual_decision STRING,

    baseline_response STRING,
    counterfactual_response STRING,

    decision_changed BOOL,

    semantic_delta FLOAT8,
    effect_score FLOAT8,

    latency_ms INT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Intervention types:

```text
RETRIEVED_MEMORY_ABLATION
ANCESTOR_ABLATION
RETRIEVAL_RANK_PERTURBATION
MEMORY_REPLACEMENT
LINEAGE_RECOMPUTATION
```

The MVP only needs the first two.

---

# 14. Lineage Traversal

For:

```text
M2 → M7 → M11
```

we need transitive ancestry.

Conceptually:

```sql
WITH RECURSIVE ancestry AS (
    SELECT
        parent_memory_id,
        child_memory_id,
        1 AS depth
    FROM memory_edges
    WHERE child_memory_id = $1

    UNION ALL

    SELECT
        e.parent_memory_id,
        e.child_memory_id,
        a.depth + 1
    FROM memory_edges e
    JOIN ancestry a
      ON e.child_memory_id = a.parent_memory_id
)
SELECT *
FROM ancestry;
```

This lets MemoryIR say:

```text
Retrieved M11

M11
 └── M7
      ├── M2
      ├── M3
      └── M4

max lineage depth = 2
```

---

# 15. The Crucial Derived-Memory Intervention

This is the feature to prioritize above almost everything else.

Suppose:

```text
M2 ─┐
M3 ─┼─► M7 ─► M11 ─► decision
M4 ─┘
```

If M11 is causal, MemoryIR then asks:

> Is M2 actually responsible for the information in M11 that caused the decision?

Implement:

```python
counterfactual_without(M2)
```

as:

```text
remove M2

recompute M7
      ↓
M7'

recompute M11 using M7'
      ↓
M11'

rerun final agent
      ↓

compare decision
```

That is the feature separating MemoryIR from ordinary attribution.

---

# 16. Attribution Engine

Backend service:

```text
attribution.py
```

gets:

```text
retrieved set R
claimed set C
influential set I
```

Calculate separately:

## Claim/Retrieval Precision

```text
|C ∩ R|
───────
  |C|
```

Did it claim memories that were even available?

## Causal Precision

```text
|C ∩ I|
───────
  |C|
```

How many claimed memories actually mattered?

## Causal Recall

```text
|C ∩ I|
───────
  |I|
```

Did the agent mention the memories that mattered?

## Proxy Citation Rate

The especially interesting one:

```text
Agent cited derived M7

but causal chain is:

M2 → M7 → decision
```

Report:

```text
Proxy citation: TRUE
Ground ancestor: M2
Proxy depth: 1
```

For:

```text
M2 → M7 → M11 → decision
```

```text
Proxy depth: 2
```

This should be a first-class metric in MemoryIR.

---

# 17. Backend API

Do not make dozens of endpoints.

## Memories

```text
POST /api/memories
GET  /api/memories
GET  /api/memories/{memory_id}
GET  /api/memories/{memory_id}/lineage
```

## Consolidation

```text
POST /api/consolidations
GET  /api/consolidations/{id}
```

Request:

```json
{
  "memory_ids": ["M1", "M2", "M3"]
}
```

Response:

```json
{
  "output_memory_id": "M7",
  "content": "...",
  "generation": 1
}
```

## Agent

```text
POST /api/query
```

Request:

```json
{
  "query": "Which database should we choose?",
  "top_k": 5
}
```

Response:

```json
{
  "trace_id": "T42",
  "answer": "CockroachDB",
  "decision": "COCKROACHDB",
  "retrieved": [...],
  "claimed": [...]
}
```

## Interventions

```text
POST /api/traces/{trace_id}/interventions
GET  /api/traces/{trace_id}/interventions
```

## Full Report

```text
GET /api/traces/{trace_id}/report
```

Response:

```json
{
  "claimed_memories": ["M7", "M12"],
  "retrieved_memories": ["M7", "M12", "M16"],
  "influential_memories": ["M7"],

  "causal_precision": 0.5,
  "causal_recall": 1.0,

  "ground_provenance": [
    {
      "retrieved": "M7",
      "ancestor": "M2",
      "depth": 1,
      "decision_changed": true
    }
  ]
}
```

---

# 18. MCP Forensic Investigator

This is Cockroach requirement #2.

The managed service supports API-key authentication and lets the connection be limited to a specific cluster using `mcp-cluster-id`.

Backend:

```text
mcp_investigator.py
```

connects to:

```text
https://cockroachlabs.cloud/mcp
```

using:

```text
Authorization: Bearer <service-account-key>
mcp-cluster-id: <memoryir-cluster-id>
```

## Important Security Rule

Do **not** give the model unrestricted access to every MCP tool.

Our MCP client exposes only:

```text
list_databases
list_tables
get_table_schema
select_query
explain_query
show_statement
```

Do not expose:

```text
create_database
create_table
insert_rows
```

The managed MCP provides both read and write tools, and API-key permissions follow the service account's role, so our application should perform its own tool allowlisting on top.

---

# 19. Investigator Endpoint

```text
POST /api/forensics/{trace_id}
```

User asks:

> Why did T42 choose CockroachDB?

Investigator receives:

```text
You are MemoryIR Investigator.

Trace: T42

Use CockroachDB MCP to inspect:
- traces
- retrieval_runs
- retrieval_items
- generation_claims
- memory_edges
- intervention_runs

Determine:
1. what was retrieved
2. what the agent claimed
3. what interventions changed the decision
4. the ground lineage of influential derived memories
```

And produces:

```text
MEMORYIR FORENSIC REPORT

Trace T42

Decision
COCKROACHDB

Agent claimed
M7, M12

Retrieved
M7, M12, M16

Intervention results
M7 removed  → DYNAMODB
M12 removed → COCKROACHDB
M16 removed → COCKROACHDB

Finding
M7 was causally influential.
M12 was cited but had no measured effect.

M7 lineage
M2 ─┐
M3 ─┼─► M7
M4 ─┘

Ancestor intervention
M2 removed → DYNAMODB

Ground provenance
M2 → M7 → decision

Faithfulness
PARTIAL
```

This is an excellent Cockroach MCP demo.

---

# 20. Frontend: Only Five Screens

Do **not** build a generic admin dashboard.

## Screen 1 — Home

Very simple:

```text
┌─────────────────────────────────────────────────────┐
│ MEMORYIR                                            │
│                                                     │
│ Forensics for persistent AI memory                  │
│                                                     │
│ Which memories actually caused this decision?       │
│                                                     │
│ [ Launch Interactive Demo ]                         │
│                                                     │
│ CockroachDB Vector Index • Managed MCP • AWS        │
└─────────────────────────────────────────────────────┘
```

---

# 21. Screen 2 — Memory Lab

This shows why persistent memory matters.

```text
MEMORY LAB

Ground Memories

┌───────────────────┐
│ M1                │
│ User prefers ...  │
│ RAW • Generation 0│
└───────────────────┘

┌───────────────────┐
│ M2                │
│ System requires   │
│ multi-region ...  │
│ RAW • Generation 0│
└───────────────────┘

┌───────────────────┐
│ M3                │
│ Team wants ...    │
└───────────────────┘

        [ Consolidate ]

                ↓

┌─────────────────────────────┐
│ M7                          │
│ PostgreSQL-compatible...    │
│ CONSOLIDATED • Generation 1 │
└─────────────────────────────┘
```

And next to it show:

```text
M1 ─┐
M2 ─┼──► M7
M3 ─┘
```

React Flow is perfect for this.

---

# 22. Screen 3 — Agent Trace

This should be the main demo screen.

Three columns:

```text
┌──────────────┬─────────────────────┬───────────────────┐
│ RETRIEVAL    │ AGENT               │ CLAIMED           │
│              │                     │ PROVENANCE        │
│ #1 M7        │ Question            │                   │
│ 0.113        │ Which database?     │ M7 ██████████     │
│              │                     │ M12 ███████       │
│ #2 M12       │ Answer              │                   │
│ 0.181        │ CockroachDB         │                   │
│              │                     │                   │
│ #3 M16       │ Decision            │                   │
│ 0.226        │ COCKROACHDB         │                   │
└──────────────┴─────────────────────┴───────────────────┘

                   [ Investigate ]
```

---

# 23. Screen 4 — Causal Trace Explorer

Click **Investigate**.

Animation:

```text
Testing M7...
```

Then:

```text
REMOVE M7
COCKROACHDB → DYNAMODB       ⚠ FLIP
```

```text
REMOVE M12
COCKROACHDB → COCKROACHDB    no effect
```

```text
REMOVE M16
COCKROACHDB → COCKROACHDB    no effect
```

Then show:

```text
AGENT CLAIM                  MEASURED INFLUENCE

M7  ██████████               M7  ██████████

M12 ███████                  M12 ▏
```

That visual communicates the entire project in five seconds.

---

# 24. Expand M7

This should be the video money shot.

```text
                    DECISION
                       ▲
                       │
                      M7
                  ╱    │    ╲
                M1     M2     M3
                       ▲
                       │
                  true ground
                   influence
```

Then:

```text
Claimed provenance
M7 + M12

Measured retrieved influence
M7

Measured ground provenance
M2 → M7 → decision
```

---

# 25. Screen 5 — MCP Investigator

Make it look like a forensic console.

```text
MemoryIR Investigator
────────────────────────────────────────

Ask about this trace...

> Why was M7 influential?

Investigating CockroachDB...

✓ retrieval_items
✓ memory_edges
✓ intervention_runs
✓ generation_claims

M7 was retrieved at rank 1.

Removing M7 changed the decision from
COCKROACHDB → DYNAMODB.

M7 was consolidated from M1, M2 and M3.

Removing M2 and recomputing the lineage
caused the same decision flip.

Ground causal path:

M2 → M7 → Decision
```

Add small badges showing which MCP calls happened:

```text
MCP
select_query
select_query
get_table_schema
```

Judges then **see the MCP integration** instead of merely reading about it in the README.

---

# 26. Evaluation Screen

Do not make this huge.

Four scenario types:

```text
Direct memory
Proxy citation
One-hop consolidation
Multi-hop consolidation
```

Metrics:

```text
Causal Precision
Causal Recall
Proxy Citation Rate
Average Provenance Depth
Decision Flip Rate
Intervention Latency
```

Compare:

```text
Agent self-report
          vs
MemoryIR measured provenance
```

That is enough.

---

# 27. Evaluation Dataset

Create around **40–60 controlled cases**, not hundreds.

For example:

```text
10 direct
10 irrelevant citations
10 one-hop consolidated
10 two-hop consolidated
10 misleading proxy citations
```

Every case should contain a known expected decision.

Example:

```json
{
  "case_id": "multi_hop_07",
  "query": "Which deployment strategy should be used?",
  "expected_decision": "BLUE_GREEN",
  "causal_ground_memory": "M2",
  "derived_path": ["M2", "M7", "M11"]
}
```

Do not claim this is a benchmark.

Call it:

> **controlled evaluation suite**

That is accurate.

---

# 28. Backend Execution Pipeline

For each normal agent call:

```text
POST /query

1. Receive query
2. Create trace
3. Generate query embedding
4. Cockroach vector search
5. Write retrieval_run
6. Write retrieval_items
7. Construct model context
8. Call LLM
9. Parse structured decision
10. Parse claimed memory IDs
11. Write generation_claims
12. Complete trace
13. Return result
```

---

# 29. Intervention Pipeline

When the user clicks Investigate:

```text
TRACE T42
   │
   ├── retrieved M7
   │       │
   │       └─ rerun without M7
   │
   ├── retrieved M12
   │       │
   │       └─ rerun without M12
   │
   └── retrieved M16
           │
           └─ rerun without M16
```

For each:

```text
same query
same system prompt
same model
same temperature
same retrieved order
except target memory removed
```

Store every run.

---

# 30. Derived-Memory Pipeline

If M7 mattered:

```text
GET ancestry(M7)
```

Suppose:

```text
M1
M2
M3
```

Then:

```text
for ancestor in [M1,M2,M3]:

    remove ancestor
    recompute M7'
    replace M7 → M7'
    rerun decision
    store ancestor intervention
```

For multi-hop:

```text
M2 → M7 → M11
```

recompute topologically:

```text
remove M2

M7' = consolidate(M1,M3)

M11' = consolidate(M7', M8)

final_context =
    replace M11 with M11'

rerun
```

This is P0 for the **one-hop** case.

Multi-hop recomputation is P1 if time gets tight.

---

# 31. One Important Scientific Rule

Do not market:

```text
decision flip = definitive causality
```

Instead say:

> **interventional influence** or **counterfactual sensitivity**.

The intervention tells us:

> Under this controlled ablation, removing this memory changed the observed decision.

That is defensible.

MemoryIR can later develop stronger causal methodology in the paper.

---

# 32. LLM Abstraction

Make this interface:

```python
class ModelProvider:
    def generate(...):
        ...

    def embed(...):
        ...
```

Implement:

```text
BedrockProvider
MockProvider
```

Optionally later:

```text
OpenAIProvider
GeminiProvider
```

This matters because **the research architecture should not become tied to AWS just because the hackathon requires AWS**.

---

# 33. AWS Deployment

Hackathon version:

```text
                     Internet
                         │
                         ▼
               AWS Lambda Function URL
                         │
                ┌────────┴────────┐
                │                 │
             React UI          FastAPI
                                  │
                     ┌────────────┼───────────┐
                     │            │           │
                     ▼            ▼           ▼
                  Bedrock    CockroachDB    CRDB MCP
                               Cloud
```

This clearly satisfies the AWS deployment requirement.

---

# 34. Deployment Checklist

## CockroachDB

- [ ] Create CockroachDB Cloud organization
- [ ] Create **Basic** cluster
- [ ] Choose AWS region close to Lambda, ideally `us-east-1`
- [ ] Create database `memoryir`
- [ ] Create `memoryir_app` SQL user
- [ ] Grant only app DB privileges
- [ ] Execute `001_schema.sql`
- [ ] Enable/create vector index
- [ ] Test ANN query
- [ ] Set monthly resource limits
- [ ] Create dedicated MCP service account
- [ ] Scope MCP to MemoryIR cluster
- [ ] Store MCP API key server-side only
- [ ] Verify MCP `select_query`
- [ ] Verify MCP investigator cannot expose write tools through our client

---

# 35. AWS Checklist

- [ ] Create AWS account/project
- [ ] Pick one region
- [ ] Enable Bedrock model access if using Bedrock
- [ ] Create Lambda execution IAM role
- [ ] Grant only `bedrock:InvokeModel`
- [ ] Create Lambda
- [ ] Configure Function URL
- [ ] Set Lambda environment variables
- [ ] Add Cockroach connection string
- [ ] Add MCP key
- [ ] Add MCP cluster ID
- [ ] Set memory to ~512–1024 MB
- [ ] Set timeout ~30–60 sec
- [ ] Set reserved concurrency to 2–5
- [ ] Build React
- [ ] Copy `frontend/dist` into Lambda artifact
- [ ] `sam build`
- [ ] `sam deploy`
- [ ] Verify public URL

---

# 36. Backend P0 Task List

These must work before anything decorative:

- [ ] Database connection
- [ ] Schema migrations
- [ ] Insert raw memory
- [ ] Generate/store embedding
- [ ] Cockroach vector retrieval
- [ ] Retrieval logging
- [ ] Agent response generation
- [ ] Structured decision
- [ ] Claimed-memory output
- [ ] Store claims
- [ ] Consolidate memories
- [ ] Store `memory_edges`
- [ ] Recursive lineage query
- [ ] Leave-one-memory-out intervention
- [ ] Decision-flip detection
- [ ] Ancestor intervention
- [ ] Attribution report
- [ ] Managed MCP connectivity
- [ ] MCP forensic query
- [ ] Public AWS deployment

If all of that works, **we have a valid submission.**

---

# 37. Frontend P0 Task List

- [ ] Home
- [ ] Memory cards
- [ ] Add memories
- [ ] Consolidate button
- [ ] Lineage graph
- [ ] Query box
- [ ] Retrieved-memory ranking
- [ ] Agent answer
- [ ] Claimed attribution
- [ ] Investigate button
- [ ] Intervention results
- [ ] Ground provenance path
- [ ] MCP investigator
- [ ] Loading states
- [ ] Error states
- [ ] Demo reset button

---

# 38. P1 Items

Only after P0:

- [ ] Multi-hop `M2 → M7 → M11`
- [ ] Parallel interventions
- [ ] Evaluation screen
- [ ] 40–60 evaluation cases
- [ ] Faithfulness metrics
- [ ] MCP tool-call visualization
- [ ] Trace export JSON
- [ ] Demo presets
- [ ] Animated graph
- [ ] Latency metrics

---

# 39. P2 — Absolutely Disposable

Do **not** delay submission for:

- Authentication
- Teams
- User accounts
- Billing
- Fancy landing page
- Mobile optimization
- Multiple LLM providers
- WebSocket streaming
- Redis
- Background queue
- Kubernetes
- Multi-region deployment
- Huge benchmark
- Sophisticated RAG chunking
- PDF uploads
- General-purpose agent platform

They do not prove the idea.

---

# 40. Can We Really Do This for Free?

**Yes, the project can be designed for $0 out-of-pocket, particularly if eligible for the current new-account credits.**

There are a couple of nuances.

## CockroachDB

CockroachDB Basic currently starts at **$0/month** and includes **50 million RUs + 10 GiB storage free each month**. The Basic tier scales request consumption to zero when idle.

A new CockroachDB Cloud organization also currently starts with **$400 in trial credits**.

MemoryIR for the hackathon is likely to contain:

```text
< 10,000 memories
< 10,000 traces
tiny vectors
tiny JSON records
```

We are nowhere near 10 GiB.

Set a hard resource limit anyway.

---

# 41. AWS Lambda

AWS Lambda's current free tier includes:

- **1,000,000 requests/month**
- **400,000 GB-seconds/month**

Suppose MemoryIR gets:

```text
5,000 Lambda calls
512 MB
3 seconds average
```

Compute usage:

```text
0.5 GB × 3 sec × 5,000
= 7,500 GB-seconds
```

Free allowance:

```text
400,000 GB-seconds
```

So the hackathon workload would be a tiny fraction of Lambda's included allowance.

Because we are serving the React frontend from Lambda too, **we do not need another AWS hosting service.**

---

# 42. New AWS Account

AWS currently offers new customers **$100 in credits at sign-up and up to another $100**, for up to $200 total.

So if using a new eligible AWS account:

```text
Lambda         → free allowance
Bedrock        → promotional credits
CockroachDB    → free Basic/trial
Frontend       → Lambda
Vector DB      → CockroachDB
MCP            → CockroachDB
```

**$0 out-of-pocket is realistic.**

---

# 43. Bedrock Is the Only Caveat

Bedrock inference itself is metered.

So do not say:

> Bedrock is free.

It is not universally free.

With a new AWS account, promotional credits can cover the tiny hackathon workload.

There are extremely cheap models available. For example, the Bedrock pricing page lists low-cost models with pricing in fractions of a dollar per million tokens.

Even:

```text
1,000 agent generations

3,000 input tokens each
500 output tokens each
```

would still be very inexpensive for a small low-cost model.

The intervention engine is why prompts should stay compact—one trace may produce 5–10 model calls.

---

# 44. Cost-Safe Configuration

Actively protect against accidental billing:

```text
CockroachDB
────────────
Basic only
hard RU/storage resource limit
one cluster
single region

AWS
────
Lambda only for hosting
reserved concurrency = 2–5
short timeout
small memory allocation

Bedrock
───────
on-demand only
NO provisioned throughput
max output tokens capped
cheap model for evaluation
stronger model only for demo if needed
```

**Never enable Bedrock Provisioned Throughput.**

That is where the scary hourly/monthly numbers live.

---

# 45. Development vs Demo Cost Strategy

## Local Development

```text
FastAPI local
React local
CockroachDB Cloud Basic
Mock LLM or existing provider
```

Cost:

```text
~$0
```

## Evaluation

Use the cheapest acceptable model.

```text
40 cases
× 4 conditions
× maybe 3 repeats
```

Keep it controlled.

## Final Demo

Use the preferred stronger model if necessary.

Only perhaps 10–20 calls.

This prevents burning model credits while debugging CSS.

---

# 46. Security Model

For the app:

```text
Browser
  │
  │ no secrets
  ▼
Lambda
  │
  ├── DB credentials
  ├── MCP service key
  └── AWS role
```

Never:

```text
React ENV
   ↓
Cockroach password        ❌

React ENV
   ↓
MCP API key               ❌
```

All secrets stay server-side.

---

# 47. CockroachDB Security Decision

Use separate identities:

```text
memoryir_app
    ↓
normal SQL connection
    ↓
READ + WRITE application tables
```

and:

```text
memoryir_forensics
    ↓
Managed MCP
    ↓
READ operations exposed by our client
```

The application runtime should **not use MCP to perform normal storage operations**.

Cleaner architecture:

```text
Production memory path
Agent → SQL → CockroachDB

Forensic investigation path
Investigator → MCP → CockroachDB
```

This makes it obvious to judges why MCP is being used.

---

# 48. Demo Seed Scenario

Have **one deterministic scenario** always ready.

Ground memories:

```text
M1
"The team prefers PostgreSQL-compatible databases."

M2
"The deployment must survive regional failures."

M3
"The operations team wants a managed service."
```

Consolidate:

```text
M7

"The application should use a managed,
PostgreSQL-compatible database with
multi-region resilience."
```

Add distractor:

```text
M12

"The frontend team prefers TypeScript."
```

Ask:

> Which database architecture best satisfies the project requirements?

Agent:

```text
COCKROACHDB

Claimed:
M7 + M12
```

Intervene:

```text
-M7  → decision changes
-M12 → no change
```

Then:

```text
-M1 from M7 → still CockroachDB
-M2 from M7 → decision changes
-M3 from M7 → still CockroachDB
```

MemoryIR:

```text
CLAIMED
M7 + M12

MEASURED
M7

GROUND
M2 → M7 → Decision
```

**That is the three-minute video.**

---

# 49. Video Structure

## 0:00–0:20

Problem.

> Agents increasingly summarize old memories into new memories. When they explain a decision, they may cite the summary rather than the underlying memory that actually drove it.

## 0:20–0:45

CockroachDB memory layer.

Show:

```text
M1 M2 M3 → M7
```

and vector retrieval.

## 0:45–1:15

Agent decision.

```text
Claims M7 + M12.
```

## 1:15–1:50

MemoryIR interventions.

```text
remove M7 → flip
remove M12 → unchanged
```

## 1:50–2:15

Derived-memory investigation.

```text
M2 → M7 → decision
```

## 2:15–2:40

Managed MCP investigator.

Natural-language forensic question.

Show actual MCP query calls.

## 2:40–2:55

Architecture:

```text
AWS Lambda
Bedrock
CockroachDB Vector
CockroachDB MCP
```

## 2:55–3:00

> **MemoryIR: don't just ask an agent what it remembers. Verify what actually mattered.**

Done.

---

# 50. Schedule From Tonight to Submission

Since it is **Wednesday, August 12, 2026** and submissions close **Tuesday, August 18, 2026 at 5:00 PM EDT**, use this schedule:

| Date | Deliverable |
|---|---|
| **Aug 12 night** | Repo, Cockroach cluster, complete SQL schema, vector index |
| **Aug 13** | Memory CRUD + embeddings + vector retrieval + trace logging |
| **Aug 14** | Consolidation + lineage DAG + normal agent |
| **Aug 15** | Direct interventions + ancestor recomputation |
| **Aug 16** | React trace explorer + graph + MCP investigator |
| **Aug 17** | AWS deploy + controlled evaluation + bug fixes |
| **Aug 18 AM** | README, architecture graphic, demo video, Devpost |
| **Aug 18 ~2 PM** | Freeze submission; no major coding after this |

Do **not** aim for 4:59 PM.

---

# 51. Definition of Done

Do not call MemoryIR hackathon-ready until this exact sequence works on the public URL:

```text
[1] Add raw memories
           ↓
[2] embeddings stored in CockroachDB
           ↓
[3] consolidate memories
           ↓
[4] lineage edges visible
           ↓
[5] query agent
           ↓
[6] Cockroach vector index retrieves memories
           ↓
[7] agent returns decision + claimed provenance
           ↓
[8] MemoryIR removes each retrieved memory
           ↓
[9] decision changes / doesn't change
           ↓
[10] derived influential memory expanded
           ↓
[11] ancestor removed + descendant recomputed
           ↓
[12] ground provenance produced
           ↓
[13] MCP investigator independently inspects trace
           ↓
[14] report displayed
```

If those **14 things work**, we have MemoryIR.

Everything else is polish.

---

# 52. Cost Target

For the actual hackathon build, budget:

```text
CockroachDB              $0
Lambda                    $0
Frontend hosting          $0   (served by Lambda)
MCP                       $0   within Cockroach plan
Bedrock                credits / cents
────────────────────────────────────────
Expected out-of-pocket    $0 with eligible credits
```

CockroachDB Basic's current free allocation is **50M RUs + 10 GiB/month**.

Lambda's free allocation is **1M requests + 400k GB-seconds/month**.

New AWS customers can currently receive promotional credits.

So **cost is not the main risk. Scope is.**

The thing to protect at all costs is the chain:

> **vector retrieval → claimed attribution → intervention → derived-memory lineage → ground provenance → MCP investigation**

That is the actual MemoryIR contribution.

---

# 53. Final Build Priorities

If time gets tight, preserve these in this order:

1. CockroachDB persistent memory schema
2. Vector retrieval
3. Consolidation lineage
4. Agent decision + claimed provenance
5. Direct leave-one-memory-out interventions
6. One-hop ancestor recomputation
7. Attribution report
8. MCP forensic investigator
9. AWS public deployment
10. Minimal React UI
11. Controlled evaluation suite
12. Multi-hop recomputation
13. Polish and animations

The hackathon submission should remain fully identifiable as **MemoryIR**, not a generic RAG dashboard or a generic prompt-injection demo.

The product message should stay:

> **MemoryIR — Forensics for persistent AI memory.**
>
> **Don't just ask an agent what it remembers. Verify what actually mattered.**
