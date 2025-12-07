from __future__ import annotations

import os
from typing import Optional

from neo4j import GraphDatabase, Driver


_driver: Optional[Driver] = None


def get_neo4j_driver() -> Driver:
    """Singleton-style accessor for the Neo4j driver.

    Uses environment variables configured in backend/knowledge/.env:
    - NEO4J_URI
    - NEO4J_USER
    - NEO4J_PASSWORD
    - NEO4J_DB (optional, defaults to "neo4j")
    """

    global _driver

    if _driver is None:
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER")
        password = os.getenv("NEO4J_PASSWORD")
        db_name = os.getenv("NEO4J_DB", "neo4j")

        if not uri or not user or not password:
            raise RuntimeError("Neo4j configuration is missing. Please set NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD.")

        _driver = GraphDatabase.driver(uri, auth=(user, password), database=db_name)

    return _driver


def close_neo4j_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
