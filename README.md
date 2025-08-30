🤖 온프레미스(On-Premise) 환경을 위한 범용 Text-to-SQL 에이전트
본 저장소는 온프레미스(On-Premise) 환경에서 **MCP(Model Context Protocol)**를 활용하여, 데이터베이스 종류에 구애받지 않는 범용 Text-to-SQL 에이전트의 설계 및 구현에 관한 연구 결과물입니다.
SQL 비전문가도 자연어 질의를 통해 손쉽게 데이터에 접근할 수 있도록 지원하며, 기존 솔루션의 높은 비용, 데이터 보안, 확장성 문제를 해결하는 것을 목표로 합니다.

✨ 주요 특징 (Key Features)
💻 온프레미스 실행: 모든 시스템이 내부 서버에서 독립적으로 구동되어 외부 API 의존 없이 민감한 데이터를 안전하게 보호하고 비용을 절감합니다.

🌐 범용 데이터베이스 지원: MCP를 통해 표준화된 도구를 사용하여 Oracle, MS SQL, MySQL, PostgreSQL 등 다양한 데이터베이스와 유연하게 연동합니다.

🧠 ReAct 기반 자율 에이전트: LangGraph의 ReAct(Reasoning and Acting) 프레임워크를 기반으로, 에이전트가 스스로 '생각 → 행동 → 관찰'의 과정을 반복하며 복잡한 자연어 질의를 해결합니다.

🧩 표준화된 확장 구조: MCP(Model Context Protocol)를 통해 데이터베이스 제어 도구를 표준화하여, 새로운 데이터 소스나 기능을 손쉽게 추가할 수 있습니다.

💡 핵심 개념 (Core Concepts)
1. LLM-based 에이전트 (LLM-based Agent)
본 시스템의 핵심 에이전트는 ReAct 프레임워크를 기반으로 동작합니다. 사용자의 자연어 질의를 해결하기 위해 스스로 추론(Thought)하고, 필요한 도구를 호출(Action)하며, 그 결과를 관찰(Observation)하는 단계를 반복하여 최종 답변을 도출합니다.

[그림 1] LLM(Large Language Model)-based 에이전트의 구조

2. MCP (Model Context Protocol)
MCP는 LLM 에이전트가 외부 도구 및 데이터와 상호작용하는 방식을 표준화하는 개방형 프로토콜입니다. Host-Client-Server 구조를 통해 각 구성 요소를 독립적으로 개발하고 확장할 수 있어, 특정 데이터베이스나 서비스에 종속되지 않는 유연한 시스템 구축을 가능하게 합니다.

[그림 2] MCP(Model Context Protocol) 구조도

🏗️ 시스템 아키텍처 (System Architecture)
본 시스템은 2개의 독립된 컨테이너 환경에서 MCP Host-Client-Server 구조로 동작합니다.

[그림 3] 제안한 시스템의 전체 구조도

MCP Host (UI): 사용자는 Streamlit으로 구현된 웹 인터페이스를 통해 자연어 질의를 입력합니다.

MCP Client (Agent): gpt-oss:20b 모델과 LangGraph로 구현된 에이전트가 사용자 질의를 해석하고, MCP Server에 필요한 도구 호출을 요청합니다.

MCP Server (Tools): 데이터베이스 조회를 위한 9개의 표준화된 도구(list_tables, show_data 등)를 API 형태로 제공합니다.

Databases: Docker 컨테이너 환경에서 Oracle, MS SQL, MySQL, PostgreSQL 데이터베이스가 독립적으로 실행됩니다.

🛠️ 기술 스택 (Tech Stack)
구분

항목

내용

H/W

GPU

NVIDIA V100 32GB



OS

Debian 12.0 Bookworm

S/W

Language

Python 3.12



LLM

gpt-oss:20b



MCP Host

Streamlit 1.44



MCP Client

LangGraph 0.3.21, LangChain-Ollama 0.3.6



MCP Server

langchain-mcp-adapters 0.0.7



Database

Oracle XE (21c), MS SQL Server (2022), MySQL (8.0), PostgreSQL (15)



Container

Docker 28.3.2

📊 실험 결과 (Results)
4개의 서로 다른 데이터베이스 환경에서 자연어 질의를 통해 성공적으로 원하는 결과를 얻는 것을 확인했습니다.

Oracle - 테이블 목록 조회

Microsoft SQL Server - 데이터 조회





MySQL - 데이터 추가

PostgreSQL - 데이터 검색





🚀 향후 연구 방향 (Future Work)
멀티 에이전트 시스템으로 확장: 복잡하고 동적인 작업을 병렬적으로 처리하기 위해 A2A(Agent-to-Agent) 아키텍처 기반의 멀티 에이전트 시스템을 구현할 계획입니다.

도메인 특화 성능 강화: 금융, 의료 등 특정 도메인에 특화된 데이터베이스 스키마와 질의 패턴을 학습하여 에이전트의 성능을 고도화할 예정입니다.

모니터링 대시보드 구축: 에이전트의 작동 흐름과 도구 호출 과정을 시각적으로 모니터링할 수 있는 대시보드를 개발하여 사용성과 관리 효율을 높이고자 합니다.

🧑‍🔬 연구진 (Authors)
김지섭 (동서울대학교 컴퓨터소프트웨어과)

김동우 (동서울대학교 컴퓨터소프트웨어과)

이재희 교수님 (동서울대학교 컴퓨터소프트웨어과)
