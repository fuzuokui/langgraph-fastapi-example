## 聊天机器人（LangGraph + DeepSeek + FastAPI）

一个基于 LangGraph 构建的可组合对话工作流，集成 DeepSeek 模型，支持工具调用（查询天气、腾讯翻译、时间查询），提供命令行交互与 RESTful API 两种使用方式，并输出工作流的 Mermaid 图。

### 功能特性
- **工作流驱动**：使用 LangGraph 的 `StateGraph` 编排结点与边，清晰可视化。
- **模型接入**：通过 `OpenAI` SDK 以 DeepSeek API 作为后端。
- **工具调用**：内置天气查询、腾讯翻译、当前时间查询。
- **两种使用方式**：
  - 终端交互：直接运行 `_main.py`。
  - Web API：基于 FastAPI 暴露 `/AIchat/` 接口。
- **Mermaid 可视化**：自动在 `workflow/workflow.mermaid` 生成工作流图。
- **日志记录**：统一记录到 `log/app.log`（配置见 `log/logger.py`）。

### 目录结构
```
e:\Python\langgraph\聊天机器人\
  - _main.py                # 交互式主程序，构建工作流并运行
  - base_node.py            # 基础结点：开始/结束与汇总
  - ai_node.py              # AI 结点：意图分析与回复生成
  - tools.py                # 工具层：天气/翻译/时间 + 工具编排
  - config.py               # DeepSeek 客户端、状态类型、记忆管理
  - api/
    - api.py                # FastAPI 应用与 /AIchat/ 接口
    - run_api_server.py     # 启动 Uvicorn 的入口
    - test_api.py           # 简单的本地请求测试脚本
  - log/
    - logger.py             # 日志配置（输出到 log/app.log）
  - workflow/
    - workflow.mermaid      # 运行后自动生成的工作流 Mermaid 文件
```

### 环境准备
- Python 3.10+（建议 3.10 或以上）
- Windows PowerShell（或任意终端）
- 依赖库（pip 安装）：
  - `openai`、`langgraph`、`fastapi`、`uvicorn`、`python-dotenv`、`requests`、`tiktoken`
  - 可选：`graphviz`（如需将 Mermaid 转为图片）

可以在项目根目录创建并激活虚拟环境，然后安装依赖：

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -U pip
pip install openai langgraph fastapi uvicorn python-dotenv requests tiktoken
# 可选
pip install graphviz
```

### 环境变量
本项目通过 `python-dotenv` 读取 `.env`，也可直接使用系统环境变量。推荐在项目根目录创建 `.env`：

```env
# DeepSeek / OpenAI 兼容 API
OPENAI_API_KEY=你的DeepSeek_API_Key

# WeatherAPI（https://www.weatherapi.com/）
WEATHER_API_KEY=你的WeatherAPI_Key

# 腾讯云翻译（TMT）签名所需
SECRET_ID=你的SecretId
SECRET_KEY=你的SecretKey
```

> 备注：
> - DeepSeek 默认 base_url 为 `https://api.deepseek.com`，如需自定义可在 `create_deepseek_client` 传参。
> - 未配置对应 Key 的工具将不可用或报错，请按需配置。

### 运行方式一：终端交互
在项目根目录执行：

```powershell
python _main.py
```

交互指令：
- 输入任意内容与 AI 对话
- 输入 `show` 显示历史对话
- 输入 `clear` 清空历史对话
- 输入 `quit` 退出程序

运行后会自动在 `workflow/workflow.mermaid` 生成最新工作流图。

### 运行方式二：启动 API 服务
在项目根目录执行：

```powershell
python api\run_api_server.py
```

默认监听：`http://127.0.0.1:8000`

- 接口：`POST /AIchat/`
- 请求体：

```json
{
  "user_input": "今天天气如何？"
}
```

- 响应体：

```json
{
  "ai_reply": "..."
}
```

快速测试（PowerShell）：

```powershell
python api\test_api.py
```

或使用 `Invoke-RestMethod`：

```powershell
$body = @{ user_input = "帮我把下面英文翻译成中文：Hello World" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/AIchat/ -Body $body -ContentType "application/json"
```

### 工作流说明（简要）
- 入口结点：`start`
- `analyze_input`：调用 DeepSeek 对用户输入进行意图分析，决定是否调用工具
- 条件分支：`need_tool` → `call_tool` 或直接 `generate_response`
- `call_tool`：顺序执行配置在 `state.tool_usage` 的工具，结果写入 `state.tool_results`
- `generate_response`：结合主题提示与工具结果生成流式回复，并计入会话历史
- `end`：汇总 token 使用，写入 `state.summary`

Mermaid 文件在运行时生成，可在任意支持 Mermaid 的查看器中展示。

### 日志
- 日志目录：`log/`
- 日志文件：`log/app.log`
- 日志内容包含：结点进入/完成、工具调用、异常信息、token 统计等。

### 常见问题
- 初始化报错 “未设置 OPENAI_API_KEY”：请在 `.env` 中配置 `OPENAI_API_KEY`，或设置为系统环境变量。
- 工具不可用：确保相应的 Key（如 `WEATHER_API_KEY`、`SECRET_ID/SECRET_KEY`）已配置。
- 请求 500：查看控制台与 `log/app.log`，检查上游 API 与网络连通性。




