"""Split downloaded press releases into overlapping chunks, ready for embedding."""

import json                      
import re                        
from pathlib import Path         

RAW_DIR = Path("data/raw")              # where download_edgar.py saved the .txt files
OUT_DIR = Path("data/processed")        # where the chunks will be saved
CHUNK_SIZE = 1500                       # max characters per chunk (~300 words, ~375 tokens)
CHUNK_OVERLAP = 200                     


# ---------------------------------------------------------------------------
# HELPER 1: break the text into small pieces (lines, or sentences for long lines)
# ---------------------------------------------------------------------------
def split_into_units(text):
    """Return a list of lines; lines longer than CHUNK_SIZE are split into sentences."""
    units = []                                              # the small pieces we'll build chunks from
    for line in text.splitlines():                          # go through the text line by line
        if len(line) <= CHUNK_SIZE:                         # normal line: fits into a chunk ...
            units.append(line)                              # ... keep it as one unit
        else:                                               # very long line (a big paragraph):
            # split after ".", "!" or "?" followed by a space -> one unit per sentence
            units.extend(re.split(r"(?<=[.!?])\s+", line))
    return units


# ---------------------------------------------------------------------------
# HELPER 2: glue units together into overlapping chunks
# ---------------------------------------------------------------------------
def split_into_chunks(text):
    """Collect whole lines until a chunk is full; start the next chunk with some overlap."""
    chunks = []                                             # finished chunks
    current = []                                            # lines in the chunk we're building
    current_len = 0                                         # its length in characters

    for unit in split_into_units(text):
        # Would adding this unit make the chunk too long? Then close the current chunk first.
        if current and current_len + len(unit) + 1 > CHUNK_SIZE:   # +1 for the line break
            chunks.append("\n".join(current))               # save the finished chunk

            # Overlap: take lines from the END of the finished chunk (up to CHUNK_OVERLAP chars)
            overlap, overlap_len = [], 0
            for prev in reversed(current):                  # walk backwards from the last line
                if overlap_len + len(prev) + 1 > CHUNK_OVERLAP:
                    break                                   # overlap is full -> stop
                overlap.insert(0, prev)                     # put it at the front (keeps original order)
                overlap_len += len(prev) + 1
            current, current_len = overlap, overlap_len     # the new chunk starts with the overlap

        current.append(unit)                                # add the unit to the chunk
        current_len += len(unit) + 1                        # update the length

    if current:                                             # whatever is left at the end ...
        chunks.append("\n".join(current))                   # ... becomes the last chunk
    return chunks


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)              # create data/processed if needed

    # Read the metadata the downloader saved: one JSON object per line
    with open(RAW_DIR / "metadata.jsonl", encoding="utf-8") as f:
        records = [json.loads(line) for line in f]

    total = 0                                               # total number of chunks
    with open(OUT_DIR / "chunks.jsonl", "w", encoding="utf-8") as out:
        for rec in records:                                 # one press release at a time
            text = (RAW_DIR / rec["file"]).read_text(encoding="utf-8")   # load its text

            # Header added to every chunk, so each chunk says which company/date it's from
            header = f"{rec['company']} ({rec['ticker']}) earnings press release, filed {rec['date']}"

            chunks = split_into_chunks(text)                # split the press release
            for i, chunk in enumerate(chunks):              # i = 0, 1, 2, ... (chunk number)
                out.write(json.dumps({
                    "id": f"{rec['ticker']}_{rec['date']}_{i:03d}",   # unique ID, e.g. BLK_2024-10-11_004
                    "text": f"{header}\n\n{chunk}",         # the text that will be embedded
                    "ticker": rec["ticker"],                # metadata, kept for filtering ...
                    "company": rec["company"],
                    "date": rec["date"],
                    "url": rec["url"],                      # ... and for citations
                    "chunk_index": i,                       # position of the chunk in the document
                }) + "\n")

            print(f"{rec['file']}: {len(chunks)} chunks")   # progress per press release
            total += len(chunks)

    print(f"Done: {total} chunks saved to {OUT_DIR / 'chunks.jsonl'}")


# Run main() only when this file is started directly
if __name__ == "__main__":
    main()