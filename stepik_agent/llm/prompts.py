QUERY_SYSTEM = """You generate Stepik search queries only.
Output must match the JSON schema exactly.
Do not invent filters, languages, or ratings not provided by the user.
Queries must be short keyword strings suitable for Stepik search."""


QUERY_USER_TEMPLATE = """Learning goal (free text):
{goal}

Stored preferences:
{prefs}

Deterministic filters (explicit Q&A only, may be empty):
{filters}

Generate distinct search queries. Do not repeat the same phrase."""


REFINE_SYSTEM = """You refine Stepik search queries after reviewing initial results.
Use only information from the goal and course summaries provided.
Do not hallucinate course ids or fields not in the input."""


REFINE_USER_TEMPLATE = """Goal:
{goal}

Initial queries used:
{queries}

Sample course titles and summaries:
{samples}

Propose refined queries and a short rationale."""


RANK_SYSTEM = """You rank Stepik courses using weighted criteria already computed in the input.
Weights: relevance_to_goal, freshness_2026, language_fit, price_fit, workload_fit, rating_quality, popularity.
Do not hard-drop courses for soft mismatches: reflect them as lower dimension scores.
Missing card fields must keep low dimension scores from the input, do not invent data.
Write detailed_explanation in Russian: 10-18 sentences. Explain weight formula, tradeoffs, why top courses win, why others are lower.
Every ranked course needs dimensions list aligned with input breakdown and evidence from card fields.
rejected is only for courses with total weighted score below 0.15 or clearly off-topic."""


RANK_USER_TEMPLATE = """Goal:
{goal}

User filters (soft constraints, not hard):
{filters}

Weights:
{weights}

Freshness notes:
{freshness}

Courses with precomputed _weighted_score and _score_breakdown:
{courses}

Return JSON: ranked (best first), optional rejected, summary (2-3 sentences), detailed_explanation (long)."""


FRESHNESS_SYSTEM = """Generate short web search queries to check whether topics/tools
mentioned in courses remain relevant in 2026. Output queries only."""


JUDGE_SYSTEM = """You evaluate agent outputs for a test case.
Score 0-1. passed=true only if the output meets the criterion in the test.
Be strict about hallucinations and empty-handling."""
