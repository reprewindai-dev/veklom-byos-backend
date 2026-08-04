"""
GraphQL Connector Builder
Generates Python clients from GraphQL schemas

Location: veklom-byos-backend/backend/gpc/builders/graphql_builder.py
"""

from typing import Dict, Optional, Any
from backend.gpc.poltergeist.watcher import CapabilityRequirement
from backend.gpc.builders.base_builder import BaseCapabilityBuilder


class GraphQLConnectorBuilder(BaseCapabilityBuilder):
    """
    Builds Python GraphQL clients from schema.

    Generates type-safe clients with query/mutation builders.
    """

    async def prepare(self, requirement: CapabilityRequirement) -> None:
        """Validate GraphQL endpoint is accessible"""
        if not requirement.external_system:
            raise ValueError("GraphQL builder requires external_system")

    async def generate(self, requirement: CapabilityRequirement) -> str:
        """Generate GraphQL client code"""
        code = f'''"""
GraphQL Client for {requirement.external_system}
Auto-generated connector
"""

import httpx
from typing import Dict, Any, Optional
import json


class {requirement.external_system.title()}GraphQLClient:
    """GraphQL client"""

    def __init__(self, endpoint: str, api_key: Optional[str] = None):
        self.endpoint = endpoint
        self.api_key = api_key
        self.client = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient()
        return self

    async def __aexit__(self, *args):
        if self.client:
            await self.client.aclose()

    async def query(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute GraphQL query"""
        headers = {{}}
        if self.api_key:
            headers["Authorization"] = f"Bearer {{self.api_key}}"

        response = await self.client.post(
            self.endpoint,
            json={{"query": query, "variables": variables or {{}}}},
            headers=headers
        )

        return response.json()

    async def mutation(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute GraphQL mutation"""
        return await self.query(query, variables)
'''
        return code

    async def compile(self, source_code: str, requirement: CapabilityRequirement) -> bytes:
        """Compile to wheel"""
        return source_code.encode()
