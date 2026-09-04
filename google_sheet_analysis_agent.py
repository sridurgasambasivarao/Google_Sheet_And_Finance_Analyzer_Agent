"""Google Sheets and finance analyzer agent"""

import sys
import os

root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_dir)

from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langchain.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from scripts import prompts, utils

from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

model = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite")

checkpointer = InMemorySaver()

async def get_tools():    
    tools = []

    mcp_config = utils.load_mcp_config("google-sheets", "yahoo-finance")
    client = MultiServerMCPClient(mcp_config) 

    # Fetch google sheet tools safely
    try:
        sheet_tools = await client.get_tools(server_name="google-sheets")
        tools.extend(sheet_tools)
    except Exception as e:
        print(f"google sheet server down: {e}")       

    # Fetch yahoo finance tools safely
    try:
        yahoo_tools = await client.get_tools(server_name="yahoo-finance")
        tools.extend(yahoo_tools)
    except Exception as e:
        print(f"Yahoo finance server down: {e}")

    if tools:
        # Some of the google sheet tools does not work with Gemini
        problematic_tools = ['update_cells']
                        
        safe_tools = [tool for tool in tools if tool.name not in problematic_tools]
                
        print(f"Loaded {len(safe_tools)} Tools")
        print(f"Tools Available\n{[tool.name for tool in safe_tools]}")
                
        return safe_tools
    else:
        return tools
        
    
async def google_sheet_agent(query, thread_id="default"):
    tools = await get_tools()

    agent = create_agent(model=model,
                         tools=tools, 
                         system_prompt=prompts.GOOGLE_SHEETS_PROMPT,
                         checkpointer=checkpointer)

    config = {"configurable": {"thread_id": thread_id}}
    result = await agent.ainvoke({'messages': [HumanMessage(query)]}, config=config)

    response = result['messages'][-1].text

    print("\n============== Output =============")
    print(response)



async def ask():
    print("\nChat mode started. Type 'q' or 'quite' to exit.\n")
    while True:
        print("\n\n\nAsk Question. Type 'q' or 'quite' to exit.")
        query = input("You: ").strip()

        if query.lower() in ["q", "quite"]:
            print("Exiting chat mode.")
            break

        await google_sheet_agent(query)

if __name__ == "__main__":
    # query = "list all my spreadsheets"
    asyncio.run(ask())
