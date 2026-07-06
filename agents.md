# AGENTS.md

## 项目目标

在开源 CRM 项目 Twenty 的基础上，新增 AI Sales Assistant 模块，用于增强销售人员在客户管理、商机跟进、企业知识库问答和合同风险分析中的工作效率。

本次改造不重写 Twenty 核心 CRM 能力，而是在原有公司、联系人、客户、商机等业务数据基础上，新增独立 AI 能力模块。

## 改造范围

新增模块包括：

1. AI 知识库
2. AI 客户画像
3. AI 销售建议
4. 合同 / 产品文档问答
5. 回款 / 商机风险提醒

## 推荐架构

采用“Twenty CRM + 独立 AI Backend”的方式实现。

```text
Twenty CRM
  ├── Companies
  ├── People
  ├── Opportunities
  └── Tasks
        │
        ▼
AI Backend
  ├── FastAPI
  ├── PostgreSQL / pgvector
  ├── LangGraph
  ├── Embedding Service
  └── LLM API