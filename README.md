# MemoryIR

A causal provenance layer for persistent agent memory. Before an agent
modifies critical systems, MemoryIR asks: which memories actually caused
this decision? It retrieves the agent's memory from CockroachDB, records
the claimed memory attribution, runs counterfactual interventions, traces
derived memories back to their ancestors, and blocks actions that depend
on unsafe or protected memory paths.

Built for the CockroachDB x AWS Hackathon
(https://cockroachdb-ai.devpost.com/).

## Why

A malicious or stale instruction can be stored in an agent's long-term
memory, summarized into a derived memory, retrieved days later, and
quietly steer an autonomous action. Standard citation/retrieval logs only
show correlation ("the agent retrieved memory X"), not whether X actually
caused the decision. MemoryIR measures *interventional* influence instead
of trusting the agent's self-report: it asks "what changed the decision
when removed?" rather than "what did the agent say it used?"

## Demo Use Case

An AI DevOps agent is asked to update the production database
architecture for customer orders. The attempted write is:

```text
customer_orders.primary_database = POSTGRES_SINGLE_REGION
```

That looks plausible on its own, but the agent also holds a critical
production policy in persistent memory (`M2`), later consolidated into a
derived memory (`M7`) requiring multi-region resilience. MemoryIR runs
leave-one-memory-out interventions, finds that removing `M7` flips the
decision, traces `M7` back to its causal ancestor `M2`, and blocks the
single-region write because it conflicts with that causal path.

## Architecture

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

Backend pipeline:

1. Receive a protected action request.
2. Generate a query embedding with Amazon Bedrock Titan Text Embeddings.
3. Retrieve persistent memories from CockroachDB using vector search.
4. Call an Amazon Bedrock model to produce a structured decision and
   claimed memory attribution.
5. Store the trace, retrieval run, retrieved memories, and generation
   claims in CockroachDB.
6. Run counterfactual memory ablations.
7. For influential derived memories, inspect the memory DAG and rerun
   ancestor interventions.
8. Generate a MemoryIR attribution report.
9. Block or allow the action based on causal evidence.
10. Use CockroachDB Managed MCP for natural-language forensic inspection
    of the same live memory database.

## CockroachDB Tools Used

- **Distributed Vector Indexing** — persistent memory embeddings and
  semantic retrieval for each agent trace, stored alongside the
  transactional trace/provenance data in the same database.
- **CockroachDB Cloud Managed MCP Server** — the forensic investigator
  queries trace tables, generation claims, memory edges, retrieval
  items, and intervention results through Managed MCP to explain why a
  memory mattered, independent of the app's own storage path.

## AWS Services Used

- **AWS Lambda** — packages the FastAPI backend and React production
  build together; serves both `/api/*` and static frontend assets.
- **Amazon Bedrock** — Titan Text Embeddings V2 (256-dim) for memory
  embeddings, Amazon Nova Micro for agent decision generation.
- **Amazon S3** — stores the Lambda deployment artifact.
- **Amazon API Gateway** — public HTTP endpoint in front of Lambda,
  request-gated for cost control.

## Local Demo

```bash
make backend-install
make frontend-install
make dev-backend
make dev-frontend
```

The default mode uses in-memory storage and `MockProvider`, so the demo
flow works without secrets:

`M1/M2/M3 -> M7 -> decision -> interventions -> ground provenance -> MCP console`

## Credentials

Put live credentials in `creds.env` in this folder (gitignored, never
committed). The backend loads `creds.env` first and then `.env` if
present. See `.env.example` for the full variable list. Expected live
keys:

- `MEMORYIR_PROVIDER=bedrock`
- `MEMORYIR_DATABASE_BACKEND=cockroach`
- `DATABASE_URL`
- `AWS_REGION`
- `BEDROCK_EMBED_MODEL_ID`
- `BEDROCK_AGENT_MODEL_ID`
- `MCP_API_KEY`
- `MCP_CLUSTER_ID`

## Verification

```bash
make test-backend
cd frontend && npm run build
python eval/run_eval.py
```

## Presenter Flow

Open the public demo and use **Protected Action**:

1. **Simulate Risky Write** creates an agent trace for:
   `customer_orders.primary_database = POSTGRES_SINGLE_REGION`
2. **Run MemoryIR Guard** runs causal interventions.
3. The expected verdict is **Blocked** because protected memory `M2 -> M7`
   causally supports `COCKROACHDB`, so the single-region write is rejected.
4. **Open Trace** shows retrieval, claims, interventions, and ground provenance.
5. **Open Forensics** is available after the guard runs for MCP-backed questions.

## Deploy

The working deployment path does not require the AWS or SAM CLIs. It packages
the FastAPI app for Lambda, uploads the artifact to S3, creates or updates the
Lambda execution role, Lambda function, and public HTTP API Gateway endpoint.

```powershell
cd C:\FSU\projects\MemIR\hackathon
make build-frontend
python backend/scripts/copy_frontend.py
python deploy_aws.py --direct
```

The public API Gateway stage is request-gated by default:

- `MEMORYIR_API_RATE_LIMIT=1.0`
- `MEMORYIR_API_BURST_LIMIT=5`

Override those in `creds.env` before deployment if the demo needs more room.

## License

MIT — see `LICENSE`.
