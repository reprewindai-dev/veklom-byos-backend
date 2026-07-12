from typing import Any, Dict
import asyncio
import logging

from .base import CapabilityBuilder

logger = logging.getLogger("poltergeist_database_builder")

class DatabaseAdapterBuilder(CapabilityBuilder):
    """
    Manufactures a capability for connecting to relational or NoSQL databases.
    Generates SQLAlchemy/PyMongo style connector code.
    """
    
    async def generate_source(self) -> str:
        """
        Generates database connection and query execution code.
        """
        logger.info(f"[{self.fingerprint}] Generating database adapter source")
        
        await asyncio.sleep(1.5)
        
        db_type = self.manifest.get("db_type", "postgresql")
        
        if db_type == "postgresql":
            source_code = '''
import sqlalchemy
from typing import Dict, Any, List

class PostgreSQLAdapter:
    def __init__(self, connection_string: str):
        self.engine = sqlalchemy.create_engine(connection_string)
        
    def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Executes a parameterized SQL query safely."""
        with self.engine.connect() as connection:
            result = connection.execute(sqlalchemy.text(query), parameters or {})
            
            # Fetch all results as dictionaries
            return [dict(row) for row in result.mappings()]
'''
        else:
            source_code = '''
class GenericDBAdapter:
    def __init__(self):
        pass
    def execute(self):
        raise NotImplementedError("Unsupported DB type")
'''
        return source_code.strip()

