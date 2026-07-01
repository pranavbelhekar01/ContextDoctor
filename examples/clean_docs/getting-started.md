# Getting Started with Acme Search

Acme Search is a retrieval engine for building question-answering systems. This
guide walks you through installing Acme Search, indexing your first corpus, and
running a query. Each section is self-contained so that a retriever can surface
it without losing important context.

## Installation

Install Acme Search from PyPI. The package ships with sensible defaults and does
not require a GPU for small corpora. After installation, verify the version to
confirm that the command-line tools are available on your system path.

## Indexing a Corpus

To index a corpus, point Acme Search at a directory of documents. Acme Search
reads each document, splits it into passages, and stores vector embeddings in a
local index. Indexing is incremental, so re-running the command only processes
files that changed since the last run.

## Running a Query

Once indexing finishes, run a query against the Acme Search index. The engine
returns the most relevant passages ranked by similarity. You can tune the number
of results and the similarity threshold to trade recall for precision depending
on your application's needs.
