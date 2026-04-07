from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel
import json, logging
from typing import Any, Dict
from fastapi import FastAPI
from contextlib import asynccontextmanager
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel
import json, logging
import uvicorn

logger = logging.getLogger(__name__)

mcp_session: ClientSession = None
# available_tools: list = []

@asynccontextmanager
async def server(app: FastAPI):
    global mcp_session, available_tools
    print('async agent')
    server_params = StdioServerParameters(
        command="npx", args=["-y", "@azure/mcp@latest", "server", "start"]
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            mcp_session = session
            available_tools = [
                {
                    "toolSpec": {
                        "name": t.name,
                        "description": t.description,
                        "inputSchema": {"json": t.inputSchema},
                    }
                }
                for t in tools.tools
            ]
            for t in tools.tools:
                print(f"Tools name: {t.name}. Tool {t.name} description: {t.description}")
            yield


app = FastAPI(title="Bedrock MCP Agent API", lifespan=server)


class PromptRequest(BaseModel):
    tool: str
    function_args: Dict[str, Any]


@app.post("/mcp")
async def agent(request: Request, body: PromptRequest):

    print('R E Q U E S T:')
    print(body)
    
    raw = await mcp_session.call_tool(body.tool, body.function_args)

    try:
        result_dict = raw.model_dump()
        for item in result_dict.get("content", []):
            if item.get("type") == "text":
                text_value = item.get("text")
                if isinstance(text_value, str):
                    item["text"] = json.loads(text_value)
    except Exception:
        pass

    print('R E S U L T')
    print(result_dict)
    return {
        "logs": result_dict
    }


if __name__=="__main__":
    uvicorn.run(
        "async_agent:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )