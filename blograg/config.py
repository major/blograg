"""Settings for the blograg package."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    embed_model: str = "nomic-embed-text"
    blog_post_dir: str = "major.io/content/posts"
    postgres_url: str = "postgresql+psycopg2://postgres:secrete@127.0.0.1/ragdb"


settings = Settings()
