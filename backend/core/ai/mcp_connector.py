import re
import httpx
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class OpenAPItoMCPTranslator:
    @staticmethod
    async def fetch_schema(openapi_url: str) -> Optional[Dict[str, Any]]:
        """Fetch OpenAPI schema from URL."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(openapi_url)
                if response.status_code == 200:
                    return response.json()
                logger.error(f"Failed to fetch openapi schema: HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching openapi schema: {e}")
        return None

    @classmethod
    def translate_schema(cls, schema: Dict[str, Any], server_id: str) -> List[Dict[str, Any]]:
        """Translate OpenAPI schema JSON into a list of MCP-compatible tools."""
        mcp_tools = []
        paths = schema.get("paths", {})
        components = schema.get("components", {})
        schemas = components.get("schemas", {})

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() not in ("get", "post", "put", "delete", "patch"):
                    continue

                operation_id = operation.get("operationId")
                if not operation_id:
                    # Fallback to path and method
                    clean_path = re.sub(r'[{}]', '', path).replace("/", "_").strip("_")
                    operation_id = f"{method.lower()}_{clean_path}"

                # Namespacing tool name to avoid collisions
                tool_name = f"{server_id}_{operation_id}"
                description = operation.get("summary") or operation.get("description") or f"Execute {method.upper()} on {path}"
                
                input_schema = cls._build_input_schema(method, operation, schemas)

                mcp_tools.append({
                    "name": tool_name,
                    "description": description,
                    "inputSchema": input_schema,
                    "method": method.upper(),
                    "path": path,
                    "price_usdc": 0.010, # Standard pricing for custom plugins
                })

        return mcp_tools

    @classmethod
    def _build_input_schema(cls, method: str, operation: Dict[str, Any], schemas: Dict[str, Any]) -> Dict[str, Any]:
        """Build input schema parameters for the MCP tool based on OpenAPI spec."""
        input_properties = {}
        required_fields = []

        # 1. Parse path/query parameters
        parameters = operation.get("parameters", [])
        for param in parameters:
            name = param.get("name")
            param_schema = param.get("schema", {})
            param_desc = param.get("description", "")
            
            # Resolve refs if needed
            if "$ref" in param_schema:
                param_schema = cls._resolve_ref(param_schema["$ref"], schemas)

            prop = {
                "type": param_schema.get("type", "string"),
                "description": param_desc or f"Query parameter: {name}"
            }
            if "default" in param_schema:
                prop["default"] = param_schema["default"]
            if "enum" in param_schema:
                prop["enum"] = param_schema["enum"]

            input_properties[name] = prop
            if param.get("required", False):
                required_fields.append(name)

        # 2. Parse requestBody parameters (typically for POST/PUT)
        request_body = operation.get("requestBody", {})
        content = request_body.get("content", {})
        json_content = content.get("application/json", {})
        body_schema = json_content.get("schema", {})

        if "$ref" in body_schema:
            body_schema = cls._resolve_ref(body_schema["$ref"], schemas)

        if body_schema:
            body_type = body_schema.get("type", "object")
            if body_type == "object":
                properties = body_schema.get("properties", {})
                for name, prop_schema in properties.items():
                    if "$ref" in prop_schema:
                        prop_schema = cls._resolve_ref(prop_schema["$ref"], schemas)
                    
                    prop = {
                        "type": prop_schema.get("type", "string"),
                        "description": prop_schema.get("description", "") or f"Body property: {name}"
                    }
                    if "default" in prop_schema:
                        prop["default"] = prop_schema["default"]
                    if "enum" in prop_schema:
                        prop["enum"] = prop_schema["enum"]

                    input_properties[name] = prop
                
                body_required = body_schema.get("required", [])
                required_fields.extend(body_required)
            else:
                input_properties["body"] = {
                    "type": body_type,
                    "description": "Raw request body payload"
                }

        schema = {
            "type": "object",
            "properties": input_properties,
            "additionalProperties": False
        }
        if required_fields:
            schema["required"] = list(set(required_fields))
        return schema

    @classmethod
    def _resolve_ref(cls, ref: str, schemas: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a schema reference like #/components/schemas/Name."""
        if not ref.startswith("#/components/schemas/"):
            return {}
        schema_name = ref.split("/")[-1]
        return schemas.get(schema_name, {})
