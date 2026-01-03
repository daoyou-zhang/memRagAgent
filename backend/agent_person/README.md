# AI Agent Person - 智能人模块

3D 数字人实时交互系统，整合语音识别、语音合成、认知大脑和数字人渲染。

## 功能特性

### 核心能力
- **3D 数字人渲染** - 使用阿里云 DashScope 生成逼真的数字人视频
- **实时语音识别** - Qwen3-ASR-Flash 快速准确的语音转文字
- **语音合成** - 阿里云 NLS 多种音色的文字转语音
- **认知大脑** - 调用 daoyou_agent 提供智能对话能力
- **WebSocket 实时交互** - 支持双向实时通信

### 交互模式
1. **文本聊天** - 基础的文本对话
2. **语音聊天** - 语音输入 + 语音输出
3. **数字人聊天** - 完整的 3D 数字人视频交互
4. **WebSocket 实时** - 流式对话，适合实时场景

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    前端（待开发）                        │
│              3D 数字人渲染 + 实时音视频                  │
└────────────────────┬────────────────────────────────────┘
                     │ WebSocket / HTTP
                     ▼
┌─────────────────────────────────────────────────────────┐
│              agent_person (FastAPI :8001)               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Chat API │  │ Voice API│  │ DH API   │             │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘             │
│       │             │             │                     │
│  ┌────▼─────────────▼─────────────▼─────┐             │
│  │         Services Layer                │             │
│  │  - BrainClient (认知)                 │             │
│  │  - ASRService (语音识别)              │             │
│  │  - TTSService (语音合成)              │             │
│  │  - DigitalHumanService (数字人)       │             │
│  └───────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ daoyou_agent │ │ 阿里云 NLS   │ │ DashScope    │
│   :8000      │ │   TTS        │ │  ASR + 数字人│
└──────────────┘ └──────────────┘ └──────────────┘
```

## 快速开始

### 1. 环境配置

编辑 `backend/agent_person/.env`：

```env
# 认知大脑
BRAIN_BASE=http://localhost:8000
MEMRAG_PROJECT_ID=DAOYOUTEST

# 阿里云 NLS（TTS）
ALI_NLS_APPKEY=your_appkey
ALI_ACCESS_KEY_ID=your_access_key_id
ALI_ACCESS_KEY_SECRET=your_access_key_secret

# 阿里云 DashScope（ASR + 数字人）
DASHSCOPE_API_KEY=sk-xxx
DASHSCOPE_API_MODEL=qwen3-asr-flash
```

### 2. 安装依赖

```bash
cd backend
pip install fastapi uvicorn websockets httpx loguru python-dotenv pydantic
```

### 3. 启动服务

```bash
# 确保 daoyou_agent 已启动（端口 8000）
cd backend
python -m agent_person.app
```

服务将在 `http://localhost:8001` 启动。

### 4. 测试 API

#### 文本聊天
```bash
curl -X POST http://localhost:8001/api/v1/chat/text \
  -H "Content-Type: application/json" \
  -d '{
    "input": "你好，介绍一下你自己",
    "user_id": "test_user",
    "enable_voice": false,
    "enable_digital_human": false
  }'
```

#### 语音识别
```bash
curl -X POST http://localhost:8001/api/v1/voice/asr \
  -F "audio=@test.wav" \
  -F "format=wav"
```

#### 语音合成
```bash
curl -X POST "http://localhost:8001/api/v1/voice/tts?text=你好&voice=xiaoyun" \
  --output output.mp3
```

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## 目录结构

```
agent_person/
├── __init__.py
├── app.py                    # FastAPI 应用入口
├── .env                      # 环境配置
├── README.md                 # 本文档
├── api/                      # API 路由
│   ├── __init__.py
│   ├── chat.py              # 聊天接口（文本/语音/WebSocket）
│   ├── voice.py             # 语音接口（ASR/TTS）
│   └── digital_human.py     # 数字人接口
├── models/                   # 数据模型
│   ├── __init__.py
│   ├── chat.py              # 聊天相关模型
│   └── digital_human.py     # 数字人相关模型
└── services/                 # 服务层
    ├── __init__.py
    ├── brain_client.py      # 认知大脑客户端
    ├── asr_service.py       # 语音识别服务
    ├── tts_service.py       # 语音合成服务
    └── digital_human_service.py  # 数字人服务
```

