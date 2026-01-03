# AI Agent Person 完整指南

## 项目概览

AI Agent Person 是一个完整的 3D 智能人交互系统，包含：

- **后端服务** (`backend/agent_person/`) - FastAPI + WebSocket
- **前端界面** (`agentfront/`) - React + Three.js

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    用户浏览器                                │
│              http://localhost:5174                          │
│                                                             │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  3D 数字人渲染   │         │   聊天界面       │         │
│  │  (Three.js)      │         │   (Material-UI)  │         │
│  └────────┬─────────┘         └────────┬─────────┘         │
│           │                            │                    │
│           └────────────┬───────────────┘                    │
│                        │ WebSocket                          │
└────────────────────────┼────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              agent_person (FastAPI)                         │
│              http://localhost:8001                          │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Chat API │  │ Voice API│  │  DH API  │  │ WebSocket│   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │             │             │          │
│  ┌────▼─────────────▼─────────────▼─────────────▼─────┐   │
│  │              Services Layer                         │   │
│  │  - BrainClient (认知大脑)                           │   │
│  │  - ASRService (语音识别)                            │   │
│  │  - TTSService (语音合成)                            │   │
│  │  - DigitalHumanService (数字人视频)                 │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ daoyou_agent │ │ 阿里云 NLS   │ │ DashScope    │
│   :8000      │ │   TTS        │ │  ASR + 数字人│
└──────────────┘ └──────────────┘ └──────────────┘
```

## 快速启动

### 1. 启动后端服务

```bash
# 终端 1: Memory 服务
cd backend/memory
python app.py

# 终端 2: Daoyou Agent
cd backend
uvicorn daoyou_agent.app:app --reload

# 终端 3: Agent Person
cd backend
python -m agent_person.app
```

### 2. 启动前端

```bash
# 终端 4: 前端
cd agentfront
npm install
npm run dev
```

### 3. 访问

打开浏览器访问 `http://localhost:5174`

## 目录结构

```
memRagAgent/
├── backend/
│   ├── agent_person/              # AI 智能人后端
│   │   ├── api/                   # API 路由
│   │   │   ├── chat.py           # 聊天接口
│   │   │   ├── voice.py          # 语音接口
│   │   │   └── digital_human.py  # 数字人接口
│   │   ├── services/              # 服务层
│   │   │   ├── brain_client.py   # 认知大脑客户端
│   │   │   ├── asr_service.py    # 语音识别
│   │   │   ├── tts_service.py    # 语音合成
│   │   │   └── digital_human_service.py  # 数字人
│   │   ├── models/                # 数据模型
│   │   ├── app.py                 # FastAPI 应用
│   │   ├── .env                   # 环境配置
│   │   └── README.md              # 文档
│   ├── daoyou_agent/              # 认知大脑
│   └── memory/                    # 记忆服务
├── agentfront/                    # 3D 数字人前端
│   ├── src/
│   │   ├── components/
│   │   │   └── DigitalPersonCanvas.tsx  # 3D 渲染
│   │   ├── pages/
│   │   │   └── DigitalPersonPage.tsx    # 主页面
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts          # WebSocket Hook
│   │   └── App.tsx
│   ├── package.json
│   └── README.md
└── AGENT_PERSON_GUIDE.md          # 本文档
```

## 功能特性

### 已实现 ✅

- [x] FastAPI 后端框架
- [x] WebSocket 实时通信
- [x] 认知大脑集成（调用 daoyou_agent）
- [x] React + Three.js 前端
- [x] 3D 美女模型（简化版）
- [x] 实时对话界面
- [x] 流式回复显示
- [x] 说话动画效果
- [x] 呼吸动画效果
- [x] 眨眼动画效果
- [x] 视角控制（旋转、缩放）
- [x] 状态指示器
- [x] 消息历史记录

### 待实现 🚧

- [ ] 阿里云 NLS TTS 实际调用
- [ ] 阿里云 DashScope ASR 实际调用
- [ ] 阿里云 DashScope 数字人 API
- [ ] 真实 3D 模型（Ready Player Me）
- [ ] 语音识别功能
- [ ] 语音合成功能
- [ ] 音频播放
- [ ] 更多表情动画
- [ ] 手势动画
- [ ] 背景切换
- [ ] 移动端适配

## 配置说明

### 后端配置 (backend/agent_person/.env)

```env
# 服务端口
AGENT_PERSON_PORT=8001

# 认知大脑
BRAIN_BASE=http://localhost:8000
MEMRAG_PROJECT_ID=DAOYOUTEST

# 阿里云 NLS（TTS）
ALI_NLS_APPKEY=your_appkey
ALI_ACCESS_KEY_ID=your_key_id
ALI_ACCESS_KEY_SECRET=your_key_secret
ALI_NLS_VOICE=xiaoyun

# 阿里云 DashScope（ASR + 数字人）
DASHSCOPE_API_KEY=sk-xxx
DASHSCOPE_API_BASE=https://dashscope.aliyuncs.com/api/v1
DASHSCOPE_API_MODEL=qwen3-asr-flash
```

