# MemoryIR

**Before an AI agent acts on what it remembers, prove that memory actually caused the decision.**

MemoryIR is a causal provenance firewall for persistent agent memory. It sits
between "the agent retrieved a memory" and "the agent is allowed to act,"
and it answers one question with evidence instead of trust: *if this memory
were removed, would the decision change?*

Built for the [CockroachDB x AWS Hackathon](https://cockroachdb-ai.devpost.com/).

---

## This is not a hypothetical

Persistent agent memory is already a live attack surface, in production systems, this year.

- **SpAIware (2024)** — security researcher Johann Rehberger showed that a
  single indirect prompt injection, delivered through a webpage ChatGPT
  merely *read*, could write a persistent instruction into ChatGPT's
  long-term memory. It survived across sessions and quietly exfiltrated
  data from every future conversation, invisible to the user.
  [(Details)](https://thehackernews.com/2024/09/chatgpt-macos-flaw-couldve-enabled-long.html)
- **EchoLeak / CVE-2025-32711 (2025)** — a zero-click prompt injection in
  Microsoft 365 Copilot, triggered by nothing more than a crafted email
  landing in an inbox. No click, no download, no user action. Copilot
  read the email, treated its contents as trusted context, and leaked
  internal data to an attacker. CVSS 9.3. The first documented case of
  prompt injection weaponized for real data exfiltration in a production
  LLM system.
  [(Details)](https://thehackernews.com/2025/06/zero-click-ai-vulnerability-exposes.html)
- **MemGhost (2026)** — researchers planted a false, persistent memory into
  a personal AI agent (OpenClaw) using a single ordinary email. The
  planted memory survived across sessions and silently steered the
  agent's later answers in **56 out of 56** test cases.
  [(Details)](https://thehackernews.com/2026/07/new-memghost-attack-plants-persistent.html)

Three different products, three different vendors, one shared failure mode:
**the agent trusted that a memory existing in its store meant the memory
was safe to act on.** None of these systems asked the harder question —
not "what did the agent retrieve," but "what actually caused the agent to
decide this."

That is the gap MemoryIR closes, at the moment it matters most: right
before the agent is about to write to production.

---

## The demo, end to end

An AI DevOps agent is asked to change the production database
architecture for customer orders:

```text
customer_orders.primary_database = POSTGRES_SINGLE_REGION
```

On the surface this looks reasonable — the agent has a memory saying the
team prefers PostgreSQL-compatible databases. But the agent also holds a
production policy memory (`M2`, "the deployment must survive regional
failures"), which was later consolidated into a derived memory (`M7`,
"use a managed, multi-region-resilient PostgreSQL-compatible database").

MemoryIR doesn't accept the agent's citation at face value. It runs the
intervention:

1. Remove `M7`, rerun the agent → decision flips.
2. Remove distractor memories (`M12`, `M16`) → decision doesn't move.
3. `M7` is influential. Walk its derivation lineage back to its ground
   ancestor: `M2 -> M7 -> decision`.
4. The proposed single-region write directly contradicts the causal
   memory path. **Verdict: Blocked.**

The forensic layer, backed by CockroachDB Managed MCP, lets anyone ask
*"why was M7 influential?"* after the fact and get the trace, not a guess.

### Product screenshots

The screenshots below were captured from the local demo using seeded dummy
trace data and the mock model path, so the full flow is reproducible
without live credentials.

#### Security dashboard

![MemoryIR security dashboard with guarded and flagged agent actions](docs/screenshots/security-dashboard.png)

#### Protected action blocked

![MemoryIR protected action review blocking a single-region database write](docs/screenshots/protected-action-blocked.png)

#### Causal trace and provenance

![MemoryIR agent trace showing retrieval, attribution metrics, interventions, and M2 to M7 provenance](docs/screenshots/agent-trace-provenance.png)

#### Forensic investigator

![MemoryIR forensic investigator showing MCP calls and causal memory report](docs/screenshots/forensic-investigator.png)

### What MemoryIR actually produced

SpAIware, EchoLeak, and MemGhost all exploited the same gap: the system
trusted that a memory being *retrieved or cited* meant it was *causally
responsible*. That's exactly what MemoryIR's attribution engine measures
directly. Below is real, reproducible output — not a mockup — from
running this scenario through MemoryIR's own pipeline (`MockProvider`,
no live credentials needed):

```json
{
  "decision": "COCKROACHDB",
  "claimed_memories": ["M7", "M12"],
  "retrieved_memories": ["M7", "M12", "M16"],
  "influential_memories": ["M7"],
  "claim_retrieval_precision": 1.0,
  "causal_precision": 0.5,
  "causal_recall": 1.0,
  "proxy_citation_rate": 0.5,
  "average_provenance_depth": 1.0,
  "ground_provenance": [
    {
      "ancestor": "M2",
      "retrieved": "M7",
      "depth": 1,
      "decision_changed": true,
      "path": ["M2", "M7", "Decision"]
    }
  ]
}
```

Read this as a claim about the **agent**, not about MemoryIR: the agent
cited two memories as its reasons (`M7`, `M12`), but only one of them
actually drove the decision. That's what `causal_precision: 0.5` and
`proxy_citation_rate: 0.5` mean — half of the agent's own story was a
plausible-looking proxy citation, exactly the kind of harmless derived
memory SpAIware and MemGhost rode in on.

MemoryIR's own performance is the other number: `causal_recall: 1.0` —
of every memory that *actually* changed the decision, it found 100% of
them, zero missed. It doesn't stop at "the agent used a real memory." It
walks past the proxy (`M12`) to the one memory that truly moved the
decision (`M7`), and one hop further to its real ground cause (`M2`).

Reproduce it yourself:

```bash
cd backend
python -c "
from app.config import Settings
from app.services.container import build_services

services = build_services(Settings(provider='mock', database_backend='memory'))
trace_id, result, retrieved = services.query_engine.query(
    query='Which database architecture best satisfies the project requirements?',
    top_k=3,
)
services.intervention_engine.run(trace_id)
print(services.attribution.report(trace_id).model_dump_json(indent=2))
"
```

### Controlled evaluation suite: 48 scenarios, run for real

One scenario is a story. To check the mechanism itself, we built a harness
(`eval/run_causal_eval.py`) that takes the 48 structured cases in
`eval/cases/` — direct citations, one-hop derivations, multi-hop
derivations, and proxy-citation patterns — and drives every one through
the *actual* production classes (`QueryEngine`, `InterventionEngine`,
`AttributionEngine`), not a mockup. Each case only defines structure
(which memory is the true ground cause, how many derivation hops, what
the agent claims); the pipeline does the rest.

```bash
python eval/run_causal_eval.py
```

Real output:

| Scenario type | Cases | Decision correct | Proxy citation correctly flagged | True root ancestor found |
|---|---|---|---|---|
| Direct memory (0 hops) | 12 | 12/12 | 0/12 (correctly — nothing to flag) | n/a |
| One-hop consolidation | 12 | 12/12 | 12/12 | 12/12 |
| Proxy citation (1 hop) | 12 | 12/12 | 12/12 | 12/12 |
| Multi-hop consolidation (2 hops) | 12 | 12/12 | 12/12 | **0/12** |

The decision layer is correct across all 48 cases, and every one-hop and
direct case resolves ground provenance exactly right. The honest gap: at
two derivation hops, MemoryIR currently identifies the immediate derived
parent as the cause but doesn't yet walk past it to the true root
ancestor — it stops one hop short. This is a real, measured result, not a
guess, and it's the same limitation already called out in
[What's Next](#whats-next): extending ancestor ablation from one hop to
recursive multi-hop recomputation is the next concrete piece of work, not
a hypothetical one.

---

## Architecture

```mermaid
flowchart TD
    U[Protected Action Request] --> EMB[Bedrock Titan Embeddings]
    EMB --> RET[CockroachDB Vector Search]
    RET -->|"retrieves M7, M12, M16"| GEN[Bedrock Agent Model]
    GEN -->|"decision + claimed memory attribution"| TRACE[(CockroachDB<br/>traces / retrieval_items /<br/>generation_claims)]

    TRACE --> IE[Intervention Engine]
    IE -->|"leave-one-memory-out, rerun"| FLIP{Decision flips?}
    FLIP -->|"yes: M7"| LIN[Lineage Walk]
    FLIP -->|"no: M12, M16 discarded"| DROP[Not causal]
    LIN -->|"memory_edges"| GROUND["Ground ancestor: M2"]

    GROUND --> VERDICT{"Conflicts with<br/>protected path?"}
    VERDICT -->|yes| BLOCK[🚫 Blocked]
    VERDICT -->|no| ALLOW[✅ Allowed]

    TRACE -.-> MCP[CockroachDB Managed MCP]
    MCP -.->|"forensic Q&A: why was M7 influential?"| INVESTIGATOR[Forensics Console]

    style BLOCK fill:#7f1d1d,color:#fff
    style ALLOW fill:#14532d,color:#fff
    style GROUND fill:#78350f,color:#fff
```

```text
Browser → AWS API Gateway → AWS Lambda (React static app + FastAPI backend)
                                   |
                                   ├── Amazon Bedrock (Titan embeddings, Nova Micro decisions)
                                   └── CockroachDB Cloud (memory, traces, lineage, interventions)
                                              └── CockroachDB Managed MCP (forensic investigator)
```

---

## What actually runs

1. Receive a protected action request.
2. Embed the query with Amazon Bedrock Titan Text Embeddings.
3. Retrieve persistent memories from CockroachDB via vector search.
4. Call a Bedrock model for a structured decision + claimed memory
   attribution.
5. Persist the trace, retrieval run, retrieved memories, and generation
   claims in CockroachDB.
6. Run counterfactual leave-one-memory-out interventions.
7. For influential derived memories, walk the memory DAG and rerun
   ancestor interventions.
8. Generate a MemoryIR attribution report: causal precision, recall,
   proxy-citation rate, ground provenance depth.
9. Block or allow the action based on causal evidence, not self-report.
10. Serve independent forensic Q&A over the same live memory database via
    CockroachDB Managed MCP.

## CockroachDB tools used

- **Distributed Vector Indexing** — the persistent memory layer itself.
  Embeddings, semantic retrieval, and transactional trace/provenance data
  live in one database instead of being split across a vector store and
  an app database.
- **CockroachDB Cloud Managed MCP Server** — the forensic investigator
  queries trace tables, generation claims, memory edges, retrieval items,
  and intervention results independently of the app's own read path,
  proving the memory layer is auditable, not just used as storage.

## AWS services used

- **AWS Lambda** — one Lambda serving both `/api/*` (FastAPI) and the
  static React build.
- **Amazon Bedrock** — Titan Text Embeddings V2 (256-dim) + Nova Micro for
  agent decisions.
- **Amazon S3** — Lambda deployment artifact storage.
- **Amazon API Gateway** — public, rate-gated HTTP endpoint in front of
  Lambda.

---

## Run it locally

```bash
make backend-install
make frontend-install
make dev-backend
make dev-frontend
```

Default mode uses in-memory storage and a `MockProvider`, so the full flow
works with zero secrets:

`M1/M2/M3 -> M7 -> decision -> interventions -> ground provenance -> MCP console`

## Live credentials

Put real credentials in a local `creds.env` (gitignored, never committed).
The backend loads `creds.env` first, then `.env`. See `.env.example` for
the full variable list — provider, database backend, AWS region, Bedrock
model IDs, MCP endpoint/key/cluster.

## Verify

```bash
make test-backend
cd frontend && npm run build
python eval/run_eval.py
```

## Deploy

No AWS or SAM CLI required. Packages FastAPI for Lambda, uploads to S3,
and creates/updates the Lambda execution role, function, and public HTTP
API Gateway endpoint.

```powershell
cd C:\FSU\projects\MemIR\hackathon
make build-frontend
python backend/scripts/copy_frontend.py
python deploy_aws.py --direct
```

The public endpoint is request-gated by default
(`MEMORYIR_API_RATE_LIMIT`, `MEMORYIR_API_BURST_LIMIT` in `creds.env`).

---

## What's Next

- Extend ancestor ablation from one hop to recursive multi-hop
  recomputation, closing the gap measured above.
- Add explicit injected-memory seeding for live red-team demos.
- Add policy/trust labels to memory sources and fail closed when a
  protected action's causal path is unknown or untrusted.
- Add trace export for auditors and memory-risk dashboards across
  agents/teams.

## License

MIT — see `LICENSE`.
