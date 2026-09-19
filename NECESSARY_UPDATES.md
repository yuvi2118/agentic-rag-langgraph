# Necessary Updates / Known Gaps

Running list of things we deliberately simplified or deferred while building,
to revisit once the full pipeline works end-to-end.

## FIXED: web_search fallback wasn't triggering for real recency questions

Found via manual testing: "search is there any new updates came in september
in k8s" returned "I don't know" instead of falling back to Tavily. Root
causes (both fixed):

1. planner_node had no notion of the actual current date, so it rewrote
   time-relative queries using a stale/hallucinated year (e.g. "September
   2024" when the real date was 2026). Fixed by injecting
   `datetime.now()` into the planner's system prompt.
2. CONFIDENCE_THRESHOLD was 0.3, which let weak/irrelevant matches (~0.33,
   from an unrelated architecture.pptx chunk) pass as "confident enough" and
   skip the web_search fallback. Calibrated against real queries: good
   matches scored 0.83-0.94, bad matches scored 0.04-0.27 - wide gap, no
   ambiguous middle ground in this sample. Raised threshold to 0.5 for
   margin on both sides.

## Chunking (app/ingestion.py - chunk_text)

- Current approach: custom paragraph-based greedy packing (split on `\n\n`,
  pack paragraphs up to max_chars). This is NOT LangChain's recursive
  character splitting.
- No overlap between consecutive chunks - context at a chunk boundary can be
  lost. Recursive splitters typically carry ~100-200 char overlap forward.
- No fallback if a single paragraph itself exceeds max_chars (e.g. a huge
  unbroken block of text) - need to check/fix what currently happens in that
  case.
- Considered semantic chunking (embedding-based, split where meaning shifts)
  but chose paragraph-based for simplicity. Could revisit as an upgrade.

## Reranking

- Using Cohere `rerank-v3.5` (chosen over Jina reranker since we already
  skipped Jina for embeddings). Working well in testing.

## LangGraph agent - v2 design (deferred)

Built v1 first: planner -> (retriever -> web_search fallback on low confidence
| responder direct for conversational) -> responder. 4 nodes, 2 conditional
edges. This is intentionally simple to learn LangGraph mechanics first.

Found a stronger pattern on GitHub (a paper-QA RAG project) worth adding
once v1 works end-to-end:

- 3-way router instead of 2-way: conversational / technical / claim
  ("claim" = user asserts a fact that needs checking, e.g. "X replaced Y" -
  goes straight to Tavily to verify instead of Qdrant).
- Self-correcting retrieval loop: retrieve -> relevancy_check (we can reuse
  our existing Cohere rerank_score for this, no new component needed) ->
  if weak, rewrite the query and retry retrieval (capped at ~2 retries to
  avoid an infinite loop) -> if still weak after max retries, THEN fall back
  to Tavily web search (merges with our existing fallback idea) -> responder.
- Needs a max-retry counter in AgentState so the loop can't spin forever.

## Web search (app/agent.py - web_search_node)

- Tavily's relevance_score measures how well a result's TEXT matches the
  query semantically/by keyword - it is NOT a recency signal. Observed this
  directly: for the query "latest Kubernetes version released 2026", a
  release-schedule page scored higher (0.866) than a support-lifecycle page
  containing later calendar dates (0.754), because the schedule page's
  content is more densely about "release" as a topic, even though it wasn't
  the most chronologically current source.
- Implication: if a user asks "what's the newest/latest X", we cannot just
  trust relevance ranking - may need to either (a) explicitly prompt the
  Responder to look for and prefer the most recent date mentioned across
  results, or (b) have Tavily/our own logic sort by a detected date field
  when the query is asking about recency specifically. Not yet handled.

## General

- (add more items here as we find them)
