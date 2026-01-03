# 快速开始 - AgentFront

## 一键启动

### 1. 安装依赖

```bash
cd agentfront
npm install
```

### 2. 启动后端服务

在另一个终端：

```bash
cd backend
python -m agent_person.app
```

后端将在 `http://localhost:8001` 启动。

### 3. 启动前端

```bash
npm run dev
```

前端将在 `http://localhost:5174` 启动。

### 4. 打开浏览器

访问 `http://localhost:5174`，你将看到：

- 左侧：完美漂亮的 3D 美女数字人
- 右侧：实时聊天界面

## 使用说明

### 基础对话

1. 在右侧输入框输入消息
2. 按 Enter 发送（Shift+Enter 换行）
3. 数字人会实时回复，并有说话动画

### 视角控制

- **旋转**：鼠标左键拖拽
- **缩放**：鼠标滚轮
- **重置**：刷新页面

### 功能按钮

- 🎤 **语音输入**：点击麦克风图标（待实现）
- 🔊 **静音**：点击音量图标（待实现）
- 🔄 **重置对话**：点击刷新图标

## 常见问题

### Q: 页面空白或加载失败

**A:** 检查以下几点：

1. 确保 Node.js 版本 >= 16
2. 清除缓存：`npm cache clean --force`
3. 重新安装：`rm -rf node_modules && npm install`
4. 检查浏览器控制台错误

### Q: WebSocket 连接失败

**A:** 确保：

1. 后端服务已启动（`python -m agent_person.app`）
2. 端口 8001 未被占用
3. 防火墙未阻止连接

### Q: 3D 模型不显示

**A:** 检查：

1. 浏览器是否支持 WebGL（访问 https://get.webgl.org/）
2. 显卡驱动是否最新
3. 浏览器硬件加速是否启用

### Q: 性能卡顿

**A:** 优化方案：

1. 关闭其他占用 GPU 的程序
2. 降低浏览器缩放比例
3. 使用性能更好的浏览器（Chrome/Edge）

## 开发模式

### 热重载

修改代码后，页面会自动刷新。

### 调试

打开浏览器开发者工具（F12）：

- **Console**：查看日志
- **Network**：查看 WebSocket 连接
- **Performance**：分析性能

### 环境变量

创建 `.env` 文件：

```env
VITE_API_BASE_URL=http://localhost:8001
VITE_WS_URL=ws://localhost:8001/api/v1/chat/ws
VITE_DEBUG=true
```

## 生产构建

```bash
npm run build
```

构建产物在 `dist/` 目录，可以部署到任何静态服务器。

## 下一步

- 查看 [README.md](./README.md) 了解详细功能
- 查看 [src/components/DigitalPersonCanvas.tsx](./src/components/DigitalPersonCanvas.tsx) 自定义 3D 模型
- 查看 [src/pages/DigitalPersonPage.tsx](./src/pages/DigitalPersonPage.tsx) 自定义界面

## 技术支持

遇到问题？

1. 查看 [README.md](./README.md) 的常见问题部分
2. 检查浏览器控制台错误信息
3. 查看后端日志
