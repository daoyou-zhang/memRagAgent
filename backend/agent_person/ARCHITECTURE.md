# Agent Person 架构设计

## 系统概览

Agent Person 是一个完整的 3D 智能人交互系统，整合了语音识别、语音合成、认知大脑和数字人渲染能力。

## 核心组件

### 1. API 层（api/）

负责处理 HTTP 和 WebSocket 请求。

```
api/
├── chat.py              # 聊天接口（文本/语音/WebSocket）
├── voice.py             # 语音接口（ASR/TTS）
└── digital_human.py     # 数字人接口
```

**主要端点：**

- `POST /api/v1/chat/text` - 文本聊天
- `POST /api/v1/chat/voice` - 语音聊天
- `WS /api/v1/chat/ws` - WebSocket 实时聊天
- `POST /api/v1/voice/asr` - 语音识别
- `POST /api/v1/voice/tts` - 语音合成
- `POST /api/v1/digital-human/generate` - 生成数字人视频

### 2. 服务层（services/）

封装外部服务调用和业务逻辑。

```
services/
├── brain_client.py          # 认知大脑客户端
├── asr_service.py           # 语音识别服务
├── tts_service.py           # 语音合成服务
└── digital_human_service.py # 数字人服务
```

**服务职责：**

| 服务 | 职责 | 外部依赖 |
|------|------|----------|
| BrainClient | 调用 daoyou_agent 认知服务 | daoyou_agent:8000 |
| ASRService | 语音转文字 | 阿里云 DashScope |
| TTSService | 文字转语音 | 阿里云 NLS |
| DigitalHumanService | 生成数字人视频 | 阿里云 DashScope |

### 3. 数据模型（models/）

定义请求/响应的数据结构。

```
models/
├── chat.py              # 聊天相关模型
└── digital_human.py     # 数字人相关模型
```

**核心模型：**

- `ChatRequest` - 聊天请求
- `ChatResponse` - 聊天响应
- `VoiceMessage` - 语音消息
- `DigitalHumanConfig` - 数字人配置
- `DigitalHumanRequest` - 数字人生成请求

## 数据流

### 文本聊天流程

```
用户输入
    │
    ▼
┌─────────────────────────────────────┐
│  POST /api/v1/chat/text             │
│  (api/chat.py)                      │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  BrainClient.process()              │
│  调用 daoyou_agent 认知服务         │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  daoyou_agent                       │
│  - 意图理解                         │
│  - 上下文聚合（memory + knowledge） │
│  - LLM 生成回复                     │
│  - 学习闭环                         │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  返回文本回复                       │
└─────────────────────────────────────┘
```

### 语音聊天流程

```
用户语音
    │
    ▼
┌─────────────────────────────────────┐
│  POST /api/v1/chat/voice            │
│  (api/chat.py)                      │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  ASRService.recognize()             │
│  语音 → 文字                        │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  BrainClient.process()              │
│  文字 → 认知处理 → 回复文字         │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  TTSService.synthesize()            │
│  文字 → 语音                        │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  返回文本 + 语音                    │
└─────────────────────────────────────┘
```

### 数字人聊天流程

```
用户输入
    │
    ▼
┌─────────────────────────────────────┐
│  POST /api/v1/chat/text             │
│  enable_digital_human=true          │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  BrainClient.process()              │
│  获取回复文本                       │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  TTSService.synthesize()            │
│  生成语音                           │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  DigitalHumanService.generate()     │
│  文本 + 语音 → 数字人视频           │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  返回文本 + 语音 + 视频             │
└─────────────────────────────────────┘
```

### WebSocket 实时流程

```
WebSocket 连接
    │
    ▼
┌─────────────────────────────────────┐
│  WS /api/v1/chat/ws                 │
│  建立连接                           │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  接收消息循环                       │
│  while True:                        │
│    data = await receive()           │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  BrainClient.process_stream()       │
│  流式生成回复                       │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  async for chunk:                   │
│    await send(chunk)                │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  前端实时渲染                       │
└─────────────────────────────────────┘
```

## 技术选型

### 后端框架
- **FastAPI** - 高性能异步 Web 框架
- **WebSocket** - 实时双向通信
- **httpx** - 异步 HTTP 客户端
- **Pydantic** - 数据验证

