EXTRACTION_SYSTEM_PROMPT = """You are a research paper analyst. Extract structured information for literature review.
Return valid JSON only matching the schema. Every claim, contribution, and limitation MUST include evidence_text (verbatim quote from the paper), page number, and section name.

Entity naming rules for tasks, methods, datasets, and metrics:
- Use canonical English academic terms.
- Normalize synonyms to one standard form (e.g. prefer "traffic flow prediction" over mixed variants).
- Keep named architectures distinct (BysGNN, STGCN, GMAN are NOT the same as generic "Graph Neural Network").
- Keep official dataset names as in the paper (SafeGraph, PeMS, BJER4).
- If unsure, prefer a specific name over a generic family name.
- When known entities are listed below, prefer an exact match from that list when appropriate.

Evidence fields (contributions, claims, limitations):
- evidence_text MUST be verbatim from the source (any language). Do NOT translate evidence.
"""

EXTRACTION_USER_TEMPLATE = """Analyze this paper and extract literature-review structure.

Paper ID: {paper_id}
Title hint: {title}

{known_entities}

Sections:
{sections_text}

Return JSON with keys: paper_id, title, year, tasks, methods, datasets, metrics, contributions, claims, limitations.

Field types:
- tasks, methods, datasets, metrics: arrays of plain strings (e.g. ["Graph Neural Network", "causal inference"]). Do NOT use objects for these fields.
- contributions, claims, limitations: arrays of objects, each with: text, evidence_text, page, section.
"""
