# 开发文档

## 1. 概述

- **项目目标**：利用可插拔的信息收集策略与可切换的 LLM 供应商，自动生成符合团队规范（可自定义模板/Jinja2）的 Git commit message，并支持 Hook/CLI 一键集成。
- **核心设计约束**：
  - **多供应商 LLM 路由**：基于用户配置选择 Provider，后续可扩展自动路由策略。
  - **三大核心模块**：信息收集（Collector）→ 模型调用（LLM Router & Provider）→ 消息生成（Formatter）。
  - **强解耦 + SOLID 原则**：面向接口编程，抽象清晰，高内聚低耦合。
  - **模板引擎**：Jinja2，支持用户自定义模板与多规范。
  - **运行与依赖管理**：采用 uv。

---

## 2. 架构总览

- **数据流**：
  1. **信息收集层**：根据“收集策略”动态串联多个 Collector，产出统一上下文对象 Context。
  2. **模型调用层**：LLM Router 读取配置决策 Provider，Provider 实现 HTTP/Streaming 两种调用模式，支持被 Collector/Formatter 复用。
  3. **消息生成层**：Formatter 以 Jinja2 渲染模板，将模型输出与上下文融合，生成最终 commit message。

- **解耦要点**：
  - **依赖倒置**：CLI 与核心流程依赖抽象接口（Collector、Provider、Formatter），不依赖具体实现。
  - **开闭原则**：新增 Collector/Provider/模板无需修改现有类，仅通过注册/配置生效。
  - **接口隔离**：各接口仅暴露最小必要方法。
  - **单一职责**：Collector 只收集信息；Provider 只负责模型调用；Formatter 只负责模板渲染与规范化。

- **建议目录结构**：
  ```
  ai-git-commit-msg/
  ├── cli.py
  ├── core/
  │   ├── pipeline.py               # 编排：装配策略 → 收集 → 生成 → 输出
  │   ├── contracts/                # 抽象接口与数据模型
  │   │   ├── collector.py
  │   │   ├── provider.py
  │   │   └── formatter.py
  │   ├── collectors/               # 信息收集实现
  │   │   ├── diff_collector.py
  │   │   ├── readme_collector.py
  │   │   ├── history_collector.py
  │   │   ├── issue_collector.py    # 外部工具/平台集成
  │   │   └── mcp_collector.py      # MCP 协议集成
  │   ├── llm/
  │   │   ├── router.py
  │   │   └── providers/
  │   │       ├── openai.py
  │   │       ├── claude.py
  │   │       └── deepseek.py
  │   ├── formatter/
  │   │   ├── jinja_formatter.py
  │   │   └── templates/
  │   │       ├── conventional.j2
  │   │       └── custom/           # 用户自定义模板目录（可在全局配置中指定路径）
  │   └── registry.py               # 轻量插件注册表（可选）
  ├── config/
  │   ├── default.yaml
  ├── utils/
  │   ├── logger.py
  │   └── errors.py
  └── tests/
  ```

---

## 3. 模块规范与接口

### 3.1 信息收集层（Collector）

- **目标**：可配置、可扩展、统一输出。
- **统一接口**：
  ```python
  # core/contracts/collector.py
  from typing import Protocol, Mapping, Any

  class Collector(Protocol):
      def collect(self) -> Mapping[str, Any]:
          ...
  ```
- **上下文数据模型（建议）**：
  ```python
  # core/contracts/context_model.py（可选：pydantic）
  from pydantic import BaseModel
  from typing import List, Optional, Dict, Any

  class FileChange(BaseModel):
      path: str
      diff: str
      language: Optional[str] = None
      functions: Optional[List[str]] = None

  class Context(BaseModel):
      files: List[FileChange] = []
      readme: Optional[str] = None
      recent_commits: List[str] = []
      issues: List[Dict[str, Any]] = []
      meta: Dict[str, Any] = {}  # branch, repo, author, time, etc.
  ```
- **内置 Collector 设计**：
  - **DiffCollector**：收集 `git diff --cached` 与文件路径，必要时提取函数签名。
  - **ReadmeCollector**：读取根目录 `README.md`；可选用 Provider 对 README 做摘要。
  - **HistoryCommitCollector**：按文件或全仓库抓取最近 N 条 commit message。
  - **IssueCollector**：通过外部 API（如 GitHub/GitLab/Jira）按任务号拉取 Issue 标题/描述/标签。
  - **MCPCollector**：通过 MCP 与外部工具交互（如代码索引、规范库、设计文档），并将返回纳入 Context。
- **收集策略（可配置流水线）**：
  ```yaml
  collectors:
    - type: diff
      options:
        staged_only: true
        detect_functions: true
    - type: readme
      options:
        summarize_with_llm: false
    - type: history
      options:
        scope: "repo"          # 或 "file"
        limit: 5
    - type: issue
      options:
        provider: "github"
        token: ${GITHUB_TOKEN}
        derive_issue_from_branch: true
    - type: mcp
      options:
        tools: ["spec_index", "design_notes"]
        timeout_sec: 10
  ```