## 开发状态

### 已完成 ✅
- [x] 项目结构搭建
- [x] FastAPI 应用框架
- [x] 数据模型定义
- [x] API 路由设计
- [x] 服务层接口定义
- [x] 认知大脑客户端（调用 daoyou_agent）
- [x] WebSocket 实时聊天框架

### 待实现 🚧
- [ ] 阿里云 NLS TTS 实际调用
- [ ] 阿里云 DashScope ASR 实际调用
- [ ] 阿里云 DashScope 数字人 API 集成
- [ ] 音频文件存储和管理
- [ ] 视频文件存储和管理
- [ ] 流式语音识别
- [ ] 流式语音合成
- [ ] 流式数字人视频生成
- [ ] 前端 3D 渲染界面
- [ ] 会话管理和持久化
- [ ] 性能监控和日志

### 待优化 🔧
- [ ] 错误处理和重试机制
- [ ] 音视频格式转换
- [ ] 缓存策略（减少 API 调用）
- [ ] 并发控制（限流）
- [ ] 安全认证（API Key）
- [ ] 多语言支持
- [ ] 表情和动作控制
- [ ] 背景场景切换

## 技术栈

- **Web 框架**: FastAPI
- **实时通信**: WebSocket
- **HTTP 客户端**: httpx
- **日志**: loguru
- **数据验证**: Pydantic
- **语音识别**: 阿里云 DashScope (Qwen3-ASR-Flash)
- **语音合成**: 阿里云 NLS
- **数字人**: 阿里云 DashScope
- **认知大脑**: daoyou_agent

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `AGENT_PERSON_PORT` | 服务端口 | 8001 |
| `BRAIN_BASE` | 认知大脑地址 | http://localhost:8000 |
| `MEMRAG_PROJECT_ID` | 项目 ID | DAOYOUTEST |
| `ALI_NLS_APPKEY` | 阿里云 NLS AppKey | - |
| `ALI_ACCESS_KEY_ID` | 阿里云 Access Key ID | - |
| `ALI_ACCESS_KEY_SECRET` | 阿里云 Access Key Secret | - |
| `ALI_NLS_VOICE` | 默认语音角色 | xiaoyun |
| `DASHSCOPE_API_KEY` | DashScope API Key | - |
| `DASHSCOPE_API_BASE` | DashScope API 地址 | https://dashscope.aliyuncs.com/api/v1 |
| `DASHSCOPE_API_MODEL` | ASR 模型 | qwen3-asr-flash |
| `DIGITAL_HUMAN_MODEL` | 数字人模型 ID | default |

## 使用场景

1. **虚拟客服** - 24/7 在线的 3D 数字人客服
2. **教育培训** - 互动式教学助手
3. **娱乐陪伴** - 虚拟伴侣、虚拟偶像
4. **企业展示** - 品牌形象代言人
5. **医疗咨询** - 健康咨询助手
6. **智能导览** - 博物馆、展览导览员

## 注意事项

1. **API 配额** - 阿里云服务有调用限制，注意配额管理
2. **音视频大小** - 大文件传输需要考虑带宽和存储
3. **实时性** - WebSocket 连接需要保持稳定
4. **版权** - 本地使用暂不考虑，商用需注意数字人形象版权
5. **隐私** - 语音数据需要安全处理

## 后续规划

### 短期（1-2 周）
- 完成阿里云 API 实际集成
- 实现音视频文件管理
- 开发基础前端界面

### 中期（1 个月）
- 流式处理优化
- 表情和动作控制
- 多语言支持
- 性能优化

### 长期（3 个月）
- 自定义数字人形象
- 高级表情识别
- 情感分析和表达
- 多模态融合（视觉理解）

## 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建特性分支
3. 提交代码
4. 发起 Pull Request

## 许可证

本项目仅供学习和研究使用。
