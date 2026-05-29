from __future__ import annotations

import sqlite3
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.api.config import get_settings


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def database_url() -> str:
    return get_settings().sqlalchemy_database_url


def stamp_legacy_sqlite_schema() -> None:
    settings = get_settings()
    if not settings.uses_sqlite or not settings.database_path.exists():
        return
    with sqlite3.connect(settings.database_path) as conn:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
        if "cases" not in tables:
            return
        if "alembic_version" not in tables:
            conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        current = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        if current is None:
            conn.execute("INSERT INTO alembic_version (version_num) VALUES (?)", ("0001_initial_schema",))


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    stamp_legacy_sqlite_schema()
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = database_url()
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
