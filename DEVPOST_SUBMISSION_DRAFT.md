# MemoryIR: Persistent Prompt Injection Firewall for Agentic Memory

## Tagline

MemoryIR stops sleeper prompt injections in agent memory before they become production actions.

## Short Description

AI agents are starting to write code, change infrastructure, operate databases, and take actions that affect real users. The dangerous part is not only what appears in the current prompt. A malicious instruction can be stored in long-term memory, summarized into a derived memory, retrieved days later, and quietly steer an autonomous action.

MemoryIR is a causal provenance layer for persistent agent memory. Before an agent modifies critical systems, MemoryIR asks: which memories actually caused this decision? It retrieves the agent's memory from CockroachDB, records the claimed memory attribution, runs counterfactual interventions, traces derived memories back to their ancestors, and blocks actions that depend on unsafe or protected memory paths.

## The Demo Use Case

An AI DevOps agent is asked to update the production database architecture for customer orders. This is the kind of agent that might normally have permission to open pull requests, edit deployment config, or call an internal database-change workflow.

The attack model is a persistent prompt injection: a malicious or stale memory tries to push the agent toward a single-region database change. The current demo shows the guardrail side of the story. Even when the agent has long-term memory that makes a database change look reasonable, MemoryIR checks the actual causal memory path before the write is allowed.

The attempted write is:

```text
customer_orders.primary_database = POSTGRES_SINGLE_REGION
```

That write sounds plausible because a memory says the team prefers PostgreSQL-compatible databases. But the agent also has a critical production policy stored in persistent memory:

```text
M2: The deployment must survive regional failures.
```

That policy was later consolidated into a derived memory:

```text
M7: The application should use a managed, PostgreSQL-compatible database with multi-region resilience.
```

Without MemoryIR, a compromised or incomplete memory trail can turn into a bad production change. With MemoryIR, the agent's decision is not trusted at face value. MemoryIR runs interventions and proves:

```text
M2 -> M7 -> Decision
```

Because the requested single-region write conflicts with the causal memory path, MemoryIR blocks the action before customer data is touched.

## What It Does

MemoryIR provides a forensic guardrail for agent memory:

- Stores raw, consolidated, and derived memories in CockroachDB.
- Uses CockroachDB vector search to retrieve semantically relevant memories.
- Logs every agent trace, retrieval item, generated decision, and claimed memory attribution.
- Runs leave-one-memory-out interventions over retrieved memories.
- Recomputes derived-memory ancestry to identify the ground memory that actually changed the decision.
- Produces an attribution report with causal precision, recall, proxy citation rate, and ground provenance depth.
- Uses CockroachDB Managed MCP as a forensic investigator to inspect traces, retrievals, claims, memory edges, and intervention runs.
- Blocks protected actions when the causal memory path reveals an unsafe or policy-sensitive influence.

## Why This Matters

Prompt injection is usually discussed as a single-chat problem. Agentic memory makes it more dangerous.

A bad instruction can persist after the original conversation is gone. It can be embedded, retrieved, summarized, merged with trusted memories, and cited indirectly through a harmless-looking derived memory. The agent may say it relied on the summary, but the real cause may be an older injected or policy-sensitive memory.

MemoryIR addresses this gap by measuring interventional influence instead of accepting the agent's self-report. It does not merely ask, "what did the agent retrieve?" It asks, "what changed the decision when removed?"

## How We Built It

The application is a React and FastAPI system deployed on AWS Lambda.

The backend pipeline is:

1. Receive a protected action request.
2. Generate a query embedding with Amazon Bedrock Titan Text Embeddings.
3. Retrieve persistent memories from CockroachDB using vector search.
4. Call an Amazon Bedrock model to produce a structured decision and claimed memory attribution.
5. Store the trace, retrieval run, retrieved memories, and generation claims in CockroachDB.
6. Run counterfactual memory ablations.
7. For influential derived memories, inspect the memory DAG and rerun ancestor interventions.
8. Generate a MemoryIR attribution report.
9. Block or allow the action based on causal evidence.
10. Use CockroachDB Managed MCP for natural-language forensic inspection of the same live memory database.

