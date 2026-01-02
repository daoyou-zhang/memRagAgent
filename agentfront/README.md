# AgentFront - 3D 数字人前端

完美漂亮的 3D 美女数字人交互界面，基于 React + Three.js 构建。

## 特性

- 🎨 **精美 3D 模型** - 完整身体的美女数字人
- 💬 **实时对话** - WebSocket 流式交互
- 🎤 **语音支持** - 语音识别和合成（待实现）
- 🌈 **渐变背景** - 简洁优雅的视觉效果
- 📱 **响应式设计** - 适配不同屏幕尺寸
- ⚡ **高性能渲染** - 基于 React Three Fiber

## 技术栈

- **React 18** - UI 框架
- **TypeScript** - 类型安全
- **Three.js** - 3D 渲染引擎
- **React Three Fiber** - React 的 Three.js 渲染器
- **@react-three/drei** - Three.js 辅助工具
- **Material-UI** - UI 组件库
- **Vite** - 构建工具

## 快速开始

### 1. 安装依赖

```bash
cd agentfront
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

服务将在 `http://localhost:5174` 启动。

### 3. 确保后端服务运行

```bash
# 在另一个终端
cd backend
python -m agent_person.app
```

后端服务应该在 `http://localhost:8001` 运行。

## 项目结构

```
agentfront/
├── src/
│   ├── components/
│   │   └── DigitalPersonCanvas.tsx  # 3D 渲染组件
│   ├── pages/
│   │   └── DigitalPersonPage.tsx    # 主页面
│   ├── hooks/
│   │   └── useWebSocket.ts          # WebSocket Hook
│   ├── App.tsx                      # 应用入口
│   ├── main.tsx                     # React 入口
│   └── index.css                    # 全局样式
├── index.html                       # HTML 模板
├── package.json                     # 依赖配置
├── tsconfig.json                    # TypeScript 配置
└── vite.config.ts                   # Vite 配置
```

## 功能说明

### 3D 数字人

- **外观**：完美漂亮的女性形象，拥有完整身体
- **动画**：
  - 呼吸效果（轻微上下浮动）
  - 说话时头部晃动
  - 眨眼动画
- **交互**：
  - 鼠标拖拽旋转视角
  - 滚轮缩放
  - 自动跟随对话状态

### 聊天界面

- **实时对话**：WebSocket 流式接收回复
- **消息历史**：保存对话记录
- **状态指示**：连接状态、说话状态
- **快捷操作**：
  - Enter 发送消息
  - Shift+Enter 换行
  - 语音输入（待实现）
  - 静音控制（待实现）

### 视觉效果

- **渐变背景**：深色系渐变，营造科技感
- **光影效果**：多光源照明，增强立体感
- **反射地板**：金属质感地板，提升真实感
- **信息卡片**：半透明毛玻璃效果

## 自定义配置

### 修改数字人外观

编辑 `src/components/DigitalPersonCanvas.tsx`：

```typescript
// 修改皮肤颜色
<meshStandardMaterial color="#ffd4b8" />

// 修改服装颜色
<meshStandardMaterial color="#ffffff" />

// 修改头发颜色
<meshStandardMaterial color="#2c1810" />
```

### 使用真实 3D 模型

替换简化几何体为 GLB/GLTF 模型：

```typescript
import { useGLTF } from '@react-three/drei';

const Model = () => {
  const { scene } = useGLTF('/models/avatar.glb');
  return <primitive object={scene} />;
};
```

推荐模型来源：
- [Ready Player Me](https://readyplayer.me/) - 自定义虚拟形象
- [Mixamo](https://www.mixamo.com/) - 免费 3D 角色和动画
- [Sketchfab](https://sketchfab.com/) - 3D 模型市场

### 修改后端地址

编辑 `vite.config.ts`：

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://your-backend-url:8001',
      changeOrigin: true,
    }
  }
}
```

或直接修改 WebSocket URL：

```typescript
// src/pages/DigitalPersonPage.tsx
const { sendMessage, isConnected } = useWebSocket('ws://your-backend-url:8001/api/v1/chat/ws', {
  // ...
});
```

## 性能优化

### 1. 减少多边形数量

```typescript
// 降低几何体细分
<sphereGeometry args={[0.18, 16, 16]} /> // 从 32 降到 16
```

### 2. 使用 LOD（细节层次）

```typescript
import { Lod } from '@react-three/drei';

<Lod distances={[0, 10, 20]}>
  <HighDetailModel />
  <MediumDetailModel />
  <LowDetailModel />
</Lod>
```

### 3. 启用阴影优化

```typescript
<Canvas shadows shadowMap={{ type: THREE.PCFSoftShadowMap }}>
```

## 常见问题

### Q: 3D 模型不显示

A: 检查以下几点：
1. 浏览器是否支持 WebGL
2. 控制台是否有错误信息
3. 模型路径是否正确

### Q: WebSocket 连接失败

A: 确保：
1. 后端服务已启动（端口 8001）
2. 防火墙未阻止连接
3. WebSocket URL 正确

### Q: 性能卡顿

A: 优化方案：
1. 降低几何体细分数
2. 减少光源数量
3. 禁用阴影
4. 使用更简单的材质

## 部署

### 构建生产版本

```bash
npm run build
```

构建产物在 `dist/` 目录。

### 部署到静态服务器

```bash
# 使用 Nginx
cp -r dist/* /var/www/html/

# 使用 Vercel
vercel deploy

# 使用 Netlify
netlify deploy --prod --dir=dist
```

## 后续计划

- [ ] 集成 Ready Player Me 真实模型
- [ ] 实现语音识别功能
- [ ] 实现语音合成功能
- [ ] 添加更多表情动画
- [ ] 支持手势控制
- [ ] 添加背景切换
- [ ] 支持多个数字人角色
- [ ] 移动端适配优化

## 许可证

本项目仅供学习和研究使用。