### 外部服务
- **daoyou_agent** - 认知大脑（意图理解、上下文聚合、LLM 生成）
- **阿里云 DashScope** - ASR（Qwen3-ASR-Flash）+ 数字人
- **阿里云 NLS** - TTS（多种音色）

### 日志和监控
- **loguru** - 结构化日志
- **FastAPI 内置监控** - 请求追踪

## 扩展性设计

### 1. 服务解耦

每个服务都是独立的，可以单独替换：

```python
# 替换 ASR 服务
class CustomASRService:
    async def recognize(self, audio_data: bytes) -> str:
        # 自定义实现
        pass

# 使用自定义服务
_asr_service = CustomASRService()
```

### 2. 配置驱动

所有配置通过环境变量管理：

```env
# 切换不同的 ASR 提供商
ASR_PROVIDER=aliyun  # 或 google, azure, custom
```

### 3. 插件化

支持动态加载插件：

```python
# 注册自定义处理器
@app.on_event("startup")
async def load_plugins():
    plugin_manager.load("custom_plugin")
```

## 性能优化

### 1. 异步处理

所有 I/O 操作使用 async/await，避免阻塞：

```python
async def process():
    # 并发调用多个服务
    brain_task = brain_client.process(...)
    tts_task = tts_service.synthesize(...)
    
    brain_result, tts_result = await asyncio.gather(
        brain_task, tts_task
    )
```

### 2. 连接池

复用 HTTP 连接：

```python
# 单例模式
_client = httpx.AsyncClient(
    timeout=60.0,
    limits=httpx.Limits(max_connections=100)
)
```

### 3. 缓存策略

对频繁访问的数据使用缓存：

```python
# TTS 结果缓存
@lru_cache(maxsize=1000)
def get_cached_audio(text: str, voice: str) -> bytes:
    return tts_service.synthesize(text, voice)
```

### 4. 流式处理

大文件使用流式传输：

```python
async def stream_video():
    async for chunk in video_generator():
        yield chunk
```

## 安全考虑

### 1. 认证授权

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_token(credentials = Depends(security)):
    if not valid_token(credentials.credentials):
        raise HTTPException(status_code=401)
```

### 2. 速率限制

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/chat/text")
@limiter.limit("10/minute")
async def chat(request: ChatRequest):
    pass
```

### 3. 输入验证

使用 Pydantic 自动验证：

```python
class ChatRequest(BaseModel):
    input: str = Field(..., max_length=1000)
    user_id: str = Field(..., regex=r'^[a-zA-Z0-9_-]+$')
```

## 监控和日志

### 1. 结构化日志

```python
from loguru import logger

logger.info(
    "处理聊天请求",
    extra={
        "user_id": user_id,
        "session_id": session_id,
        "processing_time": elapsed,
    }
)
```

### 2. 性能追踪

```python
import time

@app.middleware("http")
async def add_process_time_header(request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    response.headers["X-Process-Time"] = str(elapsed)
    return response
```

### 3. 错误追踪

```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )
```

## 部署架构

### 开发环境

```
localhost:8001 (agent_person)
    ↓
localhost:8000 (daoyou_agent)
    ↓
localhost:5000 (memory)
```

### 生产环境

```
                    ┌─────────────┐
                    │   Nginx     │
                    │  (反向代理)  │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ agent_person │  │ daoyou_agent │  │   memory     │
│   (多实例)   │  │   (多实例)   │  │   (多实例)   │
└──────────────┘  └──────────────┘  └──────────────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                    ┌──────▼──────┐
                    │  PostgreSQL │
                    │    Redis    │
                    └─────────────┘
```

## 未来规划

### 短期（1-2 周）
- [ ] 完成阿里云 API 实际集成
- [ ] 实现音视频文件管理
- [ ] 添加单元测试

### 中期（1 个月）
- [ ] 流式处理优化
- [ ] 表情和动作控制
- [ ] 多语言支持
- [ ] 前端界面开发

### 长期（3 个月）
- [ ] 自定义数字人形象
- [ ] 情感分析和表达
- [ ] 多模态融合（视觉理解）
- [ ] 分布式部署
