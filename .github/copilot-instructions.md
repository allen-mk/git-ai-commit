# Project Overview
本项目 **ai-git-commit-msg** 是一个 CLI 工具，用于通过多种大语言模型（LLM）自动生成符合团队规范的 Git commit message。  
目标是提供可扩展、可配置、可插拔的架构，支持多供应商 LLM 路由、灵活的信息收集策略，以及基于 Jinja2 的模板化输出。  
运行与依赖管理使用 **uv**。

## Architecture & Core Modules
项目核心分为三大模块，遵循 **SOLID 原则**，高内聚、低耦合：

1. **信息收集（Collector）**  
   - 收集 `git diff --cached`、项目 README、历史提交记录、Issue 信息等上下文  
   - 支持通过 LLM 或 MCP 协议进行信息预处理  
   - 可配置收集策略，Collector 可自由扩展

2. **模型调用（LLM Router & Provider）**  
   - LLM 路由根据用户配置选择供应商（OpenAI、Claude、DeepSeek、本地模型等）  
   - Provider 仅负责模型调用，支持 HTTP 与 Streaming 两种模式  
   - Collector 也可复用 Provider 做摘要或结构化处理

3. **消息生成（Formatter）**  
   - 使用 Jinja2 模板渲染 commit message  
   - 支持 Conventional Commits、自定义模板  
   - 模板可在项目或用户目录中扩展

## Folder Structure
```
/core
  /collectors       # 信息收集模块
  /llm              # LLM 路由与 Provider
  /formatter        # 消息生成模块与模板
  /contracts        # 抽象接口与数据模型
/config             # 默认与用户配置
/utils              # 工具与日志
/tests              # 测试用例
```

## Coding Standards
- **语言与工具**：Python 3.9+，使用 `uv` 管理依赖与运行环境
- **代码风格**：PEP8 + Black 格式化
- **命名规范**：
  - 变量/函数：`snake_case`
  - 类名：`PascalCase`
  - 常量：`UPPER_SNAKE_CASE`
- **注释**：
  - 公共方法必须有 docstring
  - 复杂逻辑需行内注释
- **禁止**：
  - 魔法数字（Magic Number）
  - 无意义命名（如 `tmp`, `data1`）

## Development Guidelines for Copilot
在生成代码时：
- 遵循模块边界，不跨模块直接访问内部实现
- 新功能优先通过新增类/函数实现，避免修改现有核心逻辑
- 对外部 API 调用（LLM、MCP、Issue Tracker）使用抽象接口

在生成模板或文档时：
- 使用 Jinja2 语法，保持模板变量命名清晰
- 遵循 Conventional Commits 格式，或读取配置中指定的模板

在生成测试时：
- 对 Collector、Provider、Formatter 分别编写单元测试
- 对 LLM 调用使用 mock，避免真实请求
- 对模板渲染使用快照测试（Golden Test）

## Libraries and Frameworks
- **核心依赖**：
  - `jinja2`（模板引擎）
  - `pydantic`（数据模型与配置解析）
  - `httpx`（HTTP/Streaming 调用）
  - `pytest`（测试框架）
  - `loguru`（日志）
- **可选依赖**：
  - `rich`（CLI 输出美化）
  - `pyyaml`（YAML 配置解析）