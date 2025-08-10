from database import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        for row in result:
            print(f"✅ Connected to: {row[0]}")
except Exception as e:
    print(f"❌ Connection failed: {e}")
