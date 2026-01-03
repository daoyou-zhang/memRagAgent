# 🎨 获取漂亮的 3D 美女模型 - 详细指南

## 🎯 目标

获取一个**高质量、漂亮的 3D 美女模型**（类似景甜风格）

## ⚡ 最快方式（推荐）

### 方案 A：Sketchfab - 5 分钟搞定 ⭐⭐⭐⭐⭐

**为什么选择 Sketchfab？**
- ✅ 中国可以访问
- ✅ 大量免费高质量模型
- ✅ 直接下载 GLB 格式
- ✅ 不需要注册（部分模型）

#### 具体步骤：

1. **打开 Sketchfab**
   ```
   https://sketchfab.com/
   ```

2. **搜索高质量美女模型**
   
   在搜索框输入以下关键词之一：
   - `anime girl rigged free` （动漫风格）
   - `female character realistic free` （写实风格）
   - `beautiful woman character` （美女角色）
   - `asian female character free` （亚洲女性）

3. **设置筛选条件**
   
   在左侧筛选栏选择：
   - ✅ **Downloadable** （可下载）
   - ✅ **Free** （免费）
   - ✅ **Rigged** （带骨骼，可以动画）
   - ✅ **Animated** （可选，带动画更好）

4. **推荐的具体模型**

   **动漫风格美女：**
   - 搜索：`anime girl rigged free download`
   - 选择评分高、下载多的模型
   - 看预览图，选择你喜欢的

   **写实风格美女：**
   - 搜索：`realistic female character free`
   - 选择面部精致、身材好的模型

5. **下载模型**
   
   - 点击模型进入详情页
   - 点击右下角 **"Download 3D Model"** 按钮
   - 选择 **"glTF"** 格式（会下载 .glb 文件）
   - 如果需要登录，可以用邮箱快速注册（免费）

6. **放置模型**
   
   ```bash
   # Windows
   # 将下载的 .glb 文件重命名为 avatar.glb
   # 放到：agentfront\public\models\avatar.glb
   
   # 如果 models 文件夹不存在，创建它
   mkdir agentfront\public\models
   ```

7. **刷新浏览器**
   
   模型会自动加载！

---

### 方案 B：Mixamo - 专业级质量 ⭐⭐⭐⭐

**优点：**
- 专业级质量
- Adobe 官方
- 自带动画
- 完全免费

#### 具体步骤：

1. **访问 Mixamo**
   ```
   https://www.mixamo.com/
   ```

2. **登录 Adobe 账号**
   - 如果没有，免费注册一个
   - 使用邮箱即可

3. **选择美女角色**
   
   推荐的漂亮女性角色：
   - **Amy** - 现代美女，长发
   - **Kaya** - 时尚美女，短发
   - **Jasmine** - 优雅美女
   - **Remy** - 可爱美女

4. **下载角色**
   
   - 点击角色
   - 点击右上角 **"Download"**
   - Format: **FBX for Unity (.fbx)**
   - Pose: **T-Pose**
   - 点击 **Download**

5. **转换为 GLB**
   
   使用在线转换工具（中国可访问）：
   ```
   https://products.aspose.app/3d/zh/conversion/fbx-to-glb
   ```
   
   - 上传下载的 .fbx 文件
   - 点击 **"转换"**
   - 下载转换后的 .glb 文件

6. **放置模型**
   ```bash
   # 重命名为 avatar.glb
   # 放到：agentfront\public\models\avatar.glb
   ```

---

### 方案 C：爱给网 - 国内资源 ⭐⭐⭐

**优点：**
- 国内网站，速度快
- 中文界面
- 免费资源多

#### 具体步骤：

1. **访问爱给网**
   ```
   https://www.aigei.com/3d/character/
   ```

2. **搜索模型**
   - 搜索：`女性角色`
   - 筛选：免费

3. **下载模型**
   - 选择喜欢的模型
   - 下载（通常是 FBX 或 OBJ 格式）

4. **转换为 GLB**
   - 使用 Aspose 转换器（见方案 B）

5. **放置模型**
   ```bash
   # 放到：agentfront\public\models\avatar.glb
   ```

---

## 🎨 如何选择好看的模型？

### 关键特征：

1. **面部精致**
   - 眼睛大而有神
   - 五官立体
   - 皮肤细腻

2. **身材比例好**
   - 身高比例协调
   - 身材匀称

3. **服装得体**
   - 现代服装
   - 颜色搭配好

4. **带骨骼（Rigged）**
   - 可以做动画
   - 必须选择

5. **多边形数适中**
   - 10K - 50K 三角面最佳
   - 太少会很粗糙
   - 太多会卡顿

### 推荐风格：

**动漫风格（Anime Style）：**
- 大眼睛
- 可爱
- 颜色鲜艳
- 适合：二次元爱好者

**写实风格（Realistic Style）：**
- 真实感强
- 细节丰富
- 适合：追求真实感

**卡通风格（Cartoon Style）：**
- 简洁
- 可爱
- 适合：轻松氛围

---

## 📁 文件放置位置

```
agentfront/
└── public/
    └── models/
        └── avatar.glb  ← 放这里！
```

**完整路径：**
```
D:\workspace\memRagAgent\agentfront\public\models\avatar.glb
```

---

## ✅ 验证模型

下载完成后，运行：

```bash
cd agentfront
python download_model.py
```

会检查模型是否正确放置。

---

## 🎯 推荐的具体模型（已验证）

### Sketchfab 上的免费美女模型：

1. **搜索关键词：** `anime girl rigged free`
   - 排序：Most Downloaded
   - 选择前几个，质量都很好

2. **搜索关键词：** `female character realistic free`
   - 筛选：Rigged + Free
   - 选择面部精致的

3. **搜索关键词：** `beautiful woman character`
   - 筛选：Downloadable + Free
   - 选择评分高的

---

## 🚀 下载后立即可用

1. **下载模型** → 重命名为 `avatar.glb`
2. **放到** → `agentfront/public/models/avatar.glb`
3. **刷新浏览器** → http://localhost:5175
4. **完成！** 🎉

模型会自动加载，替换掉程序化模型。

---

## 💡 提示

- **文件大小**：建议 5-20 MB
- **格式**：必须是 .glb 或 .gltf
- **骨骼**：必须带骨骼（Rigged）
- **动画**：可选，有更好

---

## ❓ 常见问题

**Q: 模型下载后不显示？**
A: 检查文件名是否为 `avatar.glb`，路径是否正确

**Q: 模型太大或太小？**
A: 在代码中调整 scale 参数

**Q: 模型没有动画？**
A: 确保下载的是 Rigged 模型

**Q: Sketchfab 需要登录？**
A: 部分模型需要，用邮箱免费注册即可

---

## 🎉 完成

按照以上步骤，5-10 分钟就能获得一个**漂亮的 3D 美女模型**！

**推荐顺序：**
1. 先试 Sketchfab（最快）
2. 如果不满意，试 Mixamo（质量最高）
3. 如果都不行，试爱给网（国内）

祝你找到满意的模型！💖
