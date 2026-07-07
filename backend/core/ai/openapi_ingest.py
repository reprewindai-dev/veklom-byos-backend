import re
import httpx
import logging
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class OpenAPICompiler:
    """Compiles OpenAPI specs into V1 MCP tool manifests."""
    
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
    def compile_manifest(cls, schema: Dict[str, Any], server_id: str, openapi_url: str) -> List[Dict[str, Any]]:
        """Compile an OpenAPI schema into a list of normalized tool manifests."""
        manifests = []
        paths = schema.get("paths", {})
        components = schema.get("components", {})
        schemas = components.get("schemas", {})

        # Compute hash
        import json
        spec_hash = hashlib.sha256(json.dumps(schema, sort_keys=True).encode("utf-8")).hexdigest()
        manifest_version = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() not in ("get", "post", "put", "delete", "patch"):
                    continue

                # Filter out unsupported routes
                if cls._has_unsupported_patterns(operation):
                    logger.warning(f"Skipping unsupported route: {method.upper()} {path}")
                    continue

                operation_id = operation.get("operationId")
                if not operation_id:
                    clean_path = re.sub(r'[{}]', '', path).replace("/", "_").strip("_")
                    operation_id = f"{method.lower()}_{clean_path}"

                tool_name = f"{server_id}__{operation_id}"
                summary = operation.get("summary") or f"Execute {method.upper()} on {path}"
                description = operation.get("description") or summary
                
                input_schema = cls._build_input_schema(method, operation, schemas)
                
                tags = operation.get("tags", [])
                
                manifest = {
                    "tool_name": tool_name,
                    "display_name": summary,
                    "server_id": server_id,
                    "manifest_version": manifest_version,
                    "source_spec_hash": f"sha256:{spec_hash}",
                    "operation_id": operation_id,
                    "summary": summary,
                    "description": description,
                    "tags": tags,
                    "method": method.upper(),
                    "path_template": path,
                    "base_url_ref": f"server:{server_id}",
                    "input_schema": input_schema,
                    "output_schema": {"type": "object"}, # Simplified for V1
                    "auth_profile": {
                        "scheme": "bearer",
                        "credential_ref": f"vault://tenant/{server_id}/credential"
                    },
                    "billing_profile": {
                        "billable": True,
                        "cost_class": "standard",
                        "x402_required": True
                    },
                    "risk_profile": {
                        "risk_class": "read_only" if method.lower() == "get" else "write",
                        "approval_required": False,
                        "environment": "prod"
                    },
                    "execution_profile": {
                        "timeout_ms": 15000,
                        "retry_policy": "idempotent-read" if method.lower() == "get" else "none",
                        "cache_class": "hotpath" if method.lower() == "get" else "none"
                    },
                    "conversion_notes": {
                        "flattened_request": True,
                        "refs_resolved": True,
                        "unsupported_features": []
                    }
                }
                
                manifests.append(manifest)

        return manifests

    @classmethod
    def _has_unsupported_patterns(cls, operation: Dict[str, Any]) -> bool:
        """Check if an operation contains features we do not support in V1 (streaming, multipart)."""
        request_body = operation.get("requestBody", {})
        content = request_body.get("content", {})
        
        # Reject multipart/form-data
        if "multipart/form-data" in content:
            return True
        
        # Reject generic file uploads if explicitly marked
        if "application/octet-stream" in content:
            return True
            
        return False

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
            
            if "$ref" in param_schema:
                param_schema = cls._resolve_ref(param_schema["$ref"], schemas)

            prop = {
                "type": param_schema.get("type", "string"),
                "description": param_desc or f"Parameter: {name}"
            }
            if "default" in param_schema:
                prop["default"] = param_schema["default"]
            if "enum" in param_schema:
                prop["enum"] = param_schema["enum"]

            input_properties[name] = prop
            if param.get("required", False) or param.get("in") == "path":
                required_fields.append(name)

        # 2. Parse requestBody parameters
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
                required_fields.append("body")

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
