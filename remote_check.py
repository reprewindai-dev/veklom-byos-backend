import os
from sqlalchemy import create_engine, text
db_url = "postgresql://byos:WZk0WzseaPma1_KsJ53Nr7OgMUhnk9EV@llwfyzhnft87bz6brddiax1z:5432/byos_ai"
engine = create_engine(db_url)
with engine.connect() as conn:
    query = text("SELECT email, password_hash FROM users WHERE email='studiogradekits@gmail.com'")
    row = conn.execute(query).fetchone()
    print(row)
