# AI Git Commit Message - 开发任务清单

## 项目概览
本文档基于 DEVELOP_Doc.md 制定，按照优先级和依赖关系组织开发任务。
- **P0**: 必需功能，MVP核心
- **P1**: 重要功能，完整产品
- **P2**: 可选功能，增强体验

---

## 🚀 阶段一：项目基础设施 (Week 1)

### 1.1 项目初始化 [P0]
- [x] 1.1.1 初始化 uv 项目结构
  - [x] 运行 `uv init` 创建 pyproject.toml
  - [x] 配置 Python 版本要求 (3.9+)
  - [x] 设置项目元数据和描述
- [x] 1.1.2 创建基础目录结构
  ```
  ai-git-commit-msg/
  ├── cli.py
  ├── core/
  │   ├── __init__.py
  │   ├── pipeline.py
  │   ├── contracts/
  │   ├── collectors/
  │   ├── llm/
  │   ├── formatter/
  │   └── registry.py
  ├── config/
  ├── utils/
  └── tests/
  ```
- [x] 1.1.3 添加核心依赖
  - [x] `uv add jinja2 pydantic httpx pytest loguru rich pyyaml`
- [x] 1.1.4 配置开发工具
  - [x] 添加 Black, isort, mypy 作为开发依赖
  - [x] 创建 .gitignore 文件
  - [ ] 配置 pre-commit hooks (可选)

**验收标准**: 项目结构完整，依赖正确安装，`uv run python -c "import jinja2"` 成功执行

### 1.2 基础设施模块 [P0]
- [x] 1.2.1 日志系统 (`utils/logger.py`)
  - [x] 基于 loguru 的结构化日志
  - [x] 支持不同日志级别和格式
  - [x] 文件和控制台输出配置
- [x] 1.2.2 错误处理 (`utils/errors.py`)
  - [x] 定义项目特定异常类
  - [x] CollectorError, ProviderError, FormatterError
  - [x] 优雅错误处理和用户友好提示
- [x] 1.2.3 配置系统基础 (`config/`)
  - [x] 配置文件加载器（YAML/JSON）
  - [x] 环境变量替换支持
  - [x] 配置优先级处理逻辑

**验收标准**: 基础模块可独立导入使用，错误处理覆盖主要异常场景

---

## 🏗️ 阶段二：核心抽象层 (Week 2)

### 2.1 数据模型定义 [P0]
- [x] 2.1.1 核心数据结构 (`core/contracts/models.py`)
  - [x] FileChange 模型（路径、diff、语言、函数列表）
  - [x] Context 模型（文件列表、README、历史提交、Issue、元数据）
  - [x] 使用 pydantic 进行数据验证

- [x] 2.1.2 配置模型 (`config/models.py`)
  - [x] ModelConfig（provider、name、api_key、timeout）
  - [x] CollectorConfig 配置数组
  - [x] FormatterConfig（template、template_dir）
  - [x] OutputConfig（语言、长度限制）

**验收标准**: 所有数据模型定义完整，通过 pydantic 验证测试

### 2.2 抽象接口定义 [P0]
- [x] 2.2.1 Collector 协议 (`core/contracts/collector.py`)
  - [x] 定义 `collect() -> Mapping[str, Any]` 方法
  - [x] 可选的初始化和配置参数
- [x] 2.2.2 Provider 协议 (`core/contracts/provider.py`)
  - [x] 定义 `generate(prompt: str, *, stream: bool = False)` 方法
  - [x] 支持同步和异步调用模式
- [x] 2.2.3 Formatter 协议 (`core/contracts/formatter.py`)
  - [x] 定义 `format(ctx: Context, model_output: str) -> str` 方法

**验收标准**: 接口定义清晰，通过 mypy 类型检查

### 2.3 注册表机制 [P1]
- [x] 2.3.1 组件注册表 (`core/registry.py`)
  - [x] Collector 注册和发现机制
  - [x] Provider 注册和发现机制
  - [x] 基于字符串名称的组件实例化

**验收标准**: 注册表支持动态组件加载和实例化

---

## 💼 阶段三：核心模块MVP (Week 3-4)

