# Agent Person 开发文档

## 开发环境设置

### 1. 安装依赖

```bash
cd backend
pip install -r agent_person/requirements.txt
```

### 2. 配置环境变量

复制 `.env` 文件并填写必要的配置：

```bash
cd agent_person
cp .env.example .env
# 编辑 .env 文件
```

### 3. 启动依赖服务

Agent Person 依赖以下服务：

```bash
# 1. 启动 Memory 服务（端口 5000）
cd backend/memory
python app.py

# 2. 启动 Daoyou Agent（端口 8000）
cd backend
uvicorn daoyou_agent.app:app --reload
```

### 4. 启动 Agent Person

```bash
cd backend
python -m agent_person.app
```

或使用启动脚本：

```bash
# Linux/Mac
./agent_person/start.sh

# Windows
.\agent_person\start.ps1
```

## 开发指南

### 添加新的 API 端点

1. 在 `api/` 目录创建新的路由文件
2. 定义路由和处理函数
3. 在 `app.py` 中注册路由

示例：

```python
# api/new_feature.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/test")
async def test():
    return {"message": "test"}

# app.py
from .api import new_feature
app.include_router(new_feature.router, prefix="/api/v1/new", tags=["new"])
```

### 添加新的服务

1. 在 `services/` 目录创建服务文件
2. 实现服务类和单例获取函数
3. 在 `services/__init__.py` 中导出

示例：

```python
# services/new_service.py
class NewService:
    def __init__(self):
        pass
    
    async def do_something(self):
        pass

_instance = None

def get_new_service() -> NewService:
    global _instance
    if _instance is None:
        _instance = NewService()
    return _instance
```

### 添加新的数据模型

1. 在 `models/` 目录创建模型文件
2. 使用 Pydantic 定义模型
3. 在 `models/__init__.py` 中导出

示例：

```python
# models/new_model.py
from pydantic import BaseModel, Field

class NewModel(BaseModel):
    field1: str = Field(..., description="字段1")
    field2: int = Field(0, description="字段2")
```

## 阿里云 API 集成

### 1. DashScope ASR（语音识别）

参考文档：https://help.aliyun.com/zh/dashscope/

```python
# 示例代码（需要根据实际文档调整）
import dashscope

dashscope.api_key = "your-api-key"

response = dashscope.audio.asr(
    model="qwen3-asr-flash",
    audio_url="https://example.com/audio.wav"
)
```

### 2. NLS TTS（语音合成）

参考文档：https://help.aliyun.com/zh/nls/

```python
# 示例代码（需要根据实际文档调整）
from aliyunsdkcore.client import AcsClient
from aliyunsdknls_cloud_meta.request.v20180518 import RunPreTrainServiceRequest

client = AcsClient(
    access_key_id="your-key-id",
    access_key_secret="your-key-secret",
    region_id="cn-shanghai"
)

request = RunPreTrainServiceRequest.RunPreTrainServiceRequest()
request.set_ServiceName("tts")
request.set_Text("你好")
request.set_Voice("xiaoyun")

response = client.do_action_with_exception(request)
```

### 3. DashScope 数字人

参考文档：https://help.aliyun.com/zh/dashscope/

```python
# 示例代码（需要根据实际文档调整）
import dashscope

response = dashscope.digital_human.generate(
    model="default",
    text="你好，我是数字人",
    voice="xiaoyun",
    background="office"
)
```

## 测试

### 单元测试

```bash
pytest tests/
```

### API 测试

使用 Swagger UI：http://localhost:8001/docs

或使用 curl：

```bash
# 文本聊天
curl -X POST http://localhost:8001/api/v1/chat/text \
  -H "Content-Type: application/json" \
  -d '{"input": "你好", "user_id": "test"}'

# 语音识别
curl -X POST http://localhost:8001/api/v1/voice/asr \
  -F "audio=@test.wav"

# 语音合成
curl -X POST "http://localhost:8001/api/v1/voice/tts?text=你好" \
  --output output.mp3
```

### WebSocket 测试

使用 JavaScript：

```javascript
const ws = new WebSocket('ws://localhost:8001/api/v1/chat/ws');

ws.onopen = () => {
    ws.send(JSON.stringify({
        type: 'text',
        user_id: 'test',
        input: '你好'
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data);
};
```

## 调试技巧

### 1. 启用详细日志

在 `.env` 中设置：

```env
LOG_LEVEL=DEBUG
```

### 2. 使用 loguru

```python
from loguru import logger

logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")
```

### 3. FastAPI 调试模式

```python
# app.py
if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8001,
        reload=True,  # 自动重载
        log_level="debug"  # 详细日志
    )
```

## 性能优化

### 1. 异步处理

所有 I/O 操作使用 async/await：

```python
async def process():
    result = await some_async_function()
    return result
```

### 2. 连接池

复用 HTTP 客户端：

```python
# 使用单例模式
_client = None

def get_client():
    global _client
    if _client is None:
        _client = httpx.AsyncClient()
    return _client
```

### 3. 缓存

对频繁访问的数据使用缓存：

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_config(key: str):
    return load_config(key)
```

## 常见问题

### Q: 阿里云 API 调用失败

A: 检查以下几点：
1. API Key 是否正确
2. 账户余额是否充足
3. API 配额是否用完
4. 网络连接是否正常

### Q: WebSocket 连接断开

A: 可能原因：
1. 网络不稳定
2. 超时未发送心跳
3. 服务器重启

解决方法：实现自动重连机制

### Q: 音视频文件太大

A: 优化方案：
1. 压缩音频（降低采样率、比特率）
2. 使用流式传输
3. 分片上传
4. 使用 CDN

## 部署

### Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "-m", "uvicorn", "agent_person.app:app", "--host", "0.0.0.0", "--port", "8001"]
```

### 生产环境配置

```bash
# 使用 gunicorn + uvicorn workers
gunicorn agent_person.app:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8001
```

## 贡献代码

1. Fork 项目
2. 创建特性分支：`git checkout -b feature/new-feature`
3. 提交代码：`git commit -am 'Add new feature'`
4. 推送分支：`git push origin feature/new-feature`
5. 创建 Pull Request

## 代码规范

- 使用 Python 3.11+
- 遵循 PEP 8
- 使用类型注解
- 编写文档字符串
- 添加单元测试
