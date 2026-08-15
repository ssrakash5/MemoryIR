from __future__ import annotations

import itertools
import json
from typing import Any
from urllib.parse import urlparse

import httpx
import truststore

truststore.inject_into_ssl()

from ..config import Settings
from ..models import ForensicResponse
from .attribution import AttributionEngine


ALLOWED_MCP_TOOLS = {
    "list_databases",
    "list_tables",
    "get_table_schema",
    "select_query",
    "explain_query",
    "show_statement",
}


class MCPInvestigator:
    def __init__(self, settings: Settings, store: object, attribution: AttributionEngine) -> None:
        self.settings = settings
        self.store = store
        self.attribution = attribution
        self._ids = itertools.count(1)

    def investigate(self, trace_id: str, question: str) -> ForensicResponse:
        report = self.attribution.report(trace_id)
        calls = self._inspect_with_mcp(trace_id)
        mode = "cockroach-mcp" if self.settings.mcp_api_key and self.settings.mcp_cluster_id else "mock"
        answer = self._narrative(trace_id, question, report, calls)
        return ForensicResponse(
            trace_id=trace_id,
            question=question,
            answer=answer,
            mcp_calls=calls,
            mode=mode,
        )

    def _inspect_with_mcp(self, trace_id: str) -> list[dict[str, Any]]:
        database = self._database_name()
        planned = [
            ("get_table_schema", {"database": database, "table": "traces"}),
            ("select_query", {"database": database, "query": f"SELECT * FROM traces WHERE trace_id = '{trace_id}'"}),
            ("select_query", {"database": database, "query": f"SELECT * FROM retrieval_runs WHERE trace_id = '{trace_id}'"}),
            ("select_query", {"database": database, "query": f"SELECT * FROM generation_claims WHERE trace_id = '{trace_id}'"}),
            ("select_query", {"database": database, "query": f"SELECT * FROM intervention_runs WHERE trace_id = '{trace_id}'"}),
        ]
        if not (self.settings.mcp_api_key and self.settings.mcp_cluster_id):
            return [
                {"tool": tool, "status": "simulated", "arguments": arguments}
                for tool, arguments in planned
            ]

        calls = []
        for tool, arguments in planned:
            try:
                result = self._call_tool(tool, arguments)
                calls.append({"tool": tool, "status": "ok", "arguments": arguments, "result": result})
            except Exception as exc:
                calls.append({"tool": tool, "status": "error", "arguments": arguments, "error": str(exc)})
        return calls

    def _call_tool(self, tool: str, arguments: dict[str, Any]) -> Any:
        if tool not in ALLOWED_MCP_TOOLS:
            raise ValueError(f"MCP tool is not allowlisted: {tool}")
        headers = {
            "Authorization": f"Bearer {self.settings.mcp_api_key}",
            "mcp-cluster-id": self.settings.mcp_cluster_id or "",
            "Content-Type": "application/json",
        }
        payload = {
            "jsonrpc": "2.0",
            "id": next(self._ids),
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
        }
        response = httpx.post(
            self.settings.mcp_endpoint,
            headers=headers,
            json=payload,
            timeout=20,
            trust_env=False,
        )
        response.raise_for_status()
        return self._parse_mcp_response(response)

    def _parse_mcp_response(self, response: httpx.Response) -> Any:
        content_type = response.headers.get("content-type", "")
        if content_type.startswith("text/event-stream"):
            for line in response.text.splitlines():
                if not line.startswith("data:"):
                    continue
                payload = json.loads(line.removeprefix("data:").strip())
                if "error" in payload:
                    raise RuntimeError(payload["error"])
                return payload.get("result")
            raise RuntimeError("MCP response did not contain a data event.")
        payload = response.json()
        if "error" in payload:
            raise RuntimeError(payload["error"])
        return payload.get("result", payload)

    def _database_name(self) -> str:
        if not self.settings.database_url:
            return "defaultdb"
        parsed = urlparse(self.settings.database_url)
        name = parsed.path.lstrip("/")
        return name or "defaultdb"

    def _narrative(self, trace_id: str, question: str, report, calls: list[dict[str, Any]]) -> str:
        claimed = ", ".join(report.claimed_memories) or "none"
        retrieved = ", ".join(report.retrieved_memories) or "none"
        influential = ", ".join(report.influential_memories) or "none"
        ground_lines = []
        for item in report.ground_provenance:
            ground_lines.append(
                f"{item['ancestor']} -> {item['retrieved']} -> Decision "
                f"(depth {item['depth']})"
            )
        ground = "\n".join(ground_lines) or "No ground ancestor changed the decision under ablation."
        tool_names = ", ".join(call["tool"] for call in calls)
        return (
            "MEMORYIR FORENSIC REPORT\n\n"
            f"Trace: {trace_id}\n"
            f"Question: {question}\n"
            f"Decision: {report.decision}\n\n"
            f"Agent claimed: {claimed}\n"
            f"Retrieved: {retrieved}\n"
            f"Measured influential memories: {influential}\n\n"
            f"Ground provenance:\n{ground}\n\n"
            f"Faithfulness: {'PARTIAL' if report.causal_precision < 1 else 'COMPLETE'}\n"
            f"MCP tools inspected: {tool_names}\n"
            "Finding: the report measures counterfactual sensitivity under controlled ablation."
        )
