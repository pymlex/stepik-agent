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


RANK_SYSTEM = """You rank Stepik courses for the user's learning goal.
Every ranked item must cite evidence from course card fields (field name + short excerpt).
List rejected courses with explicit reasons referencing card fields.
If data is missing, say so — do not invent ratings or workloads.
Order ranked list from best to worst."""


RANK_USER_TEMPLATE = """Goal:
{goal}

Deterministic filters:
{filters}

Freshness notes from web search:
{freshness}

Courses:
{courses}

Return ranking with evidence and rejection reasons."""


FRESHNESS_SYSTEM = """Generate short web search queries to check whether topics/tools
mentioned in courses remain relevant in 2026. Output queries only."""


JUDGE_SYSTEM = """You evaluate agent outputs for a test case.
Score 0-1. passed=true only if the output meets the criterion in the test.
Be strict about hallucinations and empty-handling."""
