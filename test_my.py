from dotenv import load_dotenv; load_dotenv()
from sqlalchemy import create_engine
import os
engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn: print("✅ MySQL connected successfully!")