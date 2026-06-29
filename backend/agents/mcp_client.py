"""
Model Context Protocol (MCP) Client Manager
Handles stdio JSON-RPC connections to external MCP servers
and translates their tools into LangChain structured tools.
"""

import asyncio
import json
import os
from typing import Dict, Any, List, Optional
from langchain_core.tools import StructuredTool
from database.db import SessionLocal
from database.models import McpServerModel


class McpClient:
    """
    Manages stdio connection to a single MCP server
    """
    def __init__(self, server_id: str, command: str, args: List[str], env: Dict[str, str] = None):
        self.server_id = server_id
        self.command = command
        self.args = args
        self.env = env or {}
        self.process = None
        self.message_id = 0
        self.pending_responses: Dict[int, asyncio.Future] = {}
        self.reader_task = None
        
    async def start(self):
        """Start the stdio process and the background reader"""
        # Ensure command path resolves or is available
        full_env = {**os.environ, **self.env}
        
        # Start subprocess
        self.process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=full_env
        )
        
        # Start background reader task
        self.reader_task = asyncio.create_task(self._read_loop())
        
    async def _read_loop(self):
        try:
            while self.process and not self.process.stdout.at_eof():
                line = await self.process.stdout.readline()
                if not line:
                    break
                line_str = line.decode('utf-8').strip()
                if not line_str:
                    continue
                try:
                    message = json.loads(line_str)
                    if "id" in message:
                        msg_id = message["id"]
                        if msg_id in self.pending_responses:
                            fut = self.pending_responses[msg_id]
                            if not fut.done():
                                fut.set_result(message)
                except Exception as e:
                    print(f"Error parsing MCP JSON line from {self.server_id}: {e}, content: {line_str}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Error in MCP read loop for {self.server_id}: {e}")
            
    async def call_method(self, method: str, params: Dict[str, Any] = None, timeout: float = 15.0) -> Dict[str, Any]:
        """Send a JSON-RPC request and wait for the response"""
        if not self.process:
            await self.start()
            
        self.message_id += 1
        msg_id = self.message_id
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": msg_id,
            "params": params or {}
        }
        
        # Register future for response
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self.pending_responses[msg_id] = fut
        
        # Write to process stdin
        request_str = json.dumps(request) + "\n"
        self.process.stdin.write(request_str.encode('utf-8'))
        await self.process.stdin.drain()
        
        # Wait for response
        try:
            response = await asyncio.wait_for(fut, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            raise TimeoutError(f"MCP server {self.server_id} method '{method}' call timed out.")
        finally:
            self.pending_responses.pop(msg_id, None)
            
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List tools provided by the MCP server"""
        response = await self.call_method("tools/list")
        if "error" in response:
            raise ValueError(f"Error listing MCP tools: {response['error']}")
        return response.get("result", {}).get("tools", [])
        
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool on the MCP server"""
        response = await self.call_method("tools/call", {"name": name, "arguments": arguments})
        if "error" in response:
            return {"isError": True, "content": [{"type": "text", "text": f"Error: {response['error']}"}]}
        return response.get("result", {})
        
    async def stop(self):
        """Terminate the process and clean up resources"""
        if self.reader_task:
            self.reader_task.cancel()
            self.reader_task = None
            
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except Exception:
                pass
            self.process = None


def make_mcp_tool(client: McpClient, original_name: str, tool_name: str, description: str) -> StructuredTool:
    """Wrapper that creates a LangChain StructuredTool from an MCP tool definition"""
    async def _acall(**kwargs):
        res = await client.call_tool(original_name, kwargs)
        contents = res.get("content", [])
        text_out = []
        for chunk in contents:
            if chunk.get("type") == "text":
                text_out.append(chunk.get("text", ""))
        return "\n".join(text_out) if text_out else str(res)
        
    def _call(**kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor() as executor:
                return executor.submit(lambda: asyncio.run(_acall(**kwargs))).result()
        else:
            return loop.run_until_complete(_acall(**kwargs))

    return StructuredTool.from_function(
        func=_call,
        coroutine=_acall,
        name=tool_name,
        description=description
    )


class McpManager:
    """
    Coordinates active MCP clients and fetches tools
    """
    def __init__(self):
        self.clients: Dict[str, McpClient] = {}
        
    async def get_client(self, server_id: str, db_session) -> Optional[McpClient]:
        if server_id in self.clients:
            return self.clients[server_id]
            
        # Fetch from DB
        db_server = db_session.query(McpServerModel).filter(
            McpServerModel.id == server_id,
            McpServerModel.enabled == True
        ).first()
        
        if not db_server:
            return None
            
        client = McpClient(
            server_id=db_server.id,
            command=db_server.command,
            args=db_server.args or [],
            env=db_server.env or {}
        )
        try:
            await client.start()
            self.clients[server_id] = client
            return client
        except Exception as e:
            print(f"Failed to start MCP server {server_id}: {e}")
            return None
            
    async def get_tools_for_agent(self, agent_mcp_ids: List[str]) -> List[StructuredTool]:
        """Load tools from all enabled MCP servers associated with this agent"""
        if not agent_mcp_ids:
            return []
            
        session = SessionLocal()
        tools = []
        try:
            for server_id in agent_mcp_ids:
                client = await self.get_client(server_id, session)
                if client:
                    try:
                        mcp_tools = await client.list_tools()
                        for t in mcp_tools:
                            tool_name = f"mcp_{server_id}_{t['name']}"
                            # Standardize tool name to match alphanumeric/underscore requirement
                            clean_tool_name = "".join(c if c.isalnum() or c == "_" else "_" for c in tool_name)
                            desc = t.get("description", "") + f"\nParameters schema: {json.dumps(t.get('inputSchema', {}))}"
                            tools.append(make_mcp_tool(client, t['name'], clean_tool_name, desc))
                    except Exception as e:
                        print(f"Error loading tools from MCP server {server_id}: {e}")
        finally:
            session.close()
        return tools
        
    def get_tools_for_agent_sync(self, agent_mcp_ids: List[str]) -> List[StructuredTool]:
        """Synchronous wrapper to get tools from enabled MCP servers"""
        if not agent_mcp_ids:
            return []
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor() as executor:
                return executor.submit(lambda: asyncio.run(self.get_tools_for_agent(agent_mcp_ids))).result()
        else:
            return loop.run_until_complete(self.get_tools_for_agent(agent_mcp_ids))

    async def shutdown(self):
        for client in self.clients.values():
            await client.stop()
        self.clients.clear()


# Global MCP manager instance
mcp_manager = McpManager()
