# ----- QDRANT SETUP ------------
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.config import get_settings

COLLECTION_NAME = "kubernetes_docs"

VECTOR_SIZE = 1536


def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(
        url=settings.qdrant_cluster_endpoint, api_key=settings.qdrant_api_key
    )


def create_collection():
    client = get_qdrant_client()
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )
    print(f"Created collection '{COLLECTION_NAME}'")


# ---- QDRANT SETUP ENDs --------------

# ------- Now Embeddings Creation ----------

from openai import OpenAI
from qdrant_client.models import PointStruct
import uuid

EMBEDDING_MODEL = "text-embedding-3-small"


def get_openai_client() -> OpenAI:
    settings = get_settings()
    return OpenAI(api_key=settings.openai_api_key)


def embed_texts(texts: list[str]) -> list[list[float]]:
    client = get_openai_client()
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


def upload_chunks(chunks: list[dict]):
    texts = [chunk["text"] for chunk in chunks]
    vectors = embed_texts(texts)

    points = []
    for chunk, vector in zip(chunks, vectors):
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={"text": chunk["text"], "source": chunk["source"]},
        )
        points.append(point)

    client = get_qdrant_client()
    client.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"Uploaded {len(points)} chunks to Qdrant")


# -------  Embeddings Created  ----------

## -------- Retrieval Check [testing] ------------


def search(query: str, top_k: int = 5) -> list[dict]:
    query_vector = embed_texts([query])[0]

    client = get_qdrant_client()
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=top_k,
    )

    return [
        {
            "text": point.payload["text"],
            "source": point.payload["source"],
            "score": point.score,
        }
        for point in results.points
    ]


# ----- Rerank -------------------


import cohere

RERANK_MODEL = "rerank-v3.5"


def get_cohere_client() -> cohere.ClientV2:
    settings = get_settings()
    return cohere.ClientV2(api_key=settings.cohere_api_key)


def rerank(query: str, chunks: list[dict], top_n: int = 5) -> list[dict]:
    client = get_cohere_client()
    documents = [chunk["text"] for chunk in chunks]

    response = client.rerank(
        model=RERANK_MODEL,
        query=query,
        documents=documents,
        top_n=top_n,
    )

    reranked = []
    for result in response.results:
        original_chunk = chunks[result.index]
        reranked.append(
            {
                "text": original_chunk["text"],
                "source": original_chunk["source"],
                "relevance_score": result.relevance_score,
            }
        )
    return reranked
