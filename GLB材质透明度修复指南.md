# GLB 材质透明度修复指南

## 问题描述

从 FBX 转换到 GLB 时，`fbx2gltf` 工具会丢弃 `TransparentColor` 纹理，导致：
- 头发材质不透明，看起来像实心块
- 睫毛材质不透明
- 衣服边缘没有透明效果

转换时的警告：
```
Warning: Mat [Std_Eyelash]: Can't handle texture for TransparentColor; discarding.
Warning: Mat [Hair_f_Mat]: Can't handle texture for TransparentColor; discarding.
Warning: Mat [Back_f_Mat]: Can't handle texture for TransparentColor; discarding.
```

## 已实施的修复方案

### 1. 前端材质修复（已完成）

在 `BeautifulAvatarModel.tsx` 中，我们添加了智能材质检测和修复：

```typescript
// 检测需要透明度的材质（头发、睫毛等）
const needsTransparency = 
  matName.includes('hair') || 
  matName.includes('eyelash') || 
  name.includes('hair') || 
  name.includes('eyelash');

// 检测需要双面渲染的材质（头发、衣服等）
const needsDoubleSide = 
  needsTransparency ||
  matName.includes('cloth') ||
  matName.includes('dress') ||
  matName.includes('skirt') ||
  name.includes('cloth') ||
  name.includes('dress');

// 设置双面渲染
if (needsDoubleSide) {
  mat.side = THREE.DoubleSide;
}

// 设置透明度
if (needsTransparency) {
  mat.transparent = true;
  mat.alphaTest = 0.5; // 使用 alpha 测试而不是混合
  mat.depthWrite = true; // 保持深度写入
  mat.alphaMap = mat.map; // 使用颜色贴图的 alpha 通道
}
```

### 2. 修复效果

- ✅ 自动检测头发、睫毛材质
- ✅ 启用双面渲染（避免背面消失）
- ✅ 启用透明度和 alpha 测试
- ✅ 使用颜色贴图的 alpha 通道作为透明度
- ✅ 自动检测衣服材质并启用双面渲染

## 更好的解决方案：使用 Blender 重新导出

如果前端修复效果不理想，建议使用 Blender 重新导出 GLB：

### 步骤 1: 安装 Blender

下载地址：https://www.blender.org/download/

### 步骤 2: 导入 FBX

1. 打开 Blender
2. File → Import → FBX (.fbx)
3. 选择你的 FBX 文件

### 步骤 3: 修复材质

1. 切换到 Shading 工作区
2. 选择需要透明的物体（头发、睫毛等）
3. 在材质节点编辑器中：
   - 找到 Base Color 贴图节点
   - 将 Alpha 输出连接到 Principled BSDF 的 Alpha 输入
   - 在材质属性中，设置 Blend Mode 为 "Alpha Clip"
   - 设置 Clip Threshold 为 0.5

### 步骤 4: 导出 GLB

1. File → Export → glTF 2.0 (.glb/.gltf)
2. 在导出选项中：
   - Format: glTF Binary (.glb)
   - Include: Selected Objects（或 Visible Objects）
   - Transform: +Y Up
   - Geometry: Apply Modifiers ✓
   - Materials: Export ✓
   - Compression: 可选启用 Draco 压缩
3. 点击 Export glTF 2.0

### 步骤 5: 替换模型

将导出的 GLB 文件替换到 `agentfront/public/models/avatar.glb`

## 测试材质效果

启动前端后，打开浏览器控制台，查看材质日志：

```
🎨 材质 Hair_f_Mat {
  transparent: true,
  alphaTest: 0.5,
  side: 'DoubleSide',
  hasAlphaMap: true
}
```

如果看到以上信息，说明材质修复成功。

## 常见问题

### Q: 模型加载后一瞬间是完整的，之后就不完整了？

A: 这是因为材质在初始化时使用了错误的透明度设置。我们的修复代码会在模型加载后立即修正这个问题。

### Q: 头发还是看起来很奇怪？

A: 可能需要调整 `alphaTest` 值：
- 值太低（如 0.1）：会显示太多半透明像素
- 值太高（如 0.9）：会裁剪掉太多像素
- 推荐值：0.5

### Q: 衣服边缘有锯齿？

A: 这是 alpha 测试的正常现象。可以尝试：
1. 使用 `transparent = true` 和 `alphaTest = 0` 启用 alpha 混合
2. 但这可能导致渲染顺序问题

### Q: 模型太大或太小？

A: 代码会自动调整模型大小，使其高度约为 2 个单位。如需调整，修改 `targetHeight` 变量。

## 下一步优化

1. **表情控制**：参考 `agentfront/表情控制示例.md`
2. **动画优化**：当前是顺次循环播放所有动画，可以根据情绪选择特定动画
3. **光照优化**：调整场景光照以获得更好的视觉效果
4. **性能优化**：如果模型太大，可以使用 Draco 压缩

## 相关文件

- `agentfront/src/components/BeautifulAvatarModel.tsx` - 模型加载和材质修复
- `agentfront/src/components/DigitalPersonCanvas.tsx` - 3D 场景设置
- `agentfront/public/models/avatar.glb` - 模型文件位置
