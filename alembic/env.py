from alembic import context
from sqlalchemy import create_engine

from tracks.config import get_settings
from tracks.models import Base

# L'URL peut être imposée (tests) ; sinon on prend celle de la configuration.
url = context.config.get_main_option("sqlalchemy.url") or get_settings().database_url

with create_engine(url).connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
