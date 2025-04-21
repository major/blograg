from pgvector.sqlalchemy import Vector  # type: ignore
from sqlalchemy import Index, String, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class BlogPosts(Base):
    __tablename__ = "blogposts"
    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(String)
    embedding = mapped_column(Vector(768))
    slug: Mapped[str] = mapped_column(String)

    def __repr__(self) -> str:
        return f"<BlogPosts(id={self.id}, content={self.content})>"


index = Index(
    "hnsw_index_for_innerproduct_items_embedding",
    BlogPosts.embedding,
    postgresql_using="hnsw",
    postgresql_with={"m": 16, "ef_construction": 64},
    postgresql_ops={"embedding": "vector_ip_ops"},
)

engine = create_engine(
    "postgresql+psycopg2://postgres:secrete@127.0.0.1/ragdb", echo=False
)
Session = sessionmaker(bind=engine)
session = Session()

session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

BlogPosts.metadata.create_all(engine)
