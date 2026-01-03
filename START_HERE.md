# 🚀 快速启动 - AI 3D 数字人

## ✅ 后端已成功启动！

服务正在运行：
- 🌐 **服务地址**: http://localhost:8001
- 📚 **API 文档**: http://localhost:8001/docs
- 💚 **健康检查**: http://localhost:8001/health
- 🔌 **WebSocket**: ws://localhost:8001/api/v1/chat/ws

## 📦 启动前端

打开**新的终端**，运行：

```bash
cd agentfront
npm install
npm run dev
```

前端将在 `http://localhost:5174` 启动。

## 🎉 开始使用

1. 打开浏览器访问 `http://localhost:5174`
2. 你将看到完美漂亮的 3D 美女数字人
3. 在右侧输入框输入消息，开始对话！

## 📖 详细文档

- [README_AGENT_PERSON.md](./README_AGENT_PERSON.md) - 项目总览
- [AGENT_PERSON_GUIDE.md](./AGENT_PERSON_GUIDE.md) - 完整指南
- [agentfront/QUICKSTART.md](./agentfront/QUICKSTART.md) - 前端快速开始

## 🛠️ 其他启动方式

### 方式一：使用 start.py（推荐）
```bash
cd backend/agent_person
python start.py
```

### 方式二：使用 PowerShell 脚本
```powershell
cd backend\agent_person
.\start.ps1
```

### 方式三：从 backend 目录启动
```bash
cd backend
python -m agent_person.app
```

---

**祝你使用愉快！** 🎭✨
