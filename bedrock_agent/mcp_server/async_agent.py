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
import subprocess

logger = logging.getLogger(__name__)

mcp_session: ClientSession = None


CUSTOM_TOOLS = {
    "disable_user": {
        "toolSpec": {
            "name": "disable_user",
            "description": "disables the user account.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "account_name": {
                            "type": "string",
                            "description": "Account name with domain."
                        },
                    },
                    "required": ["account_name"]
                }
            }
        }
    }
}


@asynccontextmanager
async def server(app: FastAPI):
    global mcp_session, available_tools
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
            yield


app = FastAPI(title="Bedrock MCP Agent API", lifespan=server)


class PromptRequest(BaseModel):
    tool: str
    function_args: Dict[str, Any]



async def custom_call_tool(tool_name: str, function_args: Dict[str, Any]):
    print('disabling tool was activated')
    if tool_name == "disable_user":

        # command = [
        #     "az", "ad", "user", "update",
        #     "--id", function_args["account_name"],
        #     "--account-enabled", "false"
        # ]

        # print(f"Executing: {' '.join(command)}")

        # result = subprocess.run(
        #     command,
        #     capture_output=True,
        #     text=True
        # )

        # success = result.returncode == 0
        # output = result.stdout if success else result.stderr
        print('user was blocked')
        return {
            "logs": {
                "content": [{"type": "text", "text": "blockedPlaceholder"}],
                "success": "yes"
            }
        }

    raise ValueError(f"Unknown custom tool: {tool_name}")


@app.post("/mcp")
async def agent(request: Request, body: PromptRequest):

    print('R E Q U E S T:')
    print(body)
    if body.tool == "disable_user":
        return await custom_call_tool(body.tool, body.function_args)
    
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
        "test_agent:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
