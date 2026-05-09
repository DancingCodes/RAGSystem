# RAGSystem API 接口文档

Base URL: `http://127.0.0.1:8000`

---

## 整体架构

```
PDF 上传 → 解析 → 分块 → Embedding (bge-small-zh-v1.5) → Qdrant 向量库
                                                              ↓
用户提问 → Embedding → 向量检索(top_k) → DeepSeek 生成答案 → 返回引用
```

| 组件 | 技术 | 说明 |
|------|------|------|
| Web 框架 | FastAPI | Python 异步 |
| 数据库 | MySQL | 知识库、文件、chunk 元数据 |
| 向量库 | Qdrant | 存储文本向量，COSINE 相似度检索 |
| Embedding | BAAI/bge-small-zh-v1.5 | 本地运行，512 维，L2 归一化 |
| LLM 生成 | DeepSeek V3 (`deepseek-chat`) | API 调用，返回带引用的答案 |

---

## 1. 知识库管理

### 1.1 创建知识库

`POST /api/knowledge-bases`

**请求体：**

```json
{
    "name": "测试知识库"
}
```

**响应示例：**

```json
{
    "code": 200,
    "msg": "ok",
    "data": {
        "id": "a1b2c3d4e5f6a7b8",
        "name": "测试知识库"
    }
}
```

---

### 1.2 查询知识库列表

`GET /api/knowledge-bases`

**响应示例：**

```json
{
    "code": 200,
    "msg": "ok",
    "data": [
        {
            "id": "a1b2c3d4e5f6a7b8",
            "name": "测试知识库"
        }
    ]
}
```

---

### 1.3 删除知识库

`DELETE /api/knowledge-bases/{knowledge_base_id}`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| knowledge_base_id | path (string) | 是 | 知识库 ID |

> 同时删除该知识库下的所有文件、chunk 和 Qdrant 向量数据。

**模拟请求：**

```
DELETE /api/knowledge-bases/a1b2c3d4e5f6a7b8
```

**响应示例：**

```json
{
    "code": 200,
    "msg": "ok",
    "data": null
}
```

---

## 2. 文档上传（同步处理）

`POST /api/documents`

Content-Type: `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | file | 是 | PDF 文件 |
| knowledge_base_id | string | 是 | 目标知识库 ID |

**处理流程：**

```
1. 接收文件 → 保存到 data/uploads/{file_id}.pdf
2. 写入 MySQL（FileRecord, status=processing）
3. pypdf 逐页提取文本 → 规范化空白字符
4. 按段落分块（target=900 字符, overlap=120 字符）
5. 每块写入 MySQL（Chunk 表）
6. 批处理（64 条/批）调用 bge-small-zh-v1.5 生成向量
7. 写入 Qdrant（collection: rag_chunks, COSINE 距离）
8. 更新 FileRecord status=succeeded → 返回
```

> 整个流程同步完成，接口返回即表示文档已入库且可检索。

**Apifox 配置：**

- Body 选 `form-data`
- `file` → 字段类型选 `file`，上传一个 PDF
- `knowledge_base_id` → 字段类型选 `text`，填入知识库 ID

**响应示例：**

```json
{
    "code": 200,
    "msg": "ok",
    "data": {
        "id": "f8e7d6c5b4a3f2e1",
        "file_name": "RAG设计文档.pdf"
    }
}
```

---

## 3. RAG 对话问答

`POST /api/chat`

**请求体：**

```json
{
    "knowledge_base_id": "a1b2c3d4e5f6a7b8",
    "question": "RAG系统的整体架构是什么？",
    "top_k": 5
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| knowledge_base_id | string | 是 | 知识库 ID |
| question | string | 是 | 提问内容 |
| top_k | int | 否 | 检索片段数，默认 5，范围 1-20 |

**处理流程：**

```
1. 问题文本 → bge-small-zh-v1.5 生成向量 (512 维, L2 归一化)
2. Qdrant COSINE 相似度检索 → 取 top_k 条最相关 chunk
3. 构建 context：拼接 [文件/页码/片段内容]（按相似度排序）
4. System Prompt: "你是检索增强问答助手，只依据资料片段回答；不足时说明未找到依据"
5. 调用 DeepSeek V3 (temperature=0.2, stream=true) → 逐 token 生成答案
6. 返回 SSE 流式响应
```

**响应格式（SSE）：**

Content-Type: `text/event-stream`

| 事件类型 | 说明 | 示例 |
|---------|------|------|
| `token` | 答案文本片段 | `{"type":"token","content":"RAG系统"}` |
| `done` | 生成完成，携带引用列表 | `{"type":"done","citations":[...]}` |
| `error` | 生成失败 | `{"type":"error","message":"llm generate failed"}` |

```
event: token
data: {"type":"token","content":"RAG系统"}

event: done
data: {"type":"done","citations":[{"file_name":"RAG设计文档.pdf","page_number":3,"text":"系统架构采用分层设计"}]}
```

引用中 `text` 字段截取前 60 字符。

---

## 4. 分块策略

| 参数 | 值 | 说明 |
|------|------|------|
| target_size | 900 字符 | 每个 chunk 目标大小 |
| overlap | 120 字符 | 相邻 chunk 重叠区域，保证语义连贯 |
| 分隔符 | `\n\n` | 优先按自然段落拆分 |

---

## 5. 测试流程

Apifox 中按顺序调：

1. **创建知识库** → 拿到 `knowledge_base_id`
2. **上传 PDF** → 填入 `knowledge_base_id`，等待响应（大文件约 5-30 秒）
3. **发起对话** → 填入 `knowledge_base_id` + 问题

---

## 6. 通用响应格式

```json
{
    "code": 200,
    "msg": "ok",
    "data": {}
}
```

| code | 含义 |
|------|------|
| 200 | 成功 |
| 500 | 失败（msg 中返回错误原因） |
