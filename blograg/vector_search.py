import logging
from typing import Any, List, Optional

import ollama
import structlog
from rich import print, rule
from sqlalchemy import Float, Integer, column, text
from sqlalchemy.orm import Session

from blograg.config import settings
from blograg.models import BlogPosts, session

logger = structlog.get_logger()
logging.basicConfig(level=logging.INFO)


def to_text(embedding: List[float]) -> str:
    return "[" + ",".join([str(float(v)) for v in embedding]) + "]"


def search(
    session: Session,
    query_text: Optional[str],
    query_vector: Optional[List[float]],
) -> List[Any]:
    """Search for blog posts using either full-text search or vector search.

    Inspired by Pamela Fox:
    https://github.com/pamelafox/learnlive-rag-starter/blob/179a3b98f7c1f71cf8be2638b80be4b47da66923/postgres_searcher.py#L42
    """
    table_name = BlogPosts.__tablename__
    vector_query = f"""
        SELECT id, RANK () OVER (ORDER BY embedding <=> :embedding) AS rank
            FROM {table_name}
            ORDER BY embedding <=> :embedding
            LIMIT 10
        """

    fulltext_query = f"""
        SELECT id, RANK () OVER (ORDER BY ts_rank_cd(to_tsvector('english', content), query) DESC)
            FROM {table_name}, plainto_tsquery('english', :query) query
            WHERE to_tsvector('english', content) @@ query
            ORDER BY ts_rank_cd(to_tsvector('english', content), query) DESC
            LIMIT 10
        """

    hybrid_query = f"""
    WITH vector_search AS (
        {vector_query}
    ),
    fulltext_search AS (
        {fulltext_query}
    )
    SELECT
        COALESCE(vector_search.id, fulltext_search.id) AS id,
        COALESCE(1.0 / (:k + vector_search.rank), 0.0) +
        COALESCE(1.0 / (:k + fulltext_search.rank), 0.0) AS score
    FROM vector_search
    FULL OUTER JOIN fulltext_search ON vector_search.id = fulltext_search.id
    ORDER BY score DESC
    LIMIT 10
    """

    if query_text is not None and query_vector is not None and len(query_vector) > 0:
        sql = text(hybrid_query).columns(column("id", Integer), column("score", Float))
    elif query_vector is not None and len(query_vector) > 0:
        sql = text(vector_query).columns(column("id", Integer), column("rank", Integer))
    elif query_text is not None:
        sql = text(fulltext_query).columns(
            column("id", Integer), column("rank", Integer)
        )
    else:
        raise ValueError("Both query text and query vector are empty")

    results = (
        session.execute(
            sql,
            {"embedding": to_text(query_vector or []), "query": query_text, "k": 60},
        )
    ).fetchall()

    return list(results)


query = "Get started in ham radio"
result = ollama.embed(model=settings.embed_model, input=query)
embedding = result.embeddings[0]

results = {
    "vector": search(session, None, list(embedding)),
    "fulltext": search(session, query, []),
    "hybrid": search(session, query, list(embedding)),
}
for search_type, search_result in results.items():
    print(rule.Rule(search_type))
    for row in search_result:
        # print(rule.Rule())
        post = session.query(BlogPosts).filter(BlogPosts.id == row[0]).first()
        if post:
            print(f"Post ID: {post.id}, Score: {row[1]}")
            print(f"Slug: {post.slug}")
            print(f"Content: {post.content[:100]}...")
        else:
            print(f"Post ID: {row[0]} not found.")