### 3.1 基础 Collector 实现 [P0]
- [x] 3.1.1 DiffCollector (`core/collectors/diff_collector.py`)
  - [x] 执行 `git diff --cached` 获取暂存区变更
  - [ ] 解析 diff 输出，提取文件路径和变更内容
  - [ ] 可选的函数签名检测（基于语言）
  - [ ] 处理二进制文件和大文件场景
- [x] 3.1.2 ReadmeCollector (`core/collectors/readme_collector.py`)
  - [x] 在项目根目录查找 README.md/README.rst
  - [x] 提取项目描述和关键信息
  - [ ] 可选的 LLM 摘要功能（通过 Provider）
- [x] 3.1.3 HistoryCollector (`core/collectors/history_collector.py`)
  - [x] 获取最近 N 次提交记录
  - [ ] 支持按文件范围或全仓库范围
  - [ ] 解析提交消息格式和风格

**验收标准**: 基础 Collector 能正确收集对应信息，处理边界情况

### 3.2 基础 Provider 实现 [P0]
- [x] 3.2.1 OpenAI Provider (`core/llm/providers/openai.py`)
  - [x] 实现 HTTP 调用模式
  - [x] 实现 Streaming 调用模式
  - [x] API 密钥管理和错误处理
  - [x] 重试机制和超时配置
- [x] 3.2.2 LLM Router (`core/llm/router.py`)
  - [x] 根据配置选择 Provider
  - [x] Provider 实例化和配置传递
  - [x] 基础的路由逻辑

**验收标准**: OpenAI Provider 正常工作，Router 能正确路由请求

### 3.3 基础 Formatter 实现 [P0]
- [x] 3.3.1 Jinja2 Formatter (`core/formatter/jinja_formatter.py`)
  - [x] 模板加载和渲染逻辑
  - [x] 支持模板目录配置
  - [x] 模板变量注入（ctx、model_output、now等）
- [x] 3.3.2 默认模板 (`core/formatter/templates/`)
  - [x] conventional.j2 - Conventional Commits 模板
  - [x] simple.j2 - 简单模板作为备选
  - [x] 模板语法验证和错误处理

**验收标准**: 模板渲染正常工作，输出符合 Conventional Commits 格式

### 3.4 核心流水线 [P0]
- [x] 3.4.1 Pipeline 编排 (`core/pipeline.py`)
  - [x] 收集阶段：并行执行多个 Collector
  - [x] 生成阶段：调用 LLM Provider
  - [x] 格式化阶段：模板渲染
  - [x] 错误处理和降级策略
- [x] 3.4.2 配置驱动的组件装配
  - [x] 根据配置文件动态创建 Collector 实例
  - [x] Provider 选择和参数传递
  - [x] 模板选择和自定义支持

**验收标准**: MVP Pipeline 端到端工作，能生成基础的 commit message

---

## 🖥️ 阶段四：CLI和基础集成 (Week 5)

### 4.1 CLI 入口点 [P0]
- [x] 4.1.1 命令行解析 (`cli.py`)
  - [x] 使用 argparse 或 click 实现
  - [x] 基础命令：`aicommit`
  - [x] 常用参数：--dry-run, --verbose, --config
- [x] 4.1.2 配置文件处理
  - [x] 默认配置文件 (`config/default.yaml`)
  - [x] 用户配置文件查找（~/.aicommit/config.yaml）
  - [x] 项目配置文件支持（.aicommit.yaml）
  - [x] 配置合并和优先级处理
- [x] 4.1.3 输出和交互
  - [x] Rich 美化输出
  - [x] 进度指示器
  - [x] 错误信息友好展示

**验收标准**: CLI 基础功能完整，`aicommit --dry-run` 能输出生成的 commit message

### 4.2 Git 集成 [P1]
- [x] 4.2.1 Git 仓库检测和验证
  - [x] 检查当前目录是否为 Git 仓库
  - [x] 检查是否有暂存区变更
  - [ ] 获取仓库元信息（分支、作者等）
- [x] 4.2.2 Commit Message 写入
  - [x] 直接执行 `git commit -m`
  - [x] 支持 `--dry-run` 仅展示不提交
  - [x] 处理提交失败情况

**验收标准**: Git 集成正常，能够完成端到端的 commit 流程

---

## 🔧 阶段五：扩展功能 (Week 6-7)

