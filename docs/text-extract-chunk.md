PRD: Text Extraction & Semantic Chunking Library (importable package)

tl;dr

Build a configurable, well-documented library that ingests PDFs (single or directory), extracts and normalizes text, and produces high-quality chunks (fixed or semantic-aware). Deliver idiomatic APIs, pluggable strategies, deterministic outputs, easy testing, logging, and low friction integration for product teams.

⸻

Problem statement

Teams keep re-implementing PDF parsing + chunking. We’ll provide an importable library that standardizes extraction, cleaning, and chunking so apps get consistent, high-quality chunks ready for embeddings, search, or RAG pipelines.

⸻

Goals

Business
• Reduce duplicated engineering time.
• Standardize downstream input to embedding/search pipelines.
• Speed up feature build cycles across products.

Developer / User
• Single-line install pip install docchunk (or similar).
• Clear, documented API with sensible defaults.
• Extensible plugin interfaces for OCR, parsers, chunkers.
• Deterministic, testable outputs for reproducible pipelines.

Non-Goals
• Not a hosted API service (no network runtime).
• Not an embeddings/LLM provider (but outputs are embedding-ready).
• Not replacing enterprise OCR offerings — we integrate them where needed.

⸻

Core Capabilities (what the library must do) 1. Input handling
• Accept a single PDF file, multiple file paths, or a directory.
• Accept file-like objects and bytes for frameworks that stream files. 2. Extraction
• Use a primary pure-text PDF parser with a configurable OCR fallback.
• Support multi-column and mixed-mode PDFs; heuristics to preserve reading order. 3. Cleaning
• Remove headers/footers and page numbers heuristically or via user-provided regex rules.
• Normalize whitespace, normalize unicode, remove repeated OCR artifacts.
• Optionally preserve/annotate original page numbers and bounding boxes (when provided). 4. Chunking
• Fixed-length chunker: token or character-based windowing with overlap.
• Semantic chunker: uses sentence/paragraph boundaries + semantic-similarity merging (local embeddings or sentence transformers).
• Structure-aware chunker: split by detected headings/sections, preserving section metadata.
• Pluggable strategy interface so teams can implement custom chunkers. 5. Output
• JSON list of chunks: {id, text, tokens, start_char, end_char, page_start, page_end, metadata}.
• Option to produce newline-separated text files or Parquet/NDJSON for large-scale pipelines. 6. Observability & Robustness
• Clear logs and structured error classes (ExtractionError, OcrFallbackUsed, ChunkingWarning).
• Statistics returned per run: pages processed, chunks produced, percent OCR fallback, time taken. 7. Integration helpers
• Convenience functions for writing to embedding stores (e.g., vector DB adaptors — optional plugins).
• Small CLI wrapper for quick local testing.

⸻

API design (Python-first)

Install

pip install docchunk

High-level usage (sync)

from docchunk import Processor, FixedChunker, SemanticChunker

proc = Processor(
parser="pdfplumber", # or "pdfium", "pypdf"
ocr_fallback=True, # use Tesseract or external OCR
header_footer_rules=[r"^Page \d+$"],
default_language="en",
logger=my_logger
)

# single file

chunks = proc.process_file("contracts/nda.pdf",
chunker=FixedChunker(chunk_size=500, overlap=50),
output_format="json")

# directory

report = proc.process_dir("docs/incoming/",
chunker=SemanticChunker(model="all-MiniLM-L6-v2", similarity_threshold=0.75),
save_to="out/chunks.ndjson")

Low-level pipeline control

# Extraction only

pages = proc.extract("file.pdf") # returns list of Page objects with text and metadata

# Cleaning only

clean_pages = proc.clean(pages, remove_headers=True)

# Chunking only

chunks = proc.chunk(clean_pages, strategy="semantic", \*\*kwargs)

Example chunk object

{
"id": "file.pdf::chunk::0001",
"text": "This is the chunk text ...",
"token_count": 412,
"char_range": [1023, 1432],
"page_range": [3,4],
"metadata": {
"source": "file.pdf",
"section_title": "Payment Terms",
"extraction_strategy": "pdfplumber"
}
}

⸻

Package structure (suggested)

docchunk/
**init**.py
processor.py # high-level orchestration
parsers/
base.py
pdfplumber.py
pypdf.py
pdfium.py
ocr/
tesseract.py
aws_textract.py
none.py
cleaners/
base.py
heuristics.py
regex_rules.py
chunkers/
base.py
fixed.py
semantic.py
heading_based.py
outputs/
json.py
ndjson.py
parquet.py
adapters/
vector_db.py # optional adapter interface
cli.py
utils/
text_utils.py
tokenizers.py
tests/
docs/

⸻

Chunking strategies — implementation details

Fixed chunker
• Operates on tokens (use a tokenizer like tiktoken / sentencepiece) or chars.
• Parameters: chunk_size (tokens), overlap (tokens), prefer_sentence_boundary (bool).
• Deterministic sliding-window with overlap; returns chunk metadata.

Semantic chunker
• Stage 1: split into candidate atomic units (paragraphs/sentences).
• Stage 2: compute local embeddings for each unit (option: user provides model or library uses a default small model).
• Stage 3: merge adjacent units while ensuring final chunk embedding cosine similarity to the chunk mean is above threshold OR until chunk token limit reached.
• Parameters: unit_split="paragraph"|"sentence", model (hf model string or callable embedding fn), similarity_threshold, max_tokens, min_tokens.
• Option to run in “offline” mode (local sentence-transformers) or “external” (user-provided embedding API).

