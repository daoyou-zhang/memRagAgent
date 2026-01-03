# 🎭 AI Agent Person - 3D 智能人系统

> 完美漂亮的 3D 美女数字人，拥有完整身体，支持实时语音交互

## ✨ 特性亮点

- 👩 **完美 3D 美女** - 拥有完整身体的漂亮数字人模型
- 💬 **实时对话** - WebSocket 流式交互，即时响应
- 🎨 **精美界面** - 简洁渐变背景，科技感十足
- 🎭 **生动动画** - 呼吸、说话、眨眼等自然动作
- 🧠 **智能大脑** - 集成 daoyou_agent 认知能力
- 🎤 **语音支持** - ASR 识别 + TTS 合成（待实现）
- 🌐 **独立前端** - 与原有 frontend 完全分离

## 📦 项目结构

```
memRagAgent/
├── backend/agent_person/     # 后端服务（FastAPI + WebSocket）
│   ├── api/                  # API 路由
│   ├── services/             # 服务层（ASR/TTS/数字人/大脑）
│   ├── models/               # 数据模型
│   └── app.py                # 应用入口
│
├── agentfront/               # 前端界面（React + Three.js）
│   ├── src/
│   │   ├── components/       # 3D 渲染组件
│   │   ├── pages/            # 页面组件
│   │   └── hooks/            # 自定义 Hooks
│   └── package.json
│
└── AGENT_PERSON_GUIDE.md     # 完整指南
```

## 🚀 快速启动

### 前置要求

- Python 3.11+
- Node.js 18+
- 现代浏览器（支持 WebGL）

### 1. 启动后端

```bash
# 终端 1: Memory 服务
cd backend/memory
python app.py

# 终端 2: Daoyou Agent（认知大脑）
cd backend
uvicorn daoyou_agent.app:app --reload

# 终端 3: Agent Person
cd backend
python -m agent_person.app
```

### 2. 启动前端

```bash
# 终端 4
cd agentfront
npm install
npm run dev
```

### 3. 访问

打开浏览器访问 `http://localhost:5174`

## 🎯 核心功能

### 已实现 ✅

- [x] 3D 美女数字人模型（完整身体）
- [x] 实时 WebSocket 通信
- [x] 流式对话显示
- [x] 说话动画（头部晃动、嘴巴张合）
- [x] 呼吸动画（轻微浮动）
- [x] 眨眼动画
- [x] 视角控制（旋转、缩放）
- [x] 消息历史记录
- [x] 状态指示器
- [x] 认知大脑集成

### 待实现 🚧

- [ ] 阿里云 NLS TTS（语音合成）
- [ ] 阿里云 DashScope ASR（语音识别）
- [ ] 阿里云 DashScope 数字人视频
- [ ] Ready Player Me 真实模型
- [ ] 音频播放功能
- [ ] 更多表情动画
- [ ] 手势动画
- [ ] 背景场景切换

## 🎨 界面预览

### 左侧：3D 数字人
- 完美漂亮的女性形象
- 完整身体（头、身体、手臂、腿）
- 长发造型
- 优雅连衣裙
- 简洁渐变背景

### 右侧：聊天界面
- 实时消息流
- 状态指示（连接、说话）
- 语音控制按钮
- 消息历史记录
- 数字人信息卡片

## 🛠️ 技术栈

### 后端
- **FastAPI** - 高性能 Web 框架
- **WebSocket** - 实时通信
- **httpx** - 异步 HTTP 客户端
- **loguru** - 结构化日志

### 前端
- **React 18** - UI 框架
- **TypeScript** - 类型安全
- **Three.js** - 3D 渲染引擎
- **React Three Fiber** - React 的 Three.js 渲染器
- **@react-three/drei** - Three.js 辅助工具
- **Material-UI** - UI 组件库
- **Vite** - 构建工具

### 外部服务
- **daoyou_agent** - 认知大脑（意图理解、上下文聚合、LLM 生成）
- **阿里云 DashScope** - ASR + 数字人
- **阿里云 NLS** - TTS

## 📝 配置说明

### 后端配置

编辑 `backend/agent_person/.env`：

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

# 阿里云 DashScope（ASR + 数字人）
DASHSCOPE_API_KEY=sk-xxx
DASHSCOPE_API_MODEL=qwen3-asr-flash
```

### 前端配置

编辑 `agentfront/.env`：

```env
VITE_API_BASE_URL=http://localhost:8001
VITE_WS_URL=ws://localhost:8001/api/v1/chat/ws
```

## 🎭 自定义数字人

### 修改外观

编辑 `agentfront/src/components/DigitalPersonCanvas.tsx`：

```typescript
// 皮肤颜色
<meshStandardMaterial color="#ffd4b8" />

// 服装颜色
<meshStandardMaterial color="#ffffff" />

// 头发颜色
<meshStandardMaterial color="#2c1810" />
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
- **Ready Player Me**: https://readyplayer.me/ （自定义虚拟形象）
- **Mixamo**: https://www.mixamo.com/ （免费 3D 角色和动画）
- **Sketchfab**: https://sketchfab.com/ （3D 模型市场）

## 📚 文档

- [AGENT_PERSON_GUIDE.md](./AGENT_PERSON_GUIDE.md) - 完整开发指南
- [agentfront/README.md](./agentfront/README.md) - 前端详细文档
- [agentfront/QUICKSTART.md](./agentfront/QUICKSTART.md) - 快速开始
- [backend/agent_person/README.md](./backend/agent_person/README.md) - 后端文档
- [backend/agent_person/DEVELOPMENT.md](./backend/agent_person/DEVELOPMENT.md) - 开发文档
- [backend/agent_person/ARCHITECTURE.md](./backend/agent_person/ARCHITECTURE.md) - 架构设计

## 🔧 故障排查

### WebSocket 连接失败

1. 检查后端是否启动：`http://localhost:8001/health`
2. 检查端口是否被占用
3. 检查防火墙设置

### 3D 模型不显示

1. 检查浏览器是否支持 WebGL：https://get.webgl.org/
2. 更新显卡驱动
3. 启用浏览器硬件加速

### 性能卡顿

1. 降低几何体细分数
2. 减少光源数量
3. 禁用阴影
4. 使用更简单的材质

## 🎯 使用场景

- 🏢 **虚拟客服** - 24/7 在线的 3D 数字人客服
- 📚 **教育培训** - 互动式教学助手
- 🎮 **娱乐陪伴** - 虚拟伴侣、虚拟偶像
- 🏪 **企业展示** - 品牌形象代言人
- 🏥 **医疗咨询** - 健康咨询助手
- 🏛️ **智能导览** - 博物馆、展览导览员

## 🗺️ 开发路线图

### 短期（1-2 周）
- [ ] 完成阿里云 API 实际集成
- [ ] 实现语音识别和合成
- [ ] 添加音频播放功能
- [ ] 优化动画效果

### 中期（1 个月）
- [ ] 集成 Ready Player Me 真实模型
- [ ] 添加更多表情和动作
- [ ] 支持多个数字人角色
- [ ] 移动端适配

### 长期（3 个月）
- [ ] 自定义数字人形象
- [ ] 情感分析和表达
- [ ] 多模态交互（视觉理解）
- [ ] 分布式部署

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交代码：`git commit -m 'Add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 创建 Pull Request

## 📄 许可证

本项目仅供学习和研究使用。

## 🙏 致谢

- Three.js 社区
- React Three Fiber 团队
- FastAPI 团队
- 阿里云团队

---

**开始体验完美的 3D 智能人吧！** 🎉