- **关键约束**：
  - **可扩展**：新 Collector 只需实现 `collect()` 并在注册表中登记。
  - **可并行**：不同 Collector 可并行执行，Pipeline 负责聚合与冲突合并。
  - **可降级**：某个 Collector 失败不应阻断整体流程，记录告警并跳过。

### 3.2 模型调用层（LLM Router & Provider）

- **目标**：按用户配置选择 Provider；遵循单一职责；支持 HTTP + Streaming。
- **Provider 接口**：
  ```python
  # core/contracts/provider.py
  from typing import Iterable, Union, Protocol

  class LLMProvider(Protocol):
      def generate(self, prompt: str, *, stream: bool = False) -> Union[str, Iterable[str]]:
          ...
  ```
- **Router 规范**：
  - **输入**：配置中的 `provider` 与 `model` 字段。
  - **行为**：实例化对应 Provider；不参与调用细节与重试逻辑。
  - **后续扩展**：可新增“自动路由”策略（基于 token 预算、延迟、可用性、合规域等）。
- **Provider 实现要求**：
  - **HTTP**：一次性返回完整文本。
  - **Streaming**：逐片段产出，CLI 在 TTY 场景按片段渲染。
  - **无业务逻辑**：仅封装认证、API 路径、重试、超时、错误翻译。
  - **被 Collector 复用**：允许 Collector 借用 Provider 对上下文做摘要/结构化提炼。
- **错误与重试**：
  - **可重试错误**：网络超时、限流、5xx 按指数退避。
  - **不可重试**：鉴权失败、配额不足，直接中止并提示。

### 3.3 消息生成层（Formatter）

- **目标**：Jinja2 模板渲染；用户可自定义模板与规范；与业务完全解耦。
- **接口**：
  ```python
  # core/contracts/formatter.py
  from typing import Protocol
  from .context_model import Context

  class Formatter(Protocol):
      def format(self, ctx: Context, model_output: str) -> str:
          ...
  ```
- **Jinja2 实现要点**：
  - **模板输入**：`ctx`（上下文对象）、`model_output`（LLM 结果）、`now()` 等辅助函数。
  - **默认模板**：`conventional.j2`（支持 type/scope/subject/body/footer）。
  - **用户自定义**：通过配置指向模板路径，允许项目内覆盖默认模板。
- **模板示例**（conventional.j2）：
  ```jinja2
  {{ type }}{% if scope %}({{ scope }}){% endif %}: {{ subject }}

  {% if body -%}
  {{ body }}
  {%- endif %}

  {% if breaking -%}
  BREAKING CHANGE: {{ breaking }}
  {%- endif %}

  {% if issues and issues|length > 0 -%}
  {% for it in issues %}
  Closes #{{ it.number }}{% if it.title %}: {{ it.title }}{% endif %}
  {% endfor -%}
  {%- endif %}
  ```
- **范式建议**：
  - **格式化职责单一**：不直接调用 LLM；如需二次润色，交由 Provider 先处理后再渲染模板。
  - **本地校验**：渲染前做长度、禁用词、换行限制校验；渲染后做空值裁剪。

---

## 4. 配置与策略

- **配置来源优先级**：环境变量 > CLI 参数 > 项目级配置 > 用户全局配置 > 默认值。
- **示例配置（~/.aicommit/config.yaml）**：
  ```yaml
  model:
    provider: "openai"
    name: "gpt-4o-mini"
    api_key: "${OPENAI_API_KEY}"
    timeout_sec: 20

  formatter:
    template: "conventional.j2"
    template_dir: "~/.aicommit/templates"

  collectors:
    - type: "diff"
      options:
        staged_only: true
        detect_functions: true
    - type: "history"
      options:
        scope: "file"
        limit: 5
    - type: "issue"
      options:
        provider: "github"
        token: "${GITHUB_TOKEN}"
        derive_issue_from_branch: true

  output:
    language: "en"        # 或 "zh"
    max_subject_len: 72
    wrap_body_at: 100
  ```
- **策略解读**：
  - **收集策略**：以数组声明 Collector 顺序，支持启停与参数化。
  - **模板策略**：支持全局模板目录与项目内覆盖。
  - **语言策略**：可提示 LLM 输出目标语言，或在 Formatter 中本地化固定短语。

---

## 5. CLI 与集成

- **核心命令**：
  - **aicommit**：生成并写入待提交消息（可支持 `--dry-run` 仅打印）。
  - **aicommit --stream**：流式生成，终端实时渲染。
  - **aicommit --provider openai --model gpt-4o-mini --format ./my_template.j2**：临时覆盖配置。