### 前端配置 (agentfront/.env)

```env
VITE_API_BASE_URL=http://localhost:8001
VITE_WS_URL=ws://localhost:8001/api/v1/chat/ws
VITE_DEBUG=true
```

## API 文档

### WebSocket 接口

**连接**: `ws://localhost:8001/api/v1/chat/ws`

**发送消息**:
```json
{
  "type": "text",
  "user_id": "user_001",
  "input": "你好"
}
```

**接收消息**:
```json
// 内容片段
{
  "type": "content",
  "data": { "text": "你好" }
}

// 完成信号
{
  "type": "done",
  "session_id": "xxx"
}
```

### HTTP 接口

#### 文本聊天
```bash
POST /api/v1/chat/text
Content-Type: application/json

{
  "input": "你好",
  "user_id": "user_001",
  "enable_voice": false,
  "enable_digital_human": false
}
```

#### 语音识别
```bash
POST /api/v1/voice/asr
Content-Type: multipart/form-data

audio: <file>
format: wav
```

#### 语音合成
```bash
POST /api/v1/voice/tts?text=你好&voice=xiaoyun
```

## 自定义开发

### 修改 3D 模型

编辑 `agentfront/src/components/DigitalPersonCanvas.tsx`：

```typescript
// 修改颜色
<meshStandardMaterial color="#ffd4b8" />  // 皮肤
<meshStandardMaterial color="#ffffff" />  // 衣服
<meshStandardMaterial color="#2c1810" />  // 头发

// 修改尺寸
<sphereGeometry args={[0.18, 32, 32]} />  // 头部大小
<cylinderGeometry args={[0.22, 0.32, 0.9, 32]} />  // 身体
```

### 使用真实模型

```typescript
import { useGLTF } from '@react-three/drei';

const Model = () => {
  const { scene } = useGLTF('/models/avatar.glb');
  return <primitive object={scene} scale={1.5} />;
};
```

推荐模型来源：
- **Ready Player Me**: https://readyplayer.me/
- **Mixamo**: https://www.mixamo.com/
- **Sketchfab**: https://sketchfab.com/

### 添加新动画

```typescript
useFrame((state) => {
  // 挥手动画
  if (isWaving) {
    armRef.current.rotation.z = Math.sin(state.clock.elapsedTime * 5) * 0.5;
  }
});
```

## 性能优化

### 前端优化

1. **降低几何体细分**
```typescript
<sphereGeometry args={[0.18, 16, 16]} />  // 从 32 降到 16
```

2. **使用 LOD（细节层次）**
```typescript
import { Lod } from '@react-three/drei';
```

3. **启用阴影优化**
```typescript
<Canvas shadows shadowMap={{ type: THREE.PCFSoftShadowMap }}>
```

### 后端优化

1. **连接池复用**
2. **异步处理**
3. **缓存策略**

## 部署

### 前端部署

```bash
cd agentfront
npm run build
# 将 dist/ 目录部署到静态服务器
```

### 后端部署

```bash
# 使用 gunicorn
gunicorn agent_person.app:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8001
```

### Docker 部署

```dockerfile
# 前端
FROM node:18 AS build
WORKDIR /app
COPY agentfront/ .
RUN npm install && npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html

# 后端
FROM python:3.11-slim
WORKDIR /app
COPY backend/agent_person/ .
RUN pip install -r requirements.txt
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
```

## 故障排查

### 问题：WebSocket 连接失败

**解决方案**:
1. 检查后端是否启动
2. 检查端口是否被占用
3. 检查防火墙设置

### 问题：3D 模型不显示

**解决方案**:
1. 检查浏览器是否支持 WebGL
2. 更新显卡驱动
3. 启用浏览器硬件加速

### 问题：性能卡顿

**解决方案**:
1. 降低几何体细分数
2. 减少光源数量
3. 禁用阴影
4. 使用更简单的材质

## 下一步计划

### 短期（1-2 周）
- 完成阿里云 API 集成
- 实现语音识别和合成
- 添加音频播放功能

### 中期（1 个月）
- 集成 Ready Player Me 真实模型
- 添加更多表情和动作
- 优化性能和用户体验

### 长期（3 个月）
- 支持自定义数字人形象
- 多模态交互（视觉理解）
- 情感分析和表达
- 移动端应用

## 参考资源

- **Three.js 文档**: https://threejs.org/docs/
- **React Three Fiber**: https://docs.pmnd.rs/react-three-fiber/
- **FastAPI 文档**: https://fastapi.tiangolo.com/
- **阿里云 DashScope**: https://help.aliyun.com/zh/dashscope/
- **阿里云 NLS**: https://help.aliyun.com/zh/nls/

## 许可证

本项目仅供学习和研究使用。