## CockroachDB Tools Used

### CockroachDB Distributed Vector Indexing

CockroachDB is the persistent memory layer. MemoryIR stores embeddings directly in CockroachDB and retrieves relevant memories through vector search. This keeps semantic memory and operational trace data in the same transactional database instead of splitting memory across a separate vector store.

Used for:

- Agent memory embeddings.
- Semantic retrieval for each agent trace.
- Retrieval provenance through persisted retrieval runs and retrieval items.
- Demo retrieval order such as `M7, M12, M16`.

### CockroachDB Cloud Managed MCP Server

The forensic investigator uses CockroachDB Managed MCP to inspect the memory system from the outside. It queries trace tables, generation claims, memory edges, retrieval items, and intervention results to explain why a memory mattered.

Used for:

- Schema inspection.
- Read-only trace investigation.
- Independent forensic questions like "Why was M7 influential?"
- Demonstrating that the memory layer is auditable, not just used as app storage.

## AWS Services Used

### AWS Lambda

The full FastAPI backend and React production build are packaged into a Lambda deployment. Lambda handles both `/api/*` routes and static frontend assets.

### Amazon Bedrock

Bedrock powers both embeddings and the agent decision step:

- Titan Text Embeddings V2 for 256-dimensional memory embeddings.
- Amazon Nova Micro for low-cost agent decision generation during testing.

### Amazon S3

S3 stores deployment artifacts for the Lambda package.

### Amazon API Gateway

The public demo endpoint is exposed through an HTTP API Gateway route to Lambda. The live endpoint is request-gated with low throttling limits for cost control during judging.

## Technical Architecture

```text
Browser
  |
  v
AWS API Gateway
  |
  v
AWS Lambda
  |-- React static app
  |-- FastAPI backend
  |
  |-- Amazon Bedrock
  |     |-- Titan embeddings
  |     |-- Nova Micro decision model
  |
  v
CockroachDB Cloud
  |-- memories
  |-- memory_edges
  |-- traces
  |-- retrieval_runs
  |-- retrieval_items
  |-- generation_claims
  |-- intervention_runs
  |
  v
CockroachDB Managed MCP
  |-- forensic schema inspection
  |-- trace investigation
```

## Live Demo Script

### 0:00-0:20: Problem

"Prompt injection does not end when the chat ends. In memory-enabled agents, malicious or stale instructions can persist, get summarized, and later influence real production actions."

### 0:20-0:45: Risky Action

Open **Protected Action**.

Show the attempted mutation:

```text
customer_orders.primary_database = POSTGRES_SINGLE_REGION
```

Explain that this is an AI DevOps agent trying to modify production customer database configuration.

### 0:45-1:15: Agent Decision

Click **Simulate Risky Write**.

The agent retrieves memories from CockroachDB and returns:

```text
Decision: COCKROACHDB
Retrieved: M7, M12, M16
```

### 1:15-1:55: MemoryIR Guard

Click **Run MemoryIR Guard**.

MemoryIR removes retrieved memories and reruns the decision. Removing `M7` flips the decision. Removing distractors like `M12` does not.

### 1:55-2:25: Ground Provenance

MemoryIR follows the derived-memory lineage:

```text
M2 -> M7 -> Decision
```

It identifies `M2`, the regional-failure policy, as the ground causal memory.

### 2:25-2:45: Block

Show verdict:

```text
Blocked
```

The single-region write is rejected because it conflicts with the causal production-resilience memory path.

### 2:45-3:00: Forensics

Open **Forensics** and ask:

```text
Why was M7 influential?
```

Show CockroachDB Managed MCP calls and the trace evidence.

Closing line:

