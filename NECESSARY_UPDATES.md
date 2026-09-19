# Necessary Updates / Known Gaps

Running list of things we deliberately simplified or deferred while building,
to revisit once the full pipeline works end-to-end.

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

## General

- (add more items here as we find them)
