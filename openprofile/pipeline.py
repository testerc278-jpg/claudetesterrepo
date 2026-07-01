"""Pipeline orchestrator: resolve -> fetch -> classify -> score -> assemble Profile."""
from __future__ import annotations

from .classifier import IndustryClassifier
from .config import Config
from .connectors.abn_lookup import AbnLookupConnector
from .connectors.rdap import RdapConnector
from .connectors.website import WebsiteConnector
from .http_client import PoliteClient
from .models import Activity, Entity, Profile, ProvenanceRecord
from .resolver import pick_best, rank_candidates
from .scoring import score_trading


class Pipeline:
    def __init__(self, config: Config | None = None):
        self.cfg = config or Config.from_env()
        self.client = PoliteClient(self.cfg)
        self.abn = AbnLookupConnector(self.client, self.cfg)
        self.web = WebsiteConnector(self.client, self.cfg)
        self.rdap = RdapConnector(self.client, self.cfg)
        self.classifier = IndustryClassifier()

    def run(self, query: str, *, state: str | None = None,
            domain: str | None = None) -> Profile:
        provenance: list[ProvenanceRecord] = []
        warnings: list[str] = []

        # --- 1. Resolve via ABR (if available) ---
        candidates: list[Entity] = []
        if self.abn.available():
            candidates, prov = self.abn.search(query)
            provenance.extend(prov)
        else:
            warnings.append(
                "ABN_LOOKUP_GUID not set: skipping the Australian Business Register. "
                "Resolution and trading status fall back to web/RDAP signals only."
            )

        ranked = rank_candidates(query, candidates, state=state)
        best, confident = pick_best(ranked)
        if not confident and ranked:
            warnings.append(
                "Entity resolution is low-confidence; review the candidate list before "
                "trusting the profile."
            )

        entity = best or Entity(name=query, state=state, domain=domain)

        # --- 2. Enrich the chosen entity from the ABR ---
        if self.abn.available() and entity.abn:
            detailed, prov = self.abn.detail(entity.abn)
            provenance.extend(prov)
            if detailed:
                detailed.match_score = entity.match_score
                detailed.domain = entity.domain or domain
                entity = detailed
        if domain and not entity.domain:
            entity.domain = domain

        # --- 3. Website + RDAP signals / activity text ---
        website_data = None
        activity_text_parts: list[str] = [entity.name]
        if entity.entity_type:
            activity_text_parts.append(entity.entity_type)
        if entity.domain:
            website_data, prov = self.web.fetch(entity.domain)
            provenance.extend(prov)
            if website_data.reachable:
                activity_text_parts += [website_data.title,
                                        website_data.meta_description,
                                        website_data.body_text]
            else:
                warnings.append(f"Website not reachable: {website_data.error}")

        domain_data = None
        if entity.domain:
            domain_data, prov = self.rdap.fetch(entity.domain)
            provenance.extend(prov)

        # --- 4. Classify industry/sector ---
        activity_text = "\n".join(p for p in activity_text_parts if p)
        classifications = self.classifier.classify(activity_text, top_k=3)
        if not classifications:
            warnings.append("No industry classification could be derived from available text.")

        activities: list[Activity] = []
        if website_data and website_data.reachable and website_data.meta_description:
            activities.append(Activity(
                description=website_data.meta_description,
                evidence=[website_data.url],
            ))

        # --- 5. Trading likelihood ---
        trading = score_trading(entity, website_data, domain_data)

        return Profile(
            query=query,
            entity=entity,
            classifications=classifications,
            activities=activities,
            trading=trading,
            provenance=provenance,
            candidates=ranked[: self.cfg.max_candidates],
            warnings=warnings,
        )