"MemoryIR does not just ask an agent what it remembers. It verifies what actually mattered before the agent acts."

## Judging Criteria Alignment

### Agentic Memory Design

CockroachDB is the core memory system, not an add-on. It stores long-term memories, derived-memory lineage, embeddings, retrieval traces, generation claims, and intervention results. The agent acts based on this persistent memory, and MemoryIR verifies that memory before allowing a protected action.

### Technical Implementation

The project uses two CockroachDB AI tools directly:

- Distributed vector indexing for memory retrieval.
- Managed MCP for forensic investigation.

It also uses AWS Lambda, Amazon Bedrock, S3, and API Gateway for a deployable agent environment.

### Real-World Impact

The use case is production safety for autonomous agents. As agents gain permission to modify infrastructure, databases, tickets, code, and customer workflows, persistent memory becomes part of the security boundary. MemoryIR helps prevent memory-based prompt injections and stale-memory mistakes from becoming real-world actions.

### Production Readiness

The design keeps secrets server-side, records audit-friendly traces, stores provenance in CockroachDB, uses low-cost request gating, and separates normal memory storage from MCP forensic inspection. The system can fail closed for protected actions when causal evidence is missing or suspicious.

### Creativity and Originality

Most RAG demos retrieve memory and generate an answer. MemoryIR treats memory as something that must be audited, stress-tested, and causally verified before an agent acts. The core idea is a provenance firewall for agentic memory.

## What We Are Proud Of

- Turning persistent prompt injection from an abstract risk into a concrete blocked-action demo.
- Showing a full memory chain from raw policy memory to derived memory to final decision.
- Measuring counterfactual sensitivity instead of trusting the model's citation.
- Using CockroachDB as both vector memory and transactional forensic ledger.
- Integrating Managed MCP so judges can see independent trace investigation.

## Challenges

- Making causal memory influence simple enough to explain in under three minutes.
- Keeping Bedrock usage low while still supporting realistic agent behavior.
- Packaging frontend, backend, and agent runtime into a compact Lambda deployment.
- Distinguishing retrieved memory, claimed memory, influential memory, and ground causal memory in the UI.

## What We Learned

Persistent memory changes the threat model for AI agents. A prompt injection can become durable state, and durable state can influence actions long after the original attack. Standard citation or retrieval logs are not enough because they show correlation, not interventional influence.

We also learned that CockroachDB is a strong fit for this problem because memory needs both semantic retrieval and transactional provenance. Vector search, memory DAGs, claims, traces, and interventions can live in one auditable system of record.

## What's Next

- Add explicit injected-memory seeding for live red-team demos.
- Add policy labels and trust labels to memory sources.
- Fail closed when protected actions have unknown or untrusted causal paths.
- Expand from one-hop derived-memory interventions to deeper multi-hop recomputation.
- Add trace export for auditors.
- Add dashboards for memory-risk trends across agents and teams.

## Devpost Submission Checklist

- Public open-source repository: TODO
- Open-source license at repository root: TODO
- Functional demo app URL: TODO, redeploy with `python deploy_aws.py --skip-build --direct`
- Public video under 3 minutes: TODO
- CockroachDB tools used and how: Distributed Vector Indexing and Managed MCP
- AWS services used and how: Lambda, Bedrock, S3, API Gateway
- Architecture diagram: Included above as text; optional image still recommended
- Feedback on CockroachDB AI tools: TODO, optional

## One-Liner Options

- "MemoryIR stops sleeper prompt injections in agent memory before they become production actions."
- "Before agents write to production, MemoryIR asks: what memory made you do that?"
- "Do not just ask an agent what it remembers. Verify what actually mattered."
- "MemoryIR is a provenance firewall for persistent AI memory."

## Source Notes

This draft is aligned to the CockroachDB x AWS Hackathon requirements on Devpost:

- https://cockroachdb-ai.devpost.com/
