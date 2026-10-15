# Finance-RAG

Ask questions about company press releases and get answers with cited sources.

> **Status: in development.** This README describes the planned scope. Items are checked off in the roadmap below as they are completed.

## Motivation

Press releases are long, repetitive and full of corporate language. Finding a specific figure or statement across hundreds of them is slow. This project builds a small Retrieval-Augmented Generation (RAG) service that:

1. retrieves the most relevant press-release passages for a question,
2. asks an LLM to answer **only** from those passages,
3. returns the answer together with the sources it was based on.

It extends my earlier work on [press releases and stock-market movement](https://github.com/NikhilaGadge/Press-Release-effect-on-Stock-markets) and on [hallucination detection in LLMs](https://github.com/NikhilaGadge/Multilingual-Token-Probability-Hallucination-Detection): the goal is not just to answer, but to answer faithfully to the source.

## How it works

```
press releases ──► chunking ──► embeddings ──► Chroma (vector store)
                                                     │
question ──► embedding ──► similarity search ────────┘
                                   │
                         top-k passages + question
                                   │
                                  LLM
                                   │
                       answer + cited sources (FastAPI /ask)
```

## Tech stack

| Component | Tool |
|---|---|
| Language | Python |
| API | FastAPI |
| Vector store | Chroma |
| Embeddings & generation | OpenAI API |
| Configuration | `.env` (API key never committed) |

## Roadmap

- [x] Repository setup, environment, `.env` handling
- [ ] Ingestion
  - [x] Download earnings press releases from SEC EDGAR (8-K, Item 2.02, Exhibit 99.1)
  - [ ] Chunk the text
  - [ ] Embed chunks and store them in Chroma
- [ ] Retrieval: top-k similarity search
- [ ] Generation: grounded prompt, answer with source citations
- [ ] FastAPI `/ask` endpoint
- [ ] Example questions and answers in this README
- [ ] Faithfulness check: how often answers are supported by the retrieved sources
- [ ] Improvements
  - [ ] Automatically detect old SEC company IDs (CIKs) after reorganizations (e.g. BlackRock before Oct 2024)
  - [ ] Table handling: extract tables with pandas, convert to Markdown/sentences, compare answer quality vs. flattened text
  - [ ] Skip already-downloaded files when re-running the downloader
- [ ] Optional: Docker container

## Data

Earnings press releases of five US-listed asset managers (BlackRock, State Street,
T. Rowe Price, Invesco, Franklin Templeton), downloaded from SEC EDGAR.
Downloaded files are stored locally in `data/raw/` and not committed.

## Author

Nikhila Gadge

