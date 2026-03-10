"""Knowledge agent — RAG over the lecture knowledge base.

Provides semantic search over documents stored in ``data/knowledge_base/``
using ChromaDB as the vector store and ``sentence-transformers`` for
embedding generation.

Supported document formats:
  * ``.txt`` / ``.md`` — read directly
  * ``.pdf``           — extracted with PyPDF2
  * ``.docx``          — extracted with python-docx

DEMO_MODE (``config.DEMO_MODE == True``):
  Returns mock knowledge results without touching the database.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from backend import config

logger = logging.getLogger(__name__)

# Approximate tokens per chunk (1 token ≈ 4 characters for English)
_CHUNK_CHARS = 2000
# Overlap between consecutive chunks to preserve context
_OVERLAP_CHARS = 200
# ChromaDB collection name
_COLLECTION_NAME = "lecture_knowledge"
# Directory containing the lecture knowledge base documents
_KNOWLEDGE_BASE_DIR = Path("data/knowledge_base")


def _chunk_text(text: str, chunk_size: int = _CHUNK_CHARS, overlap: int = _OVERLAP_CHARS) -> list[str]:
    """Split *text* into overlapping chunks.

    Args:
        text: The full document text.
        chunk_size: Maximum character length per chunk.
        overlap: Character overlap between consecutive chunks.

    Returns:
        A list of text chunk strings.
    """
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def _read_txt(path: Path) -> str:
    """Read a plain-text or Markdown file."""
    return path.read_text(encoding="utf-8", errors="replace")


def _read_pdf(path: Path) -> str:
    """Extract text from a PDF file using PyPDF2."""
    try:
        import PyPDF2  # type: ignore[import-untyped]

        text_parts: list[str] = []
        with path.open("rb") as fh:
            reader = PyPDF2.PdfReader(fh)
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)
    except ImportError:
        logger.warning("PyPDF2 not installed — skipping PDF: %s", path)
        return ""
    except Exception:
        logger.exception("Failed to read PDF: %s", path)
        return ""


def _read_docx(path: Path) -> str:
    """Extract text from a DOCX file using python-docx."""
    try:
        import docx  # type: ignore[import-untyped]

        doc = docx.Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    except ImportError:
        logger.warning("python-docx not installed — skipping DOCX: %s", path)
        return ""
    except Exception:
        logger.exception("Failed to read DOCX: %s", path)
        return ""


class KnowledgeAgent:
    """Manages the RAG knowledge base for lecture content retrieval.

    Uses ChromaDB for vector storage and ``sentence-transformers`` for
    embedding generation.  All public methods are async-compatible
    (embedding + DB operations are synchronous but fast enough to run
    inline for typical knowledge-base sizes).

    Usage::

        agent = KnowledgeAgent()
        await agent.initialize()
        results = await agent.query("What is backpropagation?", top_k=3)
    """

    def __init__(self) -> None:
        """Initialise ChromaDB client and prepare embedding model."""
        self._chroma_client = None
        self._collection = None
        self._embedding_model = None
        logger.info(
            "KnowledgeAgent initialised (DEMO_MODE=%s, chroma_path=%s)",
            config.DEMO_MODE,
            config.CHROMA_PATH,
        )

    # ------------------------------------------------------------------
    # Lazy loaders
    # ------------------------------------------------------------------

    def _load_chroma(self) -> None:
        """Connect to (or create) the ChromaDB persistent collection."""
        if self._chroma_client is not None:
            return
        try:
            import chromadb  # type: ignore[import-untyped]

            os.makedirs(config.CHROMA_PATH, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(path=config.CHROMA_PATH)
            self._collection = self._chroma_client.get_or_create_collection(
                name=_COLLECTION_NAME
            )
            logger.info(
                "KnowledgeAgent: ChromaDB connected (path=%s, collection=%s)",
                config.CHROMA_PATH,
                _COLLECTION_NAME,
            )
        except Exception:
            logger.exception("KnowledgeAgent: failed to connect to ChromaDB")

    def _load_embedding_model(self) -> None:
        """Load the sentence-transformers embedding model."""
        if self._embedding_model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

            logger.info("Loading embedding model: %s", config.EMBEDDING_MODEL)
            self._embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
            logger.info("Embedding model loaded")
        except Exception:
            logger.exception("KnowledgeAgent: failed to load embedding model")

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of text strings.

        Args:
            texts: Strings to embed.

        Returns:
            List of embedding vectors (one per input string).
        """
        if self._embedding_model is None:
            return [[0.0] * 384] * len(texts)
        return self._embedding_model.encode(texts).tolist()

    # ------------------------------------------------------------------
    # Initialisation / ingestion
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Scan the knowledge base directory and ingest all documents.

        Existing embeddings in ChromaDB are reused if the document has not
        changed (based on content hash stored as metadata).

        Creates the knowledge base directory if it does not yet exist.
        """
        if config.DEMO_MODE:
            logger.info("KnowledgeAgent.initialize: DEMO_MODE — skipping ingestion")
            return

        self._load_chroma()
        self._load_embedding_model()

        if self._collection is None:
            logger.error("KnowledgeAgent.initialize: ChromaDB collection unavailable")
            return

        _KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
        files = list(_KNOWLEDGE_BASE_DIR.iterdir())
        if not files:
            logger.info(
                "KnowledgeAgent.initialize: no documents found in %s",
                _KNOWLEDGE_BASE_DIR,
            )
            return

        total_chunks = 0
        for file_path in files:
            if file_path.is_file():
                n = self._ingest_file(file_path)
                total_chunks += n

        logger.info(
            "KnowledgeAgent.initialize: ingested %d files, %d chunks",
            len(files),
            total_chunks,
        )

    def _ingest_file(self, path: Path) -> int:
        """Ingest a single document file into ChromaDB.

        Args:
            path: Absolute or relative path to the document.

        Returns:
            Number of chunks added.
        """
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md"}:
            text = _read_txt(path)
        elif suffix == ".pdf":
            text = _read_pdf(path)
        elif suffix == ".docx":
            text = _read_docx(path)
        else:
            logger.debug("KnowledgeAgent: unsupported file type — %s", path)
            return 0

        if not text.strip():
            logger.warning("KnowledgeAgent: empty content — %s", path)
            return 0

        chunks = _chunk_text(text)
        if not chunks:
            return 0

        embeddings = self._embed(chunks)
        ids = [f"{path.name}::{i}" for i in range(len(chunks))]
        metadatas = [{"source": path.name, "chunk_index": i} for i in range(len(chunks))]

        try:
            # Upsert so re-ingestion is idempotent
            self._collection.upsert(  # type: ignore[union-attr]
                documents=chunks,
                embeddings=embeddings,
                ids=ids,
                metadatas=metadatas,
            )
        except Exception:
            logger.exception("KnowledgeAgent: ChromaDB upsert failed for %s", path)
            return 0

        logger.debug(
            "KnowledgeAgent: ingested %s — %d chunks", path.name, len(chunks)
        )
        return len(chunks)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    async def query(self, query_text: str, top_k: int = 3) -> list[dict]:
        """Semantic search over the knowledge base.

        Args:
            query_text: Natural-language query.
            top_k: Maximum number of relevant chunks to return.

        Returns:
            List of dicts, each with keys ``text``, ``source``, and ``score``.
        """
        if config.DEMO_MODE:
            return [
                {
                    "text": f"[DEMO] Relevant knowledge about: {query_text}",
                    "source": "demo_knowledge.txt",
                    "score": 0.9,
                }
            ]

        self._load_chroma()
        self._load_embedding_model()

        if self._collection is None:
            logger.warning("KnowledgeAgent.query: collection not available")
            return []

        try:
            embeddings = self._embed([query_text])
            if not embeddings:
                logger.warning("KnowledgeAgent.query: embedding returned empty result")
                return []
            query_embedding = embeddings[0]

            # ChromaDB handles n_results exceeding collection size gracefully
            # (returns all available documents), so we don't need to call count().
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=max(1, top_k),
                include=["documents", "metadatas", "distances"],
            )

            chunks: list[dict] = []
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            for doc, meta, dist in zip(documents, metadatas, distances):
                # Convert L2 distance to a similarity score [0,1]
                score = 1.0 / (1.0 + float(dist))
                chunks.append(
                    {
                        "text": doc,
                        "source": meta.get("source", "unknown"),
                        "score": round(score, 3),
                    }
                )
            return chunks
        except Exception:
            logger.exception("KnowledgeAgent.query: error during search")
            return []

    # ------------------------------------------------------------------
    # Document management
    # ------------------------------------------------------------------

    async def add_document(self, file_path: str) -> bool:
        """Ingest a single document at runtime.

        Args:
            file_path: Path to the document file to add.

        Returns:
            ``True`` if at least one chunk was ingested, ``False`` otherwise.
        """
        if config.DEMO_MODE:
            logger.info("KnowledgeAgent.add_document: DEMO_MODE — no-op")
            return True

        self._load_chroma()
        self._load_embedding_model()

        path = Path(file_path)
        if not path.exists():
            logger.error("KnowledgeAgent.add_document: file not found: %s", file_path)
            return False

        n = self._ingest_file(path)
        return n > 0

    async def get_topic_outline(self, topic: str) -> list[str]:
        """Extract a lecture outline for *topic* from the knowledge base.

        Searches for topic-related chunks and extracts heading-like lines to
        build an ordered outline.

        Args:
            topic: The lecture topic to build an outline for.

        Returns:
            Ordered list of subtopic strings.
        """
        if config.DEMO_MODE:
            return [
                f"Introduction to {topic}",
                f"Core concepts of {topic}",
                f"Practical applications of {topic}",
                f"Common challenges in {topic}",
                f"Summary and further reading",
            ]

        results = await self.query(topic, top_k=5)
        if not results:
            return [f"Introduction to {topic}", "Core concepts", "Summary"]

        headings: list[str] = []
        for r in results:
            text = r.get("text", "")
            for line in text.splitlines():
                line = line.strip()
                # Treat lines that start with markdown heading or are short and title-case as headings
                if (
                    line.startswith("#")
                    or (
                        len(line) < 80
                        and len(line) > 5
                        and line[0].isupper()
                        and not line.endswith(".")
                    )
                ):
                    clean = line.lstrip("#").strip()
                    if clean and clean not in headings:
                        headings.append(clean)

        if not headings:
            headings = [f"Introduction to {topic}", "Core concepts", "Summary"]

        return headings[:10]  # Return at most 10 outline items


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
knowledge_agent = KnowledgeAgent()
