from contextlib import contextmanager

from flask_sqlalchemy import BaseQuery
from flask_sqlalchemy.session import Session
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

from tools import config

url = config.DATABASE_URI
options = config.db_engine_config
engine = create_engine(url, **options)
session = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()
Base.query = session.query_property(query_cls=BaseQuery)


def get_shared_metadata():
    meta = MetaData()
    for table in Base.metadata.tables.values():
        if table.schema != "tenant":
            table.tometadata(meta)
    return meta


def get_tenant_specific_metadata():
    meta = MetaData(schema="tenant")
    for table in Base.metadata.tables.values():
        if table.schema == "tenant":
            table.tometadata(meta)
    return meta


def get_project_schema_session(project_id: int | None):
    if project_id:
        schema_translate_map = dict(tenant=f"Project-{project_id}")
    else:
        schema_translate_map = None

    connectable = engine.execution_options(schema_translate_map=schema_translate_map)
    return scoped_session(sessionmaker(bind=connectable))


@contextmanager
def with_project_schema_session(project_id: int | None):
    if project_id:
        schema_translate_map = dict(tenant=f"Project-{project_id}")
    else:
        schema_translate_map = None

    connectable = engine.execution_options(schema_translate_map=schema_translate_map)

    try:
        db = scoped_session(sessionmaker(bind=connectable))
        yield db
    finally:
        db.close()
