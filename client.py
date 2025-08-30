import json
from langchain_ollama import ChatOllama
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

async def create_agent():
    config_file_path = "mcp_config.json"
    with open(config_file_path, 'r', encoding='utf-8') as f:
        mcp_config = json.load(f)

    client = MultiServerMCPClient(mcp_config)
    tools = await client.get_tools()
    
    # gpt-oss:20b로 테스트 (1개 tool이므로 문제없을 것)
    model_name_to_use = "gpt-oss:20b"
    
    model = ChatOllama(
        model=model_name_to_use,
        temperature=0,
    )
    
    # 에이전트 생성
    agent = create_react_agent(
        model, 
        tools,
        messages_modifier=lambda messages: messages
    )

    return agent, client, model_name_to_use, tools