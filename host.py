import streamlit as st
import asyncio
import nest_asyncio
import traceback
import json
from langchain_core.messages import HumanMessage
from client import create_agent

# ----------------------------------------------------
# 1. 비동기(async) 및 에이전트 실행 관련 설정
# ----------------------------------------------------

nest_asyncio.apply()
if "event_loop" not in st.session_state:
    st.session_state.event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(st.session_state.event_loop)

async def get_agent_response(inputs, text_placeholder, tool_placeholder):
    final_text = ""
    tool_request_info = ""
    tool_response_info = ""
    tool_call_id = None

    async for chunk in st.session_state.agent.astream(inputs, stream_mode="updates"):
        if "agent" in chunk:
            messages = chunk["agent"].get("messages", [])
            if messages:
                if hasattr(messages[-1], 'tool_calls') and messages[-1].tool_calls:
                    tool_call_id = messages[-1].tool_calls[0]['id']
                    tool_calls_pretty = json.dumps(messages[-1].tool_calls, indent=2, ensure_ascii=False)
                    tool_request_info = f"```json\n# Tool Call Request (호출 요청)\n{tool_calls_pretty}\n```"
                    with tool_placeholder.expander("🔧 도구 호출 정보", expanded=True):
                        st.markdown(tool_request_info)
                if messages[-1].content:
                    final_text = messages[-1].content
                    text_placeholder.markdown(final_text + " ▌")
        
        if "tools" in chunk:
            messages = chunk["tools"].get("messages", [])
            if messages:
                tool_response_content = messages[-1].content
                tool_response_info = f"```markdown\n# Tool Call Response (호출 응답)\n{tool_response_content}\n```"
                with tool_placeholder.expander("🔧 도구 호출 정보", expanded=True):
                    st.markdown(tool_request_info)
                    st.markdown(tool_response_info)
        
        await asyncio.sleep(0.01)
    
    text_placeholder.markdown(final_text)
    full_tool_info = (tool_request_info + "\n\n" + tool_response_info).strip()
    return final_text, full_tool_info, tool_call_id

# ----------------------------------------------------
# 2. Streamlit UI 구성
# ----------------------------------------------------

st.set_page_config(page_title="MCP Host", layout="wide")

# --- 👨‍💻 여기를 수정해주세요 ---

# st.columns를 사용해 레이아웃을 두 개의 열로 나눕니다.
# [1.5, 10]은 로고와 제목 영역의 가로 비율입니다.
# vertical_alignment="center"는 로고와 제목의 세로 위치를 중앙으로 맞춥니다.
col1, col2 = st.columns([1.5, 10], vertical_alignment="center")

try:
    # 첫 번째 열(col1)에 로고를 넣습니다.
    with col1:
        st.image("logo.jpg", width=150) # 로고 크기는 여기서 조절하세요.

    # 두 번째 열(col2)에 제목을 넣습니다.
    with col2:
        st.title("MCP(Model Context Protocol)기반 Local LLM을 활용한 범용 데이터베이스 Agent 설계 및 구현")
    

except FileNotFoundError:
    # 혹시 로고 파일이 없으면 제목만 전체 너비로 표시합니다.ß
    st.title("MCP(Model Context Protocol)기반 Local LLM을 활용한 범용 데이터베이스 Agent 설계 및 구현")
    st.warning("logo.jpg 파일을 찾을 수 없습니다. 스크립트와 같은 폴더에 있는지 확인해주세요.")

# 구분선을 추가해 제목 영역을 분리합니다.
st.markdown("---")

# --- 여기까지 수정 ---


with st.sidebar:
    st.title("MCP 제어판")
    st.markdown("---")

    # '에이전트 생성하기' 버튼을 컨테이너 너비에 맞게 확장합니다.
    if st.button("에이전트 생성하기", type="primary", use_container_width=True):
        with st.spinner("에이전트를 생성하고 있습니다..."):
            try:
                loop = st.session_state.event_loop
                agent, mcp_client, model_name, tool_list = loop.run_until_complete(create_agent())
                
                st.session_state.agent = agent
                st.session_state.mcp_client = mcp_client
                st.session_state.model_name = model_name
                st.session_state.tool_list = tool_list
                st.session_state.mcp_status = "Connected"
                st.session_state.session_initialized = True
                st.success("에이전트가 성공적으로 생성되었습니다.")
            except Exception as e:
                st.session_state.mcp_status = "❌ Failed"
                st.error("에이전트 생성 실패! 자세한 오류는 아래와 같습니다.")
                st.code(traceback.format_exc())

    st.markdown("---")
    
    # st.container(border=True)를 사용해 관련 정보를 시각적으로 묶어줍니다.
    with st.container(border=True):
        st.subheader("System Information")
        
        # ▼▼▼ 여기가 요청하신 대로 수정한 부분입니다 ▼▼▼
        st.markdown(f"""
            <p style='margin-bottom: 0.5rem;'>
                <b>Model</b>: <span style='font-size: 1.1em; font-weight: bold;'>{st.session_state.get('model_name', 'N/A')}</span>
            </p>
        """, unsafe_allow_html=True)
        # ▲▲▲ 여기까지 입니다 ▲▲▲
        
        st.markdown(f"<p style='margin-top: 0.5rem;'><b>MCP Status</b>: {st.session_state.get('mcp_status', 'Not Connected')}</p>", unsafe_allow_html=True)

    st.markdown("---")
    
    # '대화 초기화' 버튼도 너비를 맞추어 통일성을 줍니다.
    if st.button("Reset Conversation", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": "대화가 초기화 되었습니다."}]
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "'에이전트 생성하기' 버튼을 눌러주세요."}]
if "session_initialized" not in st.session_state:
    st.session_state.session_initialized = False

i = 0
while i < len(st.session_state.messages):
    msg = st.session_state.messages[i]
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
        i += 1
    elif msg["role"] == "assistant":
        with st.chat_message("assistant"):
            st.write(msg["content"])
            if (i + 1 < len(st.session_state.messages) and 
                st.session_state.messages[i + 1]["role"] == "tool"):
                with st.expander("🔧 도구 호출 과정 보기"):
                    st.markdown(st.session_state.messages[i + 1]["content"])
                i += 2
            else:
                i += 1
    else:
        i += 1

if prompt := st.chat_input("여기에 메시지를 입력하세요..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    if not st.session_state.session_initialized:
        st.warning("먼저 사이드바의 '에이전트 생성하기' 버튼을 눌러주세요.")
        st.stop()

    with st.chat_message("assistant"):
        tool_placeholder = st.empty()
        text_placeholder = st.empty()
        
        try:
            inputs = {"messages": st.session_state.messages}

            loop = st.session_state.event_loop
            response_content, tool_info, tool_call_id = loop.run_until_complete(
                get_agent_response(inputs, text_placeholder, tool_placeholder)
            )
            
        except Exception as e:
            response_content = f"오류가 발생했습니다: {traceback.format_exc()}"
            text_placeholder.error(response_content)
            tool_info = ""
            tool_call_id = None

    st.session_state.messages.append({"role": "assistant", "content": response_content})
    if tool_info:
        st.session_state.messages.append({
            "role": "tool", 
            "content": tool_info,
            "tool_call_id": tool_call_id
        })
    
    st.rerun()