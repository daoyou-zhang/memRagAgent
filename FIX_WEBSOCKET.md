# 🔧 修复 WebSocket 问题

## 问题

```
WARNING: No supported WebSocket library detected
INFO: 127.0.0.1:xxx - "GET /api/v1/chat/ws HTTP/1.1" 404 Not Found
```

## 解决方案

### 方式一：使用修复脚本（推荐）

1. **停止当前服务**（按 Ctrl+C）

2. **运行修复脚本**：
```bash
cd backend/agent_person
python fix_and_restart.py
```

这个脚本会：
- ✅ 安装 `uvicorn[standard]`
- ✅ 确保 `websockets` 已安装
- ✅ 自动重启服务

### 方式二：手动修复

1. **停止当前服务**（按 Ctrl+C）

2. **安装完整的 uvicorn**：
```bash
pip install "uvicorn[standard]"
```

3. **重启服务**：
```bash
cd backend/agent_person
python start.py
```

### 方式三：使用 pip 安装所有依赖

```bash
cd backend/agent_person
pip install -r requirements.txt
python start.py
```

## 验证修复

启动后，你应该看到：

```
INFO: Started server process [xxx]
INFO: Waiting for application startup.
INFO: Application startup complete.
```

**不应该再看到** WebSocket 警告。

## 测试 WebSocket

### 使用浏览器控制台

打开 http://localhost:5174，按 F12 打开控制台，运行：

```javascript
const ws = new WebSocket('ws://localhost:8001/api/v1/chat/ws');

ws.onopen = () => {
    console.log('✅ WebSocket 连接成功');
    ws.send(JSON.stringify({
        type: 'text',
        user_id: 'test_user',
        input: '你好'
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('📨 收到消息:', data);
};

ws.onerror = (error) => {
    console.error('❌ WebSocket 错误:', error);
};
```

如果看到 `✅ WebSocket 连接成功`，说明修复成功！

## 前端连接

确保前端正确连接：

```typescript
// agentfront/src/pages/DigitalPersonPage.tsx
const { sendMessage, isConnected } = useWebSocket('ws://localhost:8001/api/v1/chat/ws', {
  // ...
});
```

## 常见问题

### Q: 还是看到 404 错误

**A:** 检查路由是否正确注册：

访问 http://localhost:8001/docs，查看是否有 `/api/v1/chat/ws` 端点。

### Q: WebSocket 连接后立即断开

**A:** 检查后端日志，可能是：
1. 认知大脑服务（daoyou_agent）未启动
2. 消息格式不正确
3. 权限问题

### Q: 前端显示"未连接"

**A:** 
1. 确保后端在 8001 端口运行
2. 检查浏览器控制台错误
3. 尝试手动测试 WebSocket（见上方）

## 下一步

修复完成后：

1. ✅ 后端 WebSocket 正常
2. ✅ 前端可以连接
3. 🎉 开始对话！

---

**需要帮助？** 查看完整日志或联系技术支持。
