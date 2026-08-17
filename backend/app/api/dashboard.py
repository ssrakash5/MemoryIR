from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import get_services
from ..models import DashboardSummary, TraceSummary
from ..services.container import Services

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(services: Services = Depends(get_services)) -> DashboardSummary:
    traces = services.store.list_traces(limit=50)
    interventions_by_trace = services.store.list_interventions_bulk([trace.trace_id for trace in traces])
    reports_by_trace = services.attribution.report_bulk(traces, interventions_by_trace)
    summaries: list[TraceSummary] = []
    precisions: list[float] = []
    proxy_rates: list[float] = []
    guarded_count = 0
    flagged_count = 0

    for trace in traces:
        guarded = len(interventions_by_trace.get(trace.trace_id, [])) > 0
        causal_precision = None
        causal_recall = None
        proxy_citation_rate = None
        ground_path = None
        flagged = False

        if guarded:
            guarded_count += 1
            report = reports_by_trace[trace.trace_id]
            causal_precision = report.causal_precision
            causal_recall = report.causal_recall
            proxy_citation_rate = report.proxy_citation_rate
            precisions.append(causal_precision)
            proxy_rates.append(proxy_citation_rate)
            if report.ground_provenance:
                path = report.ground_provenance[0].get("path")
                if isinstance(path, list):
                    ground_path = " -> ".join(str(item) for item in path)
            flagged = proxy_citation_rate > 0
            if flagged:
                flagged_count += 1

        summaries.append(
            TraceSummary(
                trace_id=trace.trace_id,
                user_query=trace.user_query,
                decision=trace.decision_label,
                status=trace.status,
                started_at=trace.started_at,
                completed_at=trace.completed_at,
                guarded=guarded,
                flagged=flagged,
                causal_precision=causal_precision,
                causal_recall=causal_recall,
                proxy_citation_rate=proxy_citation_rate,
                ground_path=ground_path,
            )
        )

    return DashboardSummary(
        total_actions=len(traces),
        guarded_actions=guarded_count,
        flagged_actions=flagged_count,
        avg_causal_precision=round(sum(precisions) / len(precisions), 4) if precisions else None,
        avg_proxy_citation_rate=round(sum(proxy_rates) / len(proxy_rates), 4) if proxy_rates else None,
        recent=summaries,
    )
