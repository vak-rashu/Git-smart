import asyncio
from openclaw_sdk import OpenClawClient, Agent
from dotenv import load_dotenv

import asyncio
import json
import websockets

async def connect_to_openclaw():
    # Replace with your actual OpenClaw gateway URI
    uri = "ws://127.0.0.1:18789" 
    
    async with websockets.connect(uri) as websocket:
        # 1. Define the mandatory connection frame
        connect_payload = {
            "type": "req",
            "method": "connect",
            "params": {
                # Add required authentication token or client info here
                "token": "0e4f1f6189f50768525d2666e07e93fb39a3d945282fde58" 
            }
        }
        
        # 2. Serialize to a JSON string and send immediately
        await websocket.send(json.dumps(connect_payload))
        print("Connect request sent.")
        
        # 3. Listen for the gateway response
        response = await websocket.recv()
        print(f"Gateway response: {response}")

# Run the connection loop

load_dotenv()
import os
os.environ["GEMINI_API_KEY"] = "AQ.Ab8RN6IRbDJmKy8OO4MYL798HSN96Y7QDPRUGPTEy3UxMq-_UA"

async def test():
    client = await OpenClawClient.connect()
    agent = Agent(client=client, agent_id="arch-reviewer")
    result = await agent.execute("test")
    print(result)

if __name__ == "__main__":
    asyncio.run(connect_to_openclaw())
    asyncio.run(test())