### 5.1 更多 Collector 实现 [P1]
- [ ] 5.1.1 IssueCollector (`core/collectors/issue_collector.py`)
  - [ ] GitHub API 集成
  - [ ] 根据分支名推导 Issue 号
  - [ ] GitLab 和 Jira 支持（可选）
- [ ] 5.1.2 MCPCollector (`core/collectors/mcp_collector.py`)
  - [ ] MCP 协议客户端实现
  - [ ] 声明式工具调用配置
  - [ ] 超时和错误处理

**验收标准**: 扩展 Collector 能正确集成外部信息源

### 5.2 更多 Provider 实现 [P1]
- [ ] 5.2.1 Claude Provider (`core/llm/providers/claude.py`)
  - [ ] Anthropic API 集成
  - [ ] Streaming 支持
- [ ] 5.2.2 DeepSeek Provider (`core/llm/providers/deepseek.py`)
  - [ ] DeepSeek API 集成
  - [ ] 中文优化处理
- [ ] 5.2.3 本地模型支持 (`core/llm/providers/local.py`)
  - [ ] Ollama 集成
  - [ ] OpenAI-compatible API 支持

**验收标准**: 多个 Provider 都能正常工作，支持配置切换

### 5.3 高级功能 [P1]
- [ ] 5.3.1 流式输出支持
  - [ ] CLI `--stream` 参数
  - [ ] 实时显示生成进度
  - [ ] Rich 组件集成
- [ ] 5.3.2 缓存机制
  - [ ] 基于 diff 哈希的结果缓存
  - [ ] 缓存失效策略
  - [ ] 缓存大小和生命周期管理
- [ ] 5.3.3 并行优化
  - [ ] Collector 并行执行
  - [ ] 异步 I/O 优化
  - [ ] 超时和取消机制

**验收标准**: 高级功能正常工作，显著提升用户体验

---

## 🔌 阶段六：Git Hook 集成 (Week 8)

### 6.1 Hook 脚本 [P1]
- [ ] 6.1.1 prepare-commit-msg Hook
  - [ ] Hook 脚本模板
  - [ ] 安装和卸载命令
  - [ ] 与手写消息的兼容处理
- [ ] 6.1.2 Hook 配置
  - [ ] --no-overwrite 选项
  - [ ] Hook 启用/禁用开关
  - [ ] 与现有 Hook 的兼容性

**验收标准**: Git Hook 安装后能自动生成 commit message，不干扰正常工作流

### 6.2 IDE 集成准备 [P2]
- [ ] 6.2.1 HTTP 服务模式 (可选)
  - [ ] 简单的本地 HTTP 服务
  - [ ] REST API 接口设计
  - [ ] VSCode/JetBrains 集成示例

**验收标准**: 提供 IDE 集成的技术方案和示例

---

## 🛡️ 阶段七：质量保证 (Week 9-10)

### 7.1 测试体系 [P0]
- [ ] 7.1.1 单元测试
  - [ ] Collector 测试（Mock Git/文件系统）
  - [ ] Provider 测试（Mock HTTP 响应）
  - [ ] Formatter 测试（Golden Test）
  - [ ] 覆盖率目标：80%+
- [ ] 7.1.2 集成测试
  - [ ] 端到端流程测试
  - [ ] 配置加载测试
  - [ ] 错误场景测试
- [ ] 7.1.3 测试数据和Mock
  - [ ] 测试用 Git 仓库
  - [ ] LLM 响应 Mock 数据
  - [ ] 配置文件测试用例

**验收标准**: 测试覆盖率达到要求，核心功能测试通过

### 7.2 安全和隐私 [P0]
- [ ] 7.2.1 密钥管理
  - [ ] 环境变量优先级
  - [ ] 配置文件脱敏检查
  - [ ] 敏感信息日志过滤
- [ ] 7.2.2 上下文安全
  - [ ] 敏感文件路径过滤
  - [ ] 大文件上传限制
  - [ ] PII 数据检测和遮盖

**验收标准**: 安全检查通过，不泄露敏感信息

### 7.3 性能和稳定性 [P1]
- [ ] 7.3.1 性能优化
  - [ ] 上下文大小限制和裁剪
  - [ ] 并发处理优化
  - [ ] 内存使用监控
