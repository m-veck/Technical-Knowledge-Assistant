"""Turn texts into vectors with the embedding provider and model set in config.py."""

import os

import cohere

from tka import config


def embed_documents(texts: list[str]) -> tuple[list[list[float]], int]:
    """Embed texts for the index. Returns one vector per text and the number of billed tokens."""
    if config.EMBED_PROVIDER != "cohere":
        raise SystemExit(f"Unknown embedding provider in config.py: {config.EMBED_PROVIDER}")
    api_key = os.environ.get("COHERE_API_KEY")
    if not api_key:
        raise SystemExit("COHERE_API_KEY is missing: put it in .env (see .env.example).")

    client = cohere.ClientV2(api_key=api_key)
    response = client.embed(
        texts=texts,
        model=config.EMBED_MODEL,
        input_type="search_document",  # questions will use "search_query"
        embedding_types=["float"],
        output_dimension=config.EMBEDDING_DIM,
    )
    return response.embeddings.float_, int(response.meta.billed_units.input_tokens)
