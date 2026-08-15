# MemoryIR Hackathon

Forensics for persistent AI memory, implemented from
`MemoryIR_End_to_End_Hackathon_Blueprint.md`.

## Local Demo

```bash
make backend-install
make frontend-install
make dev-backend
make dev-frontend
```

The default mode uses in-memory storage and `MockProvider`, so the demo flow
works without secrets:

`M1/M2/M3 -> M7 -> decision -> interventions -> ground provenance -> MCP console`

## Credentials

Put live credentials in `creds.env` in this folder. The backend loads
`creds.env` first and then `.env` if present.

Expected live keys:

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
