"""Weaviate vector store module for document embedding and retrieval.

Uses Gemini embeddings to vectorize documents and stores them in Weaviate.
Supports semantic search for first-pass candidate retrieval.
"""

import json
import logging
from typing import Any

import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.query import MetadataQuery
from google import genai

from doc_search_with_reranking_validation.config import (
    WEAVIATE_URL,
    WEAVIATE_API_KEY,
    WEAVIATE_COLLECTION,
    GOOGLE_API_KEY,
    EMBEDDING_MODEL,
    TOP_K_FIRST_PASS,
)

logger = logging.getLogger(__name__)


def _get_weaviate_client() -> weaviate.WeaviateClient:
    """Create and return a Weaviate client."""
    if WEAVIATE_API_KEY:
        auth = weaviate.auth.AuthApiKey(WEAVIATE_API_KEY)
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=WEAVIATE_URL,
            auth_credentials=auth,
        )
    else:
        client = weaviate.connect_to_local(
            host=WEAVIATE_URL.replace("http://", "").replace("https://", "").split(":")[0],
            port=int(WEAVIATE_URL.split(":")[-1]) if ":" in WEAVIATE_URL.split("//")[-1] else 8080,
        )
    return client


def _get_genai_client() -> genai.Client:
    """Create and return a Google GenAI client."""
    return genai.Client(api_key=GOOGLE_API_KEY)


def generate_embedding(text: str) -> list[float]:
    """Generate an embedding vector for the given text using Gemini.

    Args:
        text: The text to embed.

    Returns:
        A list of floats representing the embedding vector.
    """
    client = _get_genai_client()
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
    )
    return result.embeddings[0].values


def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embedding vectors for a batch of texts.

    Args:
        texts: List of texts to embed.

    Returns:
        List of embedding vectors.
    """
    client = _get_genai_client()
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
    )
    return [e.values for e in result.embeddings]


def ensure_collection_exists() -> None:
    """Ensure the Weaviate collection exists, creating it if needed."""
    client = _get_weaviate_client()
    try:
        if not client.collections.exists(WEAVIATE_COLLECTION):
            client.collections.create(
                name=WEAVIATE_COLLECTION,
                vectorizer_config=Configure.Vectorizer.none(),
                properties=[
                    Property(name="doc_id", data_type=DataType.TEXT),
                    Property(name="title", data_type=DataType.TEXT),
                    Property(name="content", data_type=DataType.TEXT),
                    Property(name="source", data_type=DataType.TEXT),
                    Property(name="metadata", data_type=DataType.TEXT),
                ],
            )
            logger.info("Created Weaviate collection: %s", WEAVIATE_COLLECTION)
        else:
            logger.info("Weaviate collection already exists: %s", WEAVIATE_COLLECTION)
    finally:
        client.close()


def ingest_documents(documents: list[dict[str, Any]]) -> int:
    """Ingest documents into the Weaviate vector store.

    Each document should have:
        - doc_id: Unique identifier
        - title: Document title
        - content: Full document text
        - source: Source reference (optional)
        - metadata: Additional metadata as dict (optional)

    Args:
        documents: List of document dictionaries.

    Returns:
        Number of documents successfully ingested.
    """
    ensure_collection_exists()

    # Generate embeddings for all documents
    texts_to_embed = [
        f"{doc.get('title', '')} {doc.get('content', '')}" for doc in documents
    ]
    embeddings = generate_embeddings_batch(texts_to_embed)

    client = _get_weaviate_client()
    try:
        collection = client.collections.get(WEAVIATE_COLLECTION)
        count = 0

        with collection.batch.dynamic() as batch:
            for doc, embedding in zip(documents, embeddings):
                metadata = doc.get("metadata", {})
                if isinstance(metadata, dict):
                    metadata = json.dumps(metadata)

                batch.add_object(
                    properties={
                        "doc_id": doc.get("doc_id", ""),
                        "title": doc.get("title", ""),
                        "content": doc.get("content", ""),
                        "source": doc.get("source", ""),
                        "metadata": metadata,
                    },
                    vector=embedding,
                )
                count += 1

        logger.info("Ingested %d documents into Weaviate", count)
        return count
    finally:
        client.close()


def semantic_search(query: str, top_k: int = TOP_K_FIRST_PASS) -> list[dict[str, Any]]:
    """Perform semantic search against the vector store.

    Args:
        query: The search query text.
        top_k: Number of top results to return.

    Returns:
        List of matching documents with similarity scores.
    """
    query_embedding = generate_embedding(query)

    client = _get_weaviate_client()
    try:
        collection = client.collections.get(WEAVIATE_COLLECTION)
        results = collection.query.near_vector(
            near_vector=query_embedding,
            limit=top_k,
            return_metadata=MetadataQuery(distance=True),
        )

        matched_docs = []
        for obj in results.objects:
            metadata_str = obj.properties.get("metadata", "{}")
            try:
                metadata = json.loads(metadata_str) if metadata_str else {}
            except (json.JSONDecodeError, TypeError):
                metadata = {}

            matched_docs.append({
                "doc_id": obj.properties.get("doc_id", ""),
                "title": obj.properties.get("title", ""),
                "content": obj.properties.get("content", ""),
                "source": obj.properties.get("source", ""),
                "metadata": metadata,
                "similarity_score": 1 - (obj.metadata.distance or 0),
            })

        logger.info("Semantic search returned %d results for query", len(matched_docs))
        return matched_docs
    finally:
        client.close()


def delete_collection() -> None:
    """Delete the Weaviate collection (useful for resetting)."""
    client = _get_weaviate_client()
    try:
        if client.collections.exists(WEAVIATE_COLLECTION):
            client.collections.delete(WEAVIATE_COLLECTION)
            logger.info("Deleted Weaviate collection: %s", WEAVIATE_COLLECTION)
    finally:
        client.close()


def get_document_count() -> int:
    """Get the total number of documents in the collection."""
    client = _get_weaviate_client()
    try:
        if not client.collections.exists(WEAVIATE_COLLECTION):
            return 0
        collection = client.collections.get(WEAVIATE_COLLECTION)
        result = collection.aggregate.over_all(total_count=True)
        return result.total_count or 0
    finally:
        client.close()