Heading-aware chunker
• Use heading detection heuristics (font size if parser provides, or capitalization + punctuation) to respect document structure.

⸻

Extensibility & plugin model
• Define abstract base classes for Parser, OCRProvider, Cleaner, Chunker, OutputWriter.
• Allow teams to register custom implementations:

from docchunk import register_chunker
register_chunker("my-company-chunker", MyChunkerClass)

    •	Provide hooks: on_extraction(page), on_chunk_created(chunk), on_error(exc, context).

⸻

Configuration & Defaults
• Provide a Config dataclass to hold defaults, environment overrides, and per-call overrides.
• Sensible defaults:
• parser: pdfplumber
• ocr_fallback: False
• chunker: FixedChunker(chunk_size=512, overlap=64)
• output: ndjson
• Allow configuration via YAML file, environment vars, or programmatic API.

⸻

Observability, errors & metrics
• Structured logs (JSON) with event types.
• Emit a summary object with:
• files_processed, pages_extracted, chunks_created, errors_count
• processing_time_seconds, ocr_pages_count
• Error classes: ExtractionError, ParserError, OcrError, ChunkingError.
• Return partial results when recoverable, and list warnings.

⸻

Performance & scaling
• Local CPU-bound operations; use multiprocessing/thread pool for directory processing.
• Memory: stream files and avoid reading huge PDFs entirely into memory when possible.
• Provide batch embedding helper (if semantic chunker used) with configurable batch size.
• Benchmarks: aim to process ~10–50 pages/second on a beefy dev machine for pure text PDFs (varies with OCR).

⸻

Security & Privacy
• No telemetry by default. Optionally enable usage metrics with explicit opt-in.
• Process files locally — no network calls unless user explicitly configures external OCR/embedding services.
• Provide encryption-at-rest advice for saved outputs (not enforced by library).

⸻

Testing & QA
• Unit tests for each parser using a curated corpus of PDFs:
• text-only, multi-column, scanned (image) PDF, tables-heavy PDF, forms.
• Golden-file tests for cleaned text and chunk boundaries.
• Integration tests for end-to-end processing on sample directories.
• Performance tests for throughput and memory.

⸻

Packaging & distribution
• Publish to PyPI: docchunk.
• Semantic versioning and changelog.
• Provide wheel distributions for common platforms.
• Optionally a minimal Node/TS port or wrapper (docchunk-node) exposing same config and chunk format.

⸻

Docs & onboarding
• API docs (Sphinx or mkdocs), quickstart examples, cookbook:
• “Process a directory and produce ndjson”
• “Customize header/footer regex”
• “Plug in AWS Textract for OCR fallback”
• Short video or GIF demo for onboarding.
• Migrations guide for teams currently using ad-hoc scripts.

⸻

Adoption plan & support
• Provide a “starter kit” repo that shows integration with:
• a vector DB (e.g., Pinecone/Weaviate) via adapter
• an embedding pipeline (example with sentence-transformers)
• a sample RAG pipeline
• Offer code review / migration help for the first two adopters.
• Maintain an internal Slack channel for support and bug reports.

⸻

Success metrics (revisited)
• Developer adoption: used by at least 3 teams in first quarter after release.
• Time saved: reduce average developer integration time from ~3 days to <1 day.
• Reliability: ≥ 95% successful processing rate on internal document corpus.
• Quality: downstream retrieval precision improves (measured post-adoption).

⸻

Milestones & sequencing (no fixed dates — use XX weeks) 1. Week 0–2: Core extraction + cleaning + example CLI (single file). 2. Week 2–4: Directory processing, parallelization, logging. 3. Week 4–6: Fixed chunker, JSON/NDJSON outputs, unit tests. 4. Week 6–8: Semantic & heading-aware chunkers, embedding adapter interface. 5. Week 8–10: Packaging, docs, example adaptors (vector DB), integration tests. 6. Week 10–12: Internal adoption, feedback, bug fixes, polish.

⸻

Example: small developer-facing README excerpt

from docchunk import Processor, FixedChunker

proc = Processor()
result = proc.process_file("specs/api-v1.pdf",
chunker=FixedChunker(chunk_size=512, overlap=64),
save_to="out/api-v1.ndjson")

print(f"Produced {result.chunks_count} chunks from {result.pages_processed} pages")

⸻

Open design decisions (recommendations)
• Default semantic model: ship with a lightweight local sentence-transformer (if licensing allows) OR require teams to supply embeddings to avoid heavy dependencies.
• OCR: recommend optional supported integrations (Tesseract for free/local; AWS Textract or GCP DocumentAI for high-quality OCR).
• Language support: ensure Unicode-first design — add directionality/RTL handling later if required.

⸻

Risks & mitigations
• OCR complexity: scanned documents can be messy — mitigate by integrating enterprise OCR and surfacing a “OCR fallback used” flag.
• Chunk quality variance across doc types: provide best-effort heuristics and allow teams to provide custom chunkers.
• Binary dependency issues (pdfium / tesseract): provide prebuilt wheels or document native dependency steps.
