# test_models.py
from sqlalchemy import text
from database import engine
import models  # just importing registers the mappings

with engine.connect() as conn:
    # Try reading counts from a couple of tables
    for tbl in ["organizations", "users", "documents", "document_chunks"]:
        n = conn.execute(text(f"SELECT count(*) FROM {tbl}")).scalar_one()
        print(tbl, n)
