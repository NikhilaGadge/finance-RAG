"""Embed chunks with OpenAI and store them in a local Chroma vector database."""

import json                      
from pathlib import Path         

import chromadb                  # the vector database
from openai import OpenAI        # client for the OpenAI API

from app import config           # our settings: API key, model name, Chroma folder


CHUNKS_FILE = Path("data/processed/chunks.jsonl")   # output of chunk_documents.py
COLLECTION_NAME = "press_releases"                   # name of the "table" inside Chroma
BATCH_SIZE = 100                                     # chunks sent to OpenAI per request


# ---------------------------------------------------------------------------
# HELPER: cut a list into pieces of `size`
# ---------------------------------------------------------------------------
def batches(items, size):
    """Yield items[0:100], items[100:200], ... one batch at a time."""
    for start in range(0, len(items), size):        # start = 0, 100, 200, ...
        yield items[start:start + size]             # hand out one slice


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    # 1. Load all chunks (one JSON object per line)
    with open(CHUNKS_FILE, encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f]
    print(f"Loaded {len(chunks)} chunks")

    # 2. Connect to OpenAI and to Chroma
    openai_client = OpenAI(api_key=config.OPENAI_API_KEY)               # uses the key from .env
    chroma_client = chromadb.PersistentClient(path=config.CHROMA_DIR)   # saves to the chroma_db/ folder
    collection = chroma_client.get_or_create_collection(COLLECTION_NAME)  # create it, or reuse it if it exists

    # 3. Embed and store, batch by batch
    for batch in batches(chunks, BATCH_SIZE):
        texts = [c["text"] for c in batch]                              # the texts of this batch

        # Ask OpenAI for one vector per text
        response = openai_client.embeddings.create(
            model=config.EMBEDDING_MODEL,                               # "text-embedding-3-small"
            input=texts,
        )
        vectors = [item.embedding for item in response.data]            # list of vectors (1536 numbers each)

        # Save text + vector + metadata in Chroma
        collection.upsert(                                              # upsert = add, or replace if the ID exists
            ids=[c["id"] for c in batch],                               # e.g. "BLK_2024-10-11_004"
            embeddings=vectors,                                         # the vectors from OpenAI
            documents=texts,                                            # the original text (returned when searching)
            metadatas=[                                                 # extra info per chunk, used for citations/filters
                {key: c[key] for key in ("ticker", "company", "date", "url", "chunk_index")}
                for c in batch
            ],
        )
        print(f"  stored {len(batch)} chunks")

    # 4. Final check: how many chunks are in the database now?
    print(f"Done: collection '{COLLECTION_NAME}' now has {collection.count()} chunks")


# Run main() only when this file is started directly
if __name__ == "__main__":
    main()