- [ ] 7.3.2 错误处理完善
  - [ ] 网络超时和重试
  - [ ] 优雅降级机制
  - [ ] 用户友好的错误提示
- [ ] 7.3.3 日志和监控
  - [ ] 结构化日志完善
  - [ ] 调试信息输出
  - [ ] 性能指标收集

**验收标准**: 性能满足要求，错误处理覆盖主要场景

---

## 📚 阶段八：文档和发布 (Week 11)

### 8.1 用户文档 [P0]
- [ ] 8.1.1 README.md
  - [ ] 项目介绍和特性
  - [ ] 安装和快速开始
  - [ ] 基础使用示例
- [ ] 8.1.2 用户手册
  - [ ] 完整的配置选项说明
  - [ ] 模板自定义指南
  - [ ] 常见问题和故障排除
- [ ] 8.1.3 最佳实践
  - [ ] 团队使用指南
  - [ ] CI/CD 集成示例
  - [ ] 模板开发指南

**验收标准**: 文档完整，用户能够独立安装和使用

### 8.2 开发者文档 [P1]
- [ ] 8.2.1 API 文档
  - [ ] 核心接口说明
  - [ ] 扩展开发指南
  - [ ] 代码示例
- [ ] 8.2.2 架构文档
  - [ ] 设计原理说明
  - [ ] 模块依赖图
  - [ ] 扩展点说明

**验收标准**: 开发者能够理解架构并参与贡献

### 8.3 打包和分发 [P0]
- [ ] 8.3.1 PyPI 发布准备
  - [ ] pyproject.toml 配置完善
  - [ ] 版本管理策略
  - [ ] 长描述和分类信息
- [ ] 8.3.2 CI/CD 流水线
  - [ ] GitHub Actions 配置
  - [ ] 自动化测试和发布
  - [ ] 多平台兼容性测试

**验收标准**: 项目可以通过 pip 安装，CI/CD 流程正常

---

## 🚀 可选增强功能 (后续版本)

### 9.1 高级特性 [P2]
- [ ] 9.1.1 智能路由
  - [ ] 基于成本/延迟的自动 Provider 选择
  - [ ] 负载均衡和故障转移
- [ ] 9.1.2 多语言支持
  - [ ] 中英文模板和提示
  - [ ] 语言自动检测
- [ ] 9.1.3 高级缓存
  - [ ] 分布式缓存支持
  - [ ] 语义相似度缓存匹配

### 9.2 生态集成 [P2]
- [ ] 9.2.1 更多版本控制系统
  - [ ] Mercurial 支持
  - [ ] SVN 支持（如有需求）
- [ ] 9.2.2 更多 Issue 跟踪系统
  - [ ] Jira 完整集成
  - [ ] Azure DevOps 支持
  - [ ] Linear 支持
- [ ] 9.2.3 团队功能
  - [ ] 团队模板共享
  - [ ] 使用统计和分析
  - [ ] 批量配置管理

---

## 📊 里程碑和时间线

| 里程碑 | 主要交付物 |
|--------|------------|
| M1 |  项目基础设施完成，核心抽象层就绪 |
| M2 |  MVP 功能完成，基础三大模块可用 |
| M3 |  CLI 完成，基础集成可用 |
| M4 |  扩展功能完成，功能相对完整 |
| M5 |  Git Hook 集成，开发体验完善 |
| M6 |  质量保证完成，产品级稳定性 |
| M7 |  文档和发布，正式可用 |

---

## 📋 注意事项

1. **开发原则**
   - 严格遵循 SOLID 原则和项目编码规范
   - 每个模块都要有对应的单元测试
   - 公共方法必须有完整的 docstring
   - 使用 uv 进行所有依赖管理操作

2. **风险控制**
   - 外部 API 调用必须有超时和重试机制
   - 敏感信息处理要格外小心
   - 大文件和大量数据要有合理限制

3. **可扩展性**
   - 新功能优先通过接口扩展实现
   - 避免修改核心模块的既有逻辑
   - 保持模块间的清晰边界

4. **用户体验**
   - 错误信息要友好且可操作
   - 提供合理的默认配置
   - 支持渐进式功能使用

