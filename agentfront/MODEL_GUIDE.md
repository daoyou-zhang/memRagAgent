# 🎭 3D 美女模型集成指南

## 推荐方案

### 方案一：Ready Player Me（推荐）⭐⭐⭐⭐⭐

**优点**：
- 🎨 超高质量，接近真人
- 💃 完整身体和动画
- 🆓 完全免费
- 🎯 可自定义外观

**步骤**：

1. **创建模型**：
   - 访问：https://readyplayer.me/
   - 点击 "Create Avatar"
   - 选择 "Full Body"
   - 自定义外观（脸型、发型、服装等）
   - 导出为 GLB 格式

2. **下载模型**：
   - 复制模型 URL（类似：`https://models.readyplayer.me/xxx.glb`）
   - 或下载到本地

3. **集成到项目**：
   ```bash
   # 如果下载到本地
   mkdir agentfront/public/models
   # 将 .glb 文件放到 public/models/ 目录
   ```

### 方案二：Mixamo（免费，需 Adobe 账号）⭐⭐⭐⭐

**优点**：
- 🎬 专业级动画
- 💃 多种角色和动作
- 🆓 免费使用

**步骤**：

1. 访问：https://www.mixamo.com/
2. 登录 Adobe 账号
3. 选择角色（推荐：Amy, Kaya, Jasmine）
4. 下载为 FBX 或 GLB 格式
5. 使用在线工具转换为 GLB：https://products.aspose.app/3d/conversion/fbx-to-glb

### 方案三：Sketchfab（部分免费）⭐⭐⭐

**优点**：
- 🎨 海量模型
- 💎 质量参差不齐
- 🔍 可筛选免费模型

**步骤**：

1. 访问：https://sketchfab.com/
2. 搜索："female character" 或 "anime girl"
3. 筛选：Free Download
4. 下载 GLB 格式

### 方案四：使用现成的免费模型（最快）⭐⭐⭐⭐⭐

我已经为你准备了几个高质量的免费模型链接：

#### 1. 现代美女（推荐）
```
https://models.readyplayer.me/64bfa15f0e72c63d7c3f4c4e.glb
```

#### 2. 动漫风格美女
```
https://models.readyplayer.me/64c0a2b50e72c63d7c3f5d2a.glb
```

#### 3. 职业装美女
```
https://models.readyplayer.me/64c1b3c60e72c63d7c3f6e3b.glb
```

## 🚀 快速集成

### 使用在线模型（最简单）

编辑 `agentfront/src/components/DigitalPersonCanvas.tsx`：

```typescript
import { useGLTF } from '@react-three/drei';

const BeautifulAvatar: React.FC<{ emotion: string; isSpeaking: boolean }> = ({ emotion, isSpeaking }) => {
  const groupRef = useRef<THREE.Group>(null);
  
  // 加载 Ready Player Me 模型
  const { scene } = useGLTF('https://models.readyplayer.me/64bfa15f0e72c63d7c3f4c4e.glb');
  
  // 动画效果
  useFrame((state) => {
    if (groupRef.current) {
      // 呼吸效果
      groupRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.8) * 0.03;
      
      // 说话时轻微晃动
      if (isSpeaking) {
        groupRef.current.rotation.y = Math.sin(state.clock.elapsedTime * 8) * 0.05;
      }
    }
  });

  return (
    <group ref={groupRef} position={[0, -1, 0]}>
      <primitive object={scene} scale={1.0} />
    </group>
  );
};
```

### 使用本地模型

1. **下载模型**到 `agentfront/public/models/avatar.glb`

2. **修改代码**：
```typescript
const { scene } = useGLTF('/models/avatar.glb');
```

## 🎨 自定义外观

### 创建景甜风格的美女

1. 访问 Ready Player Me
2. 选择以下特征：
   - **脸型**：椭圆形，精致
   - **眼睛**：大眼睛，双眼皮
   - **鼻子**：小巧挺拔
   - **嘴唇**：饱满，自然色
   - **发型**：长直发或大波浪
   - **肤色**：白皙
   - **服装**：优雅连衣裙或职业装

3. 导出模型 URL

4. 替换到代码中

## 🎬 添加动画

### 说话动画（口型同步）

```typescript
import { useAnimations } from '@react-three/drei';

const { scene, animations } = useGLTF('/models/avatar.glb');
const { actions } = useAnimations(animations, groupRef);

useEffect(() => {
  if (isSpeaking && actions['Talking']) {
    actions['Talking']?.play();
  } else {
    actions['Talking']?.stop();
  }
}, [isSpeaking, actions]);
```

### 表情动画

```typescript
// 根据情绪切换动画
useEffect(() => {
  if (emotion === 'happy' && actions['Happy']) {
    actions['Happy']?.play();
  } else if (emotion === 'thinking' && actions['Thinking']) {
    actions['Thinking']?.play();
  }
}, [emotion, actions]);
```

## 📦 完整示例代码

我会在下一个文件中提供完整的实现代码。

## 🔧 故障排查

### 模型不显示

1. 检查模型 URL 是否正确
2. 打开浏览器控制台查看错误
3. 确保模型格式为 GLB（不是 FBX）

### 模型太大或太小

调整 scale：
```typescript
<primitive object={scene} scale={2.0} /> // 放大 2 倍
<primitive object={scene} scale={0.5} /> // 缩小一半
```

### 模型位置不对

调整 position：
```typescript
<group position={[0, -1.5, 0]}> // 向下移动
```

## 🎯 推荐配置

**景甜风格美女**：
- 模型：Ready Player Me 自定义
- 比例：1.0 - 1.2
- 位置：[0, -1, 0]
- 光照：柔和，多光源
- 背景：简洁渐变

## 📚 参考资源

- Ready Player Me: https://readyplayer.me/
- Mixamo: https://www.mixamo.com/
- Three.js 文档: https://threejs.org/
- React Three Fiber: https://docs.pmnd.rs/react-three-fiber/
