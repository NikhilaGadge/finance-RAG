"""Retrieval: find the chunks most similar to a question (top-k similarity search)."""

# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------
import chromadb                  # the vector database
from openai import OpenAI        # to embed the question

from app import config           # API key, model names, Chroma folder

COLLECTION_NAME = "press_releases"   # same name as in embed_chunks.py

# Connect once, when this file is imported (reused for every question)
_openai = OpenAI(api_key=config.OPENAI_API_KEY)
_collection = chromadb.PersistentClient(path=config.CHROMA_DIR).get_collection(COLLECTION_NAME)


# ---------------------------------------------------------------------------
# HELPER: question -> vector
# ---------------------------------------------------------------------------
def embed_query(text):
    """Embed a question with the SAME model used for the chunks."""
    response = _openai.embeddings.create(model=config.EMBEDDING_MODEL, input=[text])
    return response.data[0].embedding                    # one vector (1536 numbers)


# ---------------------------------------------------------------------------
# MAIN FUNCTION: top-k search
# ---------------------------------------------------------------------------
def retrieve(question, k=5, ticker=None):
    """
    Return the k chunks most similar to the question.

    question : the user's question, e.g. "What were BlackRock's net inflows?"
    k        : how many chunks to return
    ticker   : optional company filter, e.g. "BLK" -> only search BlackRock's chunks
    """
    where = {"ticker": ticker} if ticker else None       # metadata filter, or no filter

    results = _collection.query(
        query_embeddings=[embed_query(question)],        # the question as a vector
        n_results=k,                                     # top-k
        where=where,                                     # optional company filter
    )

    # Chroma returns lists-of-lists (one inner list per question); we asked one question -> [0]
    hits = []
    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        hits.append({
            "text": doc,                                 # the chunk text
            "distance": dist,                            # Chroma's distance (smaller = closer)
            # OpenAI vectors have length 1, so squared L2 distance = 2 - 2*cos  ->  cos = 1 - d/2
            "similarity": 1 - dist / 2,
            **meta,                                      # ticker, company, date, url, chunk_index
        })
    return hits


# ---------------------------------------------------------------------------
# Try it from the terminal:  uv run python -m app.retrieval "your question"
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys                                           # to read the question from the command line

    question = " ".join(sys.argv[1:]) or "What were BlackRock's net inflows?"   # default question
    print(f"Question: {question}\n")

    for i, hit in enumerate(retrieve(question), start=1):   # number the results 1, 2, 3, ...
        print(f"[{i}] {hit['ticker']} {hit['date']}  similarity={hit['similarity']:.3f}")
        print(f"    {hit['url']}")
        print("    " + hit["text"][:300].replace("\n", " "))   # first 300 characters, on one line
        print()