- **常用参数**：
  - **--provider/--model**：选择 LLM。
  - **--template/--template-dir**：启用自定义模板。
  - **--dry-run**：只生成不提交。
  - **--stream**：启用流式输出。
  - **--verbose**：输出调试日志。
- **Git Hook 集成**：
  - **prepare-commit-msg**：在提交前生成/覆盖消息；提供 `--no-overwrite` 选项以尊重已有手写内容。
- **IDE/CI 集成建议**：
  - **IDE**：通过简单 HTTP 本地服务或 CLI task 集成到 VSCode/JetBrains。
  - **CI**：在 PR 检查中验证提交信息风格与长度，非强制阻断开发者本地提交流程。

---

## 6. 开发与环境（uv）

- **初始化**：
  - **创建项目**：
    - **uv init**：初始化 pyproject
    - **uv add**：添加依赖（jinja2、pydantic、pytest、httpx、rich 或 textual、pyyaml）
  - **运行命令**：
    - **uv run python cli.py --dry-run**
    - **uv run pytest**
- **依赖建议**：
  - **http**：httpx（同步/异步可选，其流式支持友好）
  - **模板**：jinja2
  - **配置**：pydantic + pyyaml
  - **日志**：loguru 或标准 logging
  - **CLI 展示**：rich（渲染流式输出与高亮）
- **打包与发布**：
  - **入口点**：在 pyproject 中声明 console_scripts：`aicommit=ai_git_commit_msg.cli:main`
  - **跨平台**：确保仅依赖纯 Python 或可选二进制包的软依赖。

---

## 7. 质量、测试与可观测性

- **单元测试**：
  - **Collector**：模拟 git 与文件系统；对 `issue_collector`、`mcp_collector` 使用 HTTP/MCP mock。
  - **Provider**：使用契约测试与假服务器，覆盖 HTTP 与 Streaming。
  - **Formatter**：对模板做 Golden Test（快照），覆盖边界：空上下文、超长 subject、断行。
- **集成测试**：
  - **端到端**：构造一个演示仓库，在 CI 中执行真实流程，断言输出格式。
- **可观测性**：
  - **结构化日志**：请求 ID、Provider 名称、延迟、重试次数。
  - **调试选项**：`--verbose` 打印关键 prompt/上下文尺寸（注意隐私）。
  - **遥测埋点（可选）**：匿名统计成功率、延迟分布、回退触发率。

---

## 8. 错误处理、性能与缓存

- **错误策略**：
  - **Collector 失败**：记录警告并继续；除非策略标记为必需，否则不阻断生成。
  - **Provider 失败**：按可重试错误自动重试；最终失败回退到“规则模板占位”版本（降级可控）。
  - **模板渲染失败**：回退到安全模板（最小提交信息），并报告渲染错误。
- **性能优化**：
  - **并行收集**：并行执行独立 Collector。
  - **上下文裁剪**：对 diff 做启发式截断（按文件、按函数、按行数阈值）。
  - **增量策略**：非首提时仅收集变更相关上下文。
- **缓存**：
  - **输入→输出缓存**：基于 diff 哈希缓存 LLM 结果；命中时直接返回。
  - **可配置失效**：按时间/分支/文件路径触发失效。

---

## 9. 安全与合规

- **密钥管理**：
  - **环境变量优先**：如 `${OPENAI_API_KEY}`、`${GITHUB_TOKEN}`。
  - **禁止入库**：配置文件中仅保留占位符，不提交明文密钥。
- **最小化上传**：
  - **上下文脱敏**：支持文件白名单/黑名单；对敏感路径与密钥匹配进行 Mask。
  - **外发策略**：允许在配置中关闭 README/历史/Issue 等外发内容。
- **审计**：
  - **日志脱敏**：避免打印完整 diff/密钥；在调试模式下也需遵守。

---

## 10. 路线图与非目标

- **近期目标**：
  - **完成抽象层**：Collector/Provider/Formatter 接口与基础实现。
  - **三类 Collector**：diff、readme、history；可选 Issue。
  - **三类 Provider**：OpenAI、Claude、DeepSeek；HTTP + Streaming。
  - **Jinja2 模板**：内置 Conventional 与一个自定义示例。
  - **Hook 与 CLI**：`prepare-commit-msg` 与 `aicommit --stream`.
- **中期演进**：
  - **MCP 集成**：MCPCollector 支持声明式工具调用与合并策略。
  - **自动路由**：基于 token/延迟/成本的智能 Provider 选择。
  - **多语言**：模板与 Prompt 双通道本地化；语言自动检测。
  - **IDE 扩展**：VSCode/JetBrains 简单面板与一键替换。
- **非目标（当前阶段）**：
  - **长文档端到端理解**：不做全库语义索引（通过 MCP/外部工具解决）。
  - **生成式变更描述强绑定**：Formatter 保持纯模板渲染，不直接嵌入 LLM 调用。
