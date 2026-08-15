const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export type Memory = {
  memory_id: string;
  display_id: string;
  agent_id: string;
  session_id?: string | null;
  source_id?: string | null;
  memory_type: string;
  content: string;
  generation: number;
  metadata: Record<string, unknown>;
  created_at?: string | null;
};

export type RetrievedMemory = Memory & {
  retrieval_rank: number;
  vector_distance: number;
};

export type ClaimedMemory = {
  memory_id: string;
  display_id: string;
  claim_type: string;
  claimed_rank: number;
  explanation: string;
};

export type QueryResult = {
  trace_id: string;
  answer: string;
  decision: string;
  retrieved: RetrievedMemory[];
  claimed: ClaimedMemory[];
};

export type Intervention = {
  intervention_id: string;
  trace_id: string;
  intervention_type: string;
  target_memory_id?: string | null;
  target_display_id?: string | null;
  target_depth: number;
  baseline_decision?: string | null;
  counterfactual_decision?: string | null;
  decision_changed: boolean;
  effect_score?: number | null;
  latency_ms?: number | null;
};

export type AttributionReport = {
  trace_id: string;
  decision?: string | null;
  claimed_memories: string[];
  retrieved_memories: string[];
  influential_memories: string[];
  claim_retrieval_precision: number;
  causal_precision: number;
  causal_recall: number;
  proxy_citation_rate: number;
  average_provenance_depth: number;
  ground_provenance: Array<Record<string, unknown>>;
};

export type ForensicResponse = {
  trace_id: string;
  question: string;
  answer: string;
  mcp_calls: Array<Record<string, unknown>>;
  mode: string;
};

export type TraceSummary = {
  trace_id: string;
  user_query: string;
  decision?: string | null;
  status: string;
  started_at: string;
  completed_at?: string | null;
  guarded: boolean;
  flagged: boolean;
  causal_precision?: number | null;
  causal_recall?: number | null;
  proxy_citation_rate?: number | null;
  ground_path?: string | null;
};

export type DashboardSummary = {
  total_actions: number;
  guarded_actions: number;
  flagged_actions: number;
  avg_causal_precision?: number | null;
  avg_proxy_citation_rate?: number | null;
  recent: TraceSummary[];
};

export type SystemHealth = {
  status: string;
  provider: string;
  database_backend: string;
};

export async function getHealth(): Promise<SystemHealth> {
  return request("/health");
}

export async function listMemories(): Promise<Memory[]> {
  return request("/memories");
}

export async function resetDemo(): Promise<{ memories: Memory[] }> {
  return request("/demo/reset", { method: "POST" });
}

export async function createMemory(content: string): Promise<Memory> {
  return request("/memories", {
    method: "POST",
    body: JSON.stringify({ content, memory_type: "raw", generation: 0 })
  });
}

export async function consolidate(memoryIds: string[]) {
  return request("/consolidations", {
    method: "POST",
    body: JSON.stringify({ memory_ids: memoryIds })
  });
}

export async function queryAgent(query: string, topK = 3): Promise<QueryResult> {
  return request("/query", {
    method: "POST",
    body: JSON.stringify({ query, top_k: topK })
  });
}

export async function runInterventions(traceId: string): Promise<Intervention[]> {
  return request(`/traces/${traceId}/interventions`, { method: "POST" });
}

export async function getReport(traceId: string): Promise<AttributionReport> {
  return request(`/traces/${traceId}/report`);
}

export async function investigate(traceId: string, question: string): Promise<ForensicResponse> {
  return request(`/forensics/${traceId}`, {
    method: "POST",
    body: JSON.stringify({ question })
  });
}

export async function getEvaluation() {
  return request("/evaluation");
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  return request("/dashboard/summary");
}

async function request(path: string, init: RequestInit = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {})
    },
    ...init
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || response.statusText);
  }
  return response.json();
}
