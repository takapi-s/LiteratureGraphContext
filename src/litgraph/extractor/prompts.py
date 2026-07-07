EXTRACTION_SYSTEM_PROMPT = """You are a research paper analyst. Extract structured information for literature review.
Return valid JSON only matching the schema. Every claim, contribution, and limitation MUST include evidence_text (verbatim quote from the paper), page number, and section name.
"""

EXTRACTION_USER_TEMPLATE = """Analyze this paper and extract literature-review structure.

Paper ID: {paper_id}
Title hint: {title}

Sections:
{sections_text}

Return JSON with keys: paper_id, title, year, tasks, methods, datasets, metrics, contributions, claims, limitations.

Field types:
- tasks, methods, datasets, metrics: arrays of plain strings (e.g. ["Graph Neural Network", "causal inference"]). Do NOT use objects for these fields.
- contributions, claims, limitations: arrays of objects, each with: text, evidence_text, page, section.
"""
