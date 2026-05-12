"""
rag.py — Retrieval Augmented Generation module

WHY RAG EXISTS:
Without RAG, Claude only knows what it was trained on.
With RAG, Claude can answer questions about YOUR documents.

Architecture (mirrors Nokia OAM data collection):
  Document uploaded
        ↓
  Chunked into 500-char pieces (like Nokia splitting large logs)
        ↓
  Each chunk embedded into 384-dimension vector
        ↓
  Stored in Supabase with pgvector
        ↓
  When user asks question → question embedded
        ↓
  Vector similarity search finds relevant chunks
        ↓
  Chunks injected into Claude's context window
        ↓
  Claude answers using YOUR knowledge
"""

import os
from supabase import create_client
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

# ── Supabase client ───────────────────────────────────────────────────
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# ── Embedding model ───────────────────────────────────────────────────
# WHY all-MiniLM-L6-v2:
# - 384 dimensions (fast, small, good quality)
# - No API key needed — runs locally
# - Same model used by many production RAG systems
# Downloads ~90MB on first run, cached after that
print("Loading embedding model...")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
print("Embedding model ready.")


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Split text into overlapping chunks.

    WHY overlap: If a key sentence sits at a chunk boundary,
    overlap ensures it appears in at least one complete chunk.
    Real life: Like Nokia splitting a large alarm log into
    overlapping windows so no alarm gets cut in half.

    Args:
        text: Full document text
        chunk_size: Characters per chunk (500 = ~80-100 words)
        overlap: Characters shared between adjacent chunks

    Returns:
        List of text chunks
    """
    if not text.strip():
        return []

    # Split on sentence boundaries where possible
    sentences = text.replace("\n", " ").split(". ")
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(current_chunk) + len(sentence) + 2 <= chunk_size:
            current_chunk += sentence + ". "
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            # Overlap: keep last `overlap` chars of previous chunk
            if len(current_chunk) > overlap:
                current_chunk = current_chunk[-overlap:] + sentence + ". "
            else:
                current_chunk = sentence + ". "

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    print(f"Chunked text into {len(chunks)} pieces")
    return chunks


def embed_text(text: str) -> list[float]:
    """
    Convert text into a 384-dimension vector.

    WHY embeddings: Vectors capture semantic meaning.
    "dog" and "puppy" will have similar vectors.
    "dog" and "Terraform" will have very different vectors.
    This lets us find semantically similar text.

    Args:
        text: Any string to embed

    Returns:
        List of 384 floats (the vector)
    """
    embedding = embedding_model.encode(text)
    return embedding.tolist()


def store_document(content: str, source: str = "manual") -> dict:
    """
    Chunk, embed, and store a document in Supabase.

    WHY: Every document needs to be broken into chunks
    before storing. One 10,000-word doc becomes 20+ chunks,
    each independently searchable.

    Real life: Like Nokia breaking a large configuration
    file into individual parameter records in a database.

    Args:
        content: Full document text
        source: Label for this document (filename, URL, etc.)

    Returns:
        Dict with count of chunks stored
    """
    chunks = chunk_text(content)

    if not chunks:
        return {"stored": 0, "error": "No content to store"}

    stored = 0
    for chunk in chunks:
        try:
            vector = embed_text(chunk)
            supabase.table("documents").insert({
                "content": chunk,
                "source": source,
                "embedding": vector
            }).execute()
            stored += 1
        except Exception as e:
            print(f"Failed to store chunk: {str(e)}")

    print(f"Stored {stored}/{len(chunks)} chunks for source: {source}")
    return {"stored": stored, "total_chunks": len(chunks), "source": source}


def retrieve_context(query: str, k: int = 3) -> list[dict]:
    """
    Find the k most relevant document chunks for a query.

    WHY Python-side similarity instead of RPC:
    Computes cosine similarity directly in Python using numpy —
    more portable and avoids PostgREST type casting issues.
    For production at scale, move this back to pgvector RPC.

    Real life: Like Nokia computing alarm correlation scores
    in the application layer before sending to the database.

    Args:
        query: User's question
        k: Number of chunks to retrieve (3 is standard for RAG)

    Returns:
        List of dicts with content, source, similarity score
    """
    try:
        import numpy as np

        # Embed the query
        query_vector = np.array(embed_text(query))

        # Fetch all documents with embeddings
        result = supabase.table("documents")\
            .select("id, content, source, embedding")\
            .execute()

        if not result.data:
            print("No documents in knowledge base")
            return []

        # Compute cosine similarity in Python
        similarities = []
        for row in result.data:
            emb = row.get("embedding")
            if not emb:
                continue

            # Parse embedding string if needed
            if isinstance(emb, str):
                emb = [float(x) for x in emb.strip("[]").split(",")]

            doc_vector = np.array(emb)

            # Cosine similarity = dot product / (norm * norm)
            sim = float(np.dot(query_vector, doc_vector) /
                       (np.linalg.norm(query_vector) * np.linalg.norm(doc_vector)))

            similarities.append({
                "id": row["id"],
                "content": row["content"],
                "source": row["source"],
                "similarity": sim
            })

        # Sort by similarity descending, filter threshold, return top k
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        top_k = [s for s in similarities[:k] if s["similarity"] > 0.1]

        best_sim = similarities[0]["similarity"] if similarities else 0
        print(f"Retrieved {len(top_k)} relevant chunks (best similarity: {best_sim:.3f})")
        return top_k

    except Exception as e:
        print(f"Retrieval error: {str(e)}")
        return []


def format_context(chunks: list[dict]) -> str:
    """
    Format retrieved chunks into a clean context string
    for injection into Claude's system prompt.

    Args:
        chunks: List of retrieved document chunks

    Returns:
        Formatted context string
    """
    if not chunks:
        return ""

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("source", "unknown")
        content = chunk.get("content", "")
        similarity = chunk.get("similarity", 0)
        context_parts.append(
            f"[Source {i}: {source} | Relevance: {similarity:.2f}]\n{content}"
        )

    return "\n\n".join(context_parts)


def list_documents() -> list[dict]:
    """
    List all unique document sources stored in the RAG database.

    Returns:
        List of document sources with chunk counts
    """
    try:
        result = supabase.table("documents")\
            .select("source")\
            .execute()

        sources = {}
        for row in result.data:
            src = row["source"]
            sources[src] = sources.get(src, 0) + 1

        return [{"source": k, "chunks": v} for k, v in sources.items()]

    except Exception as e:
        print(f"Could not list documents: {str(e)}")
        return []


def delete_document(source: str) -> dict:
    """
    Delete all chunks for a given document source.

    Args:
        source: Document source label to delete

    Returns:
        Dict confirming deletion
    """
    try:
        supabase.table("documents")\
            .delete()\
            .eq("source", source)\
            .execute()
        return {"deleted": True, "source": source}
    except Exception as e:
        return {"deleted": False, "error": str(e)}


# ── Test RAG directly ─────────────────────────────────────────────────
if __name__ == "__main__":

    print("\n--- Test 1: Store a document ---")
    result = store_document(
        content="""
        Sadhvi Sharma is a Cloud and AI Engineer based in Calgary, Alberta, Canada.
        She has experience deploying Nokia 5G Packet Core infrastructure.
        She has built an autonomous AI agent using the Anthropic Claude API.
        She is a Permanent Resident of Canada and is open to relocation.
        Her GitHub is github.com/sadvi11.
        She is pursuing AWS Solutions Architect Associate certification.
        """,
        source="sadhvi-profile"
    )
    print(f"Stored: {result}")

    print("\n--- Test 2: Retrieve context ---")
    chunks = retrieve_context("Tell me about Sadhvi's AWS experience")
    for chunk in chunks:
        print(f"Similarity: {chunk['similarity']:.2f}")
        print(f"Content: {chunk['content'][:100]}...")

    print("\n--- Test 3: Format context ---")
    context = format_context(chunks)
    print(context[:300])

    print("\n--- Test 4: List documents ---")
    docs = list_documents()
    print(f"Documents in RAG: {docs}")
