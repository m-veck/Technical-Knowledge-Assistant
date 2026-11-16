"""Turn texts into vectors with the embedding provider and models set in config.py."""

import os

import cohere

from tka import config


def cohere_client() -> cohere.ClientV2:
    """A Cohere client, with a clear message if the provider or the API key is not set up."""
    if config.EMBED_PROVIDER != "cohere":
        raise SystemExit(f"Unknown embedding provider in config.py: {config.EMBED_PROVIDER}")
    api_key = os.environ.get("COHERE_API_KEY")
    if not api_key:
        raise SystemExit("COHERE_API_KEY is missing: put it in .env (see .env.example).")
    return cohere.ClientV2(api_key=api_key)


def embed_documents(texts: list[str]) -> tuple[list[list[float]], int]:
    """Embed texts for the index. Returns one vector per text and the number of billed tokens."""
    response = cohere_client().embed(
        texts=texts,
        model=config.EMBED_MODEL,
        input_type="search_document",
        embedding_types=["float"],
        output_dimension=config.EMBEDDING_DIM,
    )
    return response.embeddings.float_, int(response.meta.billed_units.input_tokens)


def embed_query(question: str) -> list[float]:
    """Embed one question for searching the index."""
    response = cohere_client().embed(
        texts=[question],
        model=config.QUERY_EMBED_MODEL,
        input_type="search_query",
        embedding_types=["float"],
        output_dimension=config.EMBEDDING_DIM,
    )
    return response.embeddings.float_[0]
