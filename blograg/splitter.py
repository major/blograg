import logging
from pathlib import Path

import frontmatter  # type: ignore
import ollama
import structlog
from unstructured.partition.md import partition_md

from blograg.config import settings
from blograg.models import BlogPosts, engine, session

logger = structlog.get_logger()
logging.basicConfig(level=logging.WARNING)

# Drop/create tables each time this script runs
BlogPosts.metadata.drop_all(engine)
BlogPosts.metadata.create_all(engine)

# Gather the blog posts.
posts_files = Path(settings.blog_post_dir).rglob("*.md")

for post_file in posts_files:
    logger.info(f"Processing {post_file}")

    # Extract the YAML frontmatter.
    post = frontmatter.load(post_file)

    # Use the slug as a unique identifier.
    if "slug" not in post:
        post_slug = post_file.parent.name
    else:
        post_slug = post["slug"]

    # Split the document into sections.
    elements = partition_md(
        text=post.content,
        chunking_strategy="by_title",
        max_characters=2000,
        overlap=100,
    )

    # Generate embeddings.
    result = ollama.embed(
        model=settings.embed_model,
        input=[x.text for x in elements],
    )

    # Use the original test and the embedding to create a record.
    for index, element in enumerate(elements):
        if index < len(result.embeddings):
            record = BlogPosts(
                embedding=result.embeddings[index],
                content=element.text,
                slug=post_slug,
            )
            session.add(record)

# Commit once at the end to speed up the process.
session.commit()
