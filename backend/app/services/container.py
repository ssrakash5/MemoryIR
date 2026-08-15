from __future__ import annotations

from dataclasses import dataclass

from ..config import Settings
from .attribution import AttributionEngine
from .consolidator import Consolidator
from .evaluation import EvaluationService
from .generator import QueryEngine
from .interventions import InterventionEngine
from .llm import ModelProvider, make_provider
from .mcp_investigator import MCPInvestigator
from .memory_store import build_store


@dataclass
class Services:
    settings: Settings
    provider: ModelProvider
    store: object
    consolidator: Consolidator
    query_engine: QueryEngine
    intervention_engine: InterventionEngine
    attribution: AttributionEngine
    investigator: MCPInvestigator
    evaluation: EvaluationService


def build_services(settings: Settings) -> Services:
    provider = make_provider(settings)
    store = build_store(settings)
    query_engine = QueryEngine(store, provider)
    consolidator = Consolidator(store, provider)
    intervention_engine = InterventionEngine(store, provider, query_engine)
    attribution = AttributionEngine(store)
    investigator = MCPInvestigator(settings, store, attribution)
    evaluation = EvaluationService(settings)
    if settings.database_backend == "memory":
        store.seed_demo(provider)
    return Services(
        settings=settings,
        provider=provider,
        store=store,
        consolidator=consolidator,
        query_engine=query_engine,
        intervention_engine=intervention_engine,
        attribution=attribution,
        investigator=investigator,
        evaluation=evaluation,
    )
