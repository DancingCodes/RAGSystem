# 后端（FastAPI）

## 1. 安装依赖

在项目根目录下执行：

```bash
python -m pip install -r backend/requirements.txt
```

## 2. 启动

不要直接用 `python backend/app/main.py` 启动（会触发相对导入错误）。请使用 uvicorn 按“模块路径”启动。

Windows（PowerShell）在 `backend/` 目录下执行：

```bash
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

如果你的虚拟环境建在项目根目录（例如 `.venv/` 在 `RAGSystem/.venv`），则在项目根目录执行：

```bash
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000 --app-dir backend
```

macOS/Linux 在 `backend/` 目录下执行：

```bash
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

默认会使用 SQLite：`backend/data/app.db`，并将上传 PDF 保存到：`backend/data/uploads/`。

## 3. 环境变量（可选）

- `DATABASE_URL`：数据库连接串（不填则使用本地 SQLite）
- `OPENAI_BASE_URL`：OpenAI 兼容接口地址（默认 `https://api.openai.com/v1`）
- `OPENAI_API_KEY`：API Key
- `OPENAI_MODEL`：模型名

不配置大模型时，`/api/chat` 会返回检索片段拼接的结果，用于先验证检索与引用链路。

## 4. API（与前端对齐）

- `GET /api/health`
- `GET /api/knowledge-bases`
- `POST /api/knowledge-bases`：`{ "name": "xxx" }`
- `POST /api/files`：`multipart/form-data`，字段：
  - `knowledge_base_id`
  - `file`（PDF）
- `POST /api/chat`：`{ "knowledge_base_id": "...", "question": "...", "top_k": 5 }`
