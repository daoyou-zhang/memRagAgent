# 🎨 GLB 模型使用指南

## ✅ 已修复错误

刚才的错误 "Div is not part of the THREE namespace" 已经修复！

原因：在 Three.js Canvas 里面不能使用普通的 HTML 标签（如 `<div>`）

---

## 📁 放置 GLB 模型

### 1. 文件位置

```
agentfront/public/models/avatar.glb
```

**完整路径**：
```
D:\workspace\memRagAgent\agentfront\public\models\avatar.glb
```

### 2. 文件要求

- ✅ **文件名**：必须是 `avatar.glb`（小写）
- ✅ **格式**：GLB 格式（不是 GLTF、FBX 等）
- ✅ **大小**：建议 5-20 MB
- ✅ **骨骼**：最好带骨骼（Rigged）

---

## 🚀 使用步骤

### 步骤 1：放置文件

```bash
# 将你的 GLB 文件重命名为 avatar.glb
# 复制到：
agentfront\public\models\avatar.glb
```

### 步骤 2：刷新浏览器

```
http://localhost:5175
```

按 `F5` 刷新页面

### 步骤 3：查看效果

- 模型会自动加载
- 等待 3-5 秒
- 看到你的 3D 美女！

---

## 🔍 验证模型加载

### 浏览器控制台（F12）

**成功加载**：
```
✅ 找到真实模型，使用 BeautifulAvatarModel
✅ 模型加载成功！
📏 模型尺寸: 1.80 x 1.75 x 0.45
🔍 缩放比例: 1.14
```

**使用回退模型**：
```
ℹ️  未找到真实模型，使用程序化模型
```

**加载失败**：
```
⚠️ 真实3D模型渲染/加载错误: ...
✅ 触发兜底策略：切换为程序化模型
```

---

## 🎯 智能加载系统

### 工作流程

```
1. 检查文件是否存在
   ↓
2. 验证文件是否可用
   ↓
3. 尝试加载 GLB 模型
   ↓
4. 如果成功 → 显示真实模型
   如果失败 → 自动回退到程序化模型
```

### 回退机制

- ✅ 文件不存在 → 使用程序化模型
- ✅ 文件损坏 → 使用程序化模型
- ✅ 加载超时 → 使用程序化模型
- ✅ 渲染错误 → 使用程序化模型

**无论如何，界面都能正常显示！**

---

## 🎨 模型调整

### 如果模型太大或太小

编辑 `agentfront/src/components/BeautifulAvatarModel.tsx`：

```typescript
// 找到这一行
const targetHeight = 2.0;

// 修改为：
const targetHeight = 1.5;  // 更小
// 或
const targetHeight = 2.5;  // 更大
```

### 如果模型位置不对

```typescript
// 找到这一行
position={[0, -1, 0]}

// 修改为：
position={[0, -0.5, 0]}  // 向上移动
// 或
position={[0, -1.5, 0]}  // 向下移动
```

### 如果模型旋转不对

```typescript
// 找到这一行
rotation={[0, 0, 0]}

// 修改为：
rotation={[0, Math.PI, 0]}  // 旋转 180 度
// 或
rotation={[0, Math.PI / 2, 0]}  // 旋转 90 度
```

---

## 🐛 常见问题

### 问题 1：模型不显示

**检查**：
1. 文件名是否为 `avatar.glb`
2. 文件是否在 `public/models/` 文件夹
3. 浏览器控制台是否有错误
4. 刷新浏览器（F5）

**解决**：
- 确认文件路径正确
- 确认文件格式是 GLB
- 查看控制台错误信息

### 问题 2：模型显示但很奇怪

**可能原因**：
- 模型缩放不对
- 模型位置不对
- 模型旋转不对

**解决**：
- 按照上面的"模型调整"部分修改参数

### 问题 3：模型加载很慢

**原因**：
- 文件太大（超过 20 MB）

**解决**：
- 使用 Blender 优化模型
- 减少多边形数量
- 压缩纹理

### 问题 4：模型没有动画

**原因**：
- 模型本身没有动画
- 或者没有骨骼

**解决**：
- 使用带骨骼的模型（Rigged）
- 或者使用 VRoid Studio 创建的模型（自带动画）

---

## 📊 文件结构

```
agentfront/
├── public/
│   └── models/
│       ├── README.md          # 说明文档
│       └── avatar.glb         # ← 你的模型
│
└── src/
    └── components/
        ├── ModelWithFallback.tsx      # 智能加载器
        ├── BeautifulAvatarModel.tsx   # 真实模型组件
        └── ImprovedAvatarModel.tsx    # 程序化模型（回退）
```

---

## 🎭 支持的模型来源

### 1. VRoid Studio（推荐）
- 导出 VRM 格式
- 转换为 GLB：https://vrm.dev/vrm_converter/
- 自带 52 种表情

### 2. Ready Player Me
- 直接导出 GLB
- 写实风格

### 3. Sketchfab
- 搜索免费模型
- 下载 GLB 格式

### 4. Mixamo
- 下载 FBX
- 转换为 GLB

### 5. AI 生成
- Stable Diffusion + TripoSR
- Meshy.ai

---

## 🎉 完成

1. ✅ 错误已修复
2. ✅ 放置 GLB 文件到 `public/models/avatar.glb`
3. ✅ 刷新浏览器
4. ✅ 看到你的 3D 美女！

**如果有任何问题，查看浏览器控制台（F12）的错误信息！**

---

## 💡 提示

- 第一次加载可能需要几秒钟
- 大文件加载时间更长
- 如果模型不显示，系统会自动使用程序化模型
- 可以随时更换模型，只需替换 `avatar.glb` 文件

**享受你的 3D 数字人吧！** 🎨✨
