# backend/create_tables.py
from sqlalchemy import create_engine
from backend.config import get_settings
from backend.models import Base

settings = get_settings()
user = settings.MYSQL_USER
pw = settings.MYSQL_PASSWORD
host = settings.MYSQL_HOST
port = settings.MYSQL_PORT
db = settings.MYSQL_DB

url = f"mysql+pymysql://{user}:{pw}@{host}:{port}/{db}"
# create DB if not exists (requires root privileges); simpler: connect to mysql and create manually
engine = create_engine(url, echo=True)
Base.metadata.create_all(engine)
print("Tables created or verified.")
