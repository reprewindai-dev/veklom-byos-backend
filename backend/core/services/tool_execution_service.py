"""Real Tool Execution Service - Production Implementation"""

import json
import asyncio
import subprocess
import tempfile
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import httpx
import sqlite3
import pandas as pd
from datetime import datetime, timezone
import logging
import hashlib
import secrets

logger = logging.getLogger(__name__)


class ToolExecutionService:
    """Production-ready tool execution service with real implementations"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "veklom_tools"
        self.temp_dir.mkdir(exist_ok=True)
        self.sandbox_dir = self.temp_dir / "sandbox"
        self.sandbox_dir.mkdir(exist_ok=True)
        
        # Security: Define allowed operations
        self.allowed_file_operations = {
            "read", "write", "list", "exists", "size", "copy", "move", "delete"
        }
        self.allowed_sql_operations = {
            "SELECT", "INSERT", "UPDATE", "DELETE"
        }
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.allowed_domains = [
            "api.openai.com", "api.anthropic.com", "api.google.com",
            "github.com", "api.github.com", "jsonplaceholder.typicode.com"
        ]
    
    async def execute_filesystem_tool(self, tool_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute real filesystem operations with security checks"""
        try:
            operation = tool_data.get("operation", "read")
            path = tool_data.get("path", "")
            content = tool_data.get("content", "")
            
            # Security: Validate path
            if not self._is_safe_path(path):
                return {
                    "success": False,
                    "error": "Path traversal detected or unsafe path",
                    "operation": operation
                }
            
            full_path = self.sandbox_dir / path.lstrip("/")
            
            if operation == "read":
                return await self._read_file(full_path)
            elif operation == "write":
                return await self._write_file(full_path, content)
            elif operation == "list":
                return await self._list_directory(full_path)
            elif operation == "exists":
                return await self._file_exists(full_path)
            elif operation == "size":
                return await self._get_file_size(full_path)
            elif operation == "copy":
                dest = tool_data.get("destination", "")
                if not self._is_safe_path(dest):
                    return {"success": False, "error": "Unsafe destination path"}
                return await self._copy_file(full_path, self.sandbox_dir / dest.lstrip("/"))
            elif operation == "move":
                dest = tool_data.get("destination", "")
                if not self._is_safe_path(dest):
                    return {"success": False, "error": "Unsafe destination path"}
                return await self._move_file(full_path, self.sandbox_dir / dest.lstrip("/"))
            elif operation == "delete":
                return await self._delete_file(full_path)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported operation: {operation}",
                    "operation": operation
                }
                
        except Exception as e:
            logger.error(f"Filesystem tool execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "operation": tool_data.get("operation", "unknown")
            }
    
    async def execute_database_tool(self, tool_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute real database operations with security checks"""
        try:
            query = tool_data.get("query", "")
            db_type = tool_data.get("db_type", "sqlite")
            
            # Security: Validate SQL
            if not self._is_safe_sql(query):
                return {
                    "success": False,
                    "error": "SQL injection detected or unsafe operation",
                    "query": query[:100] + "..." if len(query) > 100 else query
                }
            
            if db_type == "sqlite":
                return await self._execute_sqlite(query, tool_data)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported database type: {db_type}"
                }
                
        except Exception as e:
            logger.error(f"Database tool execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query": tool_data.get("query", "unknown")[:100]
            }
    
    async def execute_api_tool(self, tool_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute real HTTP API calls with security checks"""
        try:
            url = tool_data.get("url", "")
            method = tool_data.get("method", "GET").upper()
            headers = tool_data.get("headers", {})
            payload = tool_data.get("payload", {})
            timeout = tool_data.get("timeout", 30)
            
            # Security: Validate URL
            if not self._is_safe_url(url):
                return {
                    "success": False,
                    "error": "Unsafe URL or blocked domain",
                    "url": url
                }
            
            # Execute HTTP request
            async with httpx.AsyncClient(timeout=timeout) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(url, json=payload, headers=headers)
                elif method == "PUT":
                    response = await client.put(url, json=payload, headers=headers)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    return {
                        "success": False,
                        "error": f"Unsupported HTTP method: {method}",
                        "url": url
                    }
                
                # Parse response
                try:
                    response_data = response.json()
                except:
                    response_data = response.text
                
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response": response_data,
                    "headers": dict(response.headers),
                    "url": url,
                    "method": method
                }
                
        except Exception as e:
            logger.error(f"API tool execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "url": tool_data.get("url", "unknown")
            }
    
    async def execute_browser_tool(self, tool_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute browser automation via Agent Browser Protocol (ABP)"""
        try:
            url = tool_data.get("url", "")
            action = tool_data.get("action", "navigate")
            
            # Security: Validate URL
            if not self._is_safe_url(url):
                return {
                    "success": False,
                    "error": "Unsafe URL for browser automation",
                    "url": url
                }
            
            import json
            import asyncio
            
            # Use ABP via MCP
            logger.info(f"Routing browser action '{action}' through Agent Browser Protocol (ABP) MCP...")
            
            # Spawn MCP subprocess
            process = await asyncio.create_subprocess_shell(
                "npx -y agent-browser-protocol --mcp",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Formulate MCP JSON-RPC payload for the browser action
            mcp_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "call_tool",
                "params": {
                    "name": "browser_action",
                    "arguments": {
                        "action": action,
                        "url": url,
                        "data": tool_data.get("data", {})
                    }
                }
            }
            
            # Send payload to ABP MCP
            payload_str = json.dumps(mcp_payload) + "
"
            process.stdin.write(payload_str.encode())
            await process.stdin.drain()
            
            # Read response
            output = await process.stdout.readline()
            
            # Clean up
            process.terminate()
            
            # Process response
            if output:
                response_data = json.loads(output.decode().strip())
                if "result" in response_data:
                    return {
                        "success": True,
                        "action": action,
                        "url": url,
                        "state": "frozen_virtual_time",
                        "abp_response": response_data["result"]
                    }
                elif "error" in response_data:
                    return {
                        "success": False,
                        "action": action,
                        "error": response_data["error"]
                    }
            
            return {
                "success": True,
                "action": action,
                "url": url,
                "state": "frozen_virtual_time",
                "abp_status": "dispatched"
            }
                
        except Exception as e:
            logger.error(f"ABP Browser execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "action": tool_data.get("action", "unknown")
            }
    async def execute_custom_tool(self, tool_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute custom tool logic"""
        try:
            tool_name = tool_data.get("tool_name", "unknown")
            parameters = tool_data.get("parameters", {})
            
            # Example custom tools
            if tool_name == "calculate_hash":
                return await self._calculate_hash(parameters)
            elif tool_name == "generate_uuid":
                return await self._generate_uuid()
            elif tool_name == "format_json":
                return await self._format_json(parameters)
            elif tool_name == "parse_csv":
                return await self._parse_csv(parameters)
            else:
                return {
                    "success": False,
                    "error": f"Unknown custom tool: {tool_name}",
                    "tool_name": tool_name
                }
                
        except Exception as e:
            logger.error(f"Custom tool execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_data.get("tool_name", "unknown")
            }
    
    # Security validation methods
    def _is_safe_path(self, path: str) -> bool:
        """Check if path is safe (no traversal, within sandbox)"""
        if not path:
            return True
        
        # Check for path traversal
        if ".." in path or path.startswith("/"):
            return False
        
        # Check for suspicious patterns
        suspicious_patterns = ["\\x00", "\\n", "\\r", "<script", "javascript:"]
        path_lower = path.lower()
        for pattern in suspicious_patterns:
            if pattern in path_lower:
                return False
        
        return True
    
    def _is_safe_sql(self, query: str) -> bool:
        """Check if SQL query is safe"""
        if not query:
            return True
        
        query_upper = query.upper().strip()
        
        # Check for dangerous keywords
        dangerous_keywords = [
            "DROP", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE",
            "ATTACH", "DETACH", "PRAGMA", "VACUUM"
        ]
        
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                return False
        
        # Only allow specific operations
        allowed_operations = ["SELECT", "INSERT", "UPDATE", "DELETE"]
        if not any(query_upper.startswith(op) for op in allowed_operations):
            return False
        
        return True
    
    def _is_safe_url(self, url: str) -> bool:
        """Check if URL is safe"""
        if not url:
            return True
        
        # Check protocol
        if not url.startswith(("http://", "https://")):
            return False
        
        # Extract domain
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Check against allowed domains
            if not any(allowed in domain for allowed in self.allowed_domains):
                # Allow localhost for development
                if not domain.startswith(("localhost", "127.0.0.1")):
                    return False
            
            return True
            
        except Exception:
            return False
    
    # Filesystem implementation methods
    async def _read_file(self, path: Path) -> Dict[str, Any]:
        """Read file content"""
        try:
            if not path.exists():
                return {"success": False, "error": "File not found"}
            
            if path.stat().st_size > self.max_file_size:
                return {"success": False, "error": "File too large"}
            
            content = path.read_text(encoding='utf-8')
            return {
                "success": True,
                "content": content,
                "size": len(content),
                "path": str(path.relative_to(self.sandbox_dir))
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _write_file(self, path: Path, content: str) -> Dict[str, Any]:
        """Write file content"""
        try:
            if len(content) > self.max_file_size:
                return {"success": False, "error": "Content too large"}
            
            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)
            
            path.write_text(content, encoding='utf-8')
            return {
                "success": True,
                "size": len(content),
                "path": str(path.relative_to(self.sandbox_dir))
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _list_directory(self, path: Path) -> Dict[str, Any]:
        """List directory contents"""
        try:
            if not path.exists():
                return {"success": False, "error": "Directory not found"}
            
            if not path.is_dir():
                return {"success": False, "error": "Not a directory"}
            
            items = []
            for item in path.iterdir():
                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else 0,
                    "modified": item.stat().st_mtime
                })
            
            return {
                "success": True,
                "items": items,
                "path": str(path.relative_to(self.sandbox_dir))
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _file_exists(self, path: Path) -> Dict[str, Any]:
        """Check if file exists"""
        return {
            "success": True,
            "exists": path.exists(),
            "path": str(path.relative_to(self.sandbox_dir))
        }
    
    async def _get_file_size(self, path: Path) -> Dict[str, Any]:
        """Get file size"""
        try:
            if not path.exists():
                return {"success": False, "error": "File not found"}
            
            size = path.stat().st_size
            return {
                "success": True,
                "size": size,
                "path": str(path.relative_to(self.sandbox_dir))
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _copy_file(self, src: Path, dst: Path) -> Dict[str, Any]:
        """Copy file"""
        try:
            if not src.exists():
                return {"success": False, "error": "Source file not found"}
            
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            
            return {
                "success": True,
                "source": str(src.relative_to(self.sandbox_dir)),
                "destination": str(dst.relative_to(self.sandbox_dir))
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _move_file(self, src: Path, dst: Path) -> Dict[str, Any]:
        """Move file"""
        try:
            if not src.exists():
                return {"success": False, "error": "Source file not found"}
            
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            
            return {
                "success": True,
                "source": str(src.relative_to(self.sandbox_dir)),
                "destination": str(dst.relative_to(self.sandbox_dir))
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _delete_file(self, path: Path) -> Dict[str, Any]:
        """Delete file or directory"""
        try:
            if not path.exists():
                return {"success": False, "error": "File not found"}
            
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            
            return {
                "success": True,
                "path": str(path.relative_to(self.sandbox_dir))
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Database implementation methods
    async def _execute_sqlite(self, query: str, tool_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SQLite query"""
        try:
            # Use a temporary database for safety
            db_path = self.sandbox_dir / "temp.db"
            
            with sqlite3.connect(str(db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(query)
                
                if query.strip().upper().startswith("SELECT"):
                    rows = cursor.fetchall()
                    results = [dict(row) for row in rows]
                    return {
                        "success": True,
                        "results": results,
                        "count": len(results),
                        "query": query
                    }
                else:
                    conn.commit()
                    return {
                        "success": True,
                        "affected_rows": cursor.rowcount,
                        "query": query
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query[:100] + "..." if len(query) > 100 else query
            }
    
    # Custom tool implementations
    async def _calculate_hash(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate hash of content"""
        try:
            content = parameters.get("content", "")
            algorithm = parameters.get("algorithm", "sha256")
            
            if algorithm == "sha256":
                hash_obj = hashlib.sha256(content.encode())
            elif algorithm == "md5":
                hash_obj = hashlib.md5(content.encode())
            else:
                return {"success": False, "error": f"Unsupported algorithm: {algorithm}"}
            
            return {
                "success": True,
                "hash": hash_obj.hexdigest(),
                "algorithm": algorithm,
                "content_length": len(content)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_uuid(self) -> Dict[str, Any]:
        """Generate UUID"""
        try:
            import uuid
            return {
                "success": True,
                "uuid": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _format_json(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Format JSON"""
        try:
            data = parameters.get("data", {})
            indent = parameters.get("indent", 2)
            
            formatted = json.dumps(data, indent=indent, ensure_ascii=False)
            return {
                "success": True,
                "formatted": formatted,
                "original_length": len(str(data)),
                "formatted_length": len(formatted)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _parse_csv(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Parse CSV data"""
        try:
            csv_data = parameters.get("csv_data", "")
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                f.write(csv_data)
                temp_path = f.name
            
            try:
                df = pd.read_csv(temp_path)
                return {
                    "success": True,
                    "rows": len(df),
                    "columns": list(df.columns),
                    "data": df.to_dict('records')[:10],  # First 10 rows
                    "preview": True
                }
            finally:
                os.unlink(temp_path)
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def cleanup(self):
        """Clean up temporary files"""
        try:
            if self.sandbox_dir.exists():
                shutil.rmtree(self.sandbox_dir)
                self.sandbox_dir.mkdir(exist_ok=True)
            logger.info("Tool execution service cleaned up")
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")


# Global instance
tool_execution_service = ToolExecutionService()


def get_tool_execution_service() -> ToolExecutionService:
    """Get the global tool execution service instance"""
    return tool_execution_service
