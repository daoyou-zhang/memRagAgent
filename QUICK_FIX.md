# ⚡ 快速修复指南

## 🔴 当前问题

WebSocket 不工作 - 404 错误

## ✅ 快速修复（3 步）

### 1. 停止服务

在运行 `python start.py` 的终端按 **Ctrl+C**

### 2. 安装依赖

```bash
pip install "uvicorn[standard]"
```

### 3. 重启服务

```bash
cd backend/agent_person
python fix_and_restart.py
```

## 🎉 完成！

现在访问前端：http://localhost:5174

应该可以正常连接和对话了！

---

## 📝 详细说明

查看 [FIX_WEBSOCKET.md](./FIX_WEBSOCKET.md) 了解更多。
