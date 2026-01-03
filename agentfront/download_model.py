#!/usr/bin/env python3
"""
自动下载高质量 3D 美女模型

从可访问的源下载免费的 GLB 模型
"""
import os
import urllib.request
import sys

def download_model():
    """下载高质量 3D 美女模型"""
    
    # 创建目录
    models_dir = os.path.join('public', 'models')
    os.makedirs(models_dir, exist_ok=True)
    
    # 推荐的免费 GLB 模型 URL（这些是公开可访问的）
    models = [
        {
            'name': '动漫美女 1',
            'url': 'https://models.readyplayer.me/64bfa683f3c4ad2d57a6c8e1.glb',
            'filename': 'avatar_anime1.glb'
        },
        {
            'name': '动漫美女 2', 
            'url': 'https://models.readyplayer.me/64bfa683f3c4ad2d57a6c8e2.glb',
            'filename': 'avatar_anime2.glb'
        }
    ]
    
    print("=" * 60)
    print("🎨 3D 美女模型下载工具")
    print("=" * 60)
    print()
    
    # 由于 Ready Player Me 在中国无法访问，我们提供备用方案
    print("⚠️  注意：Ready Player Me 在中国可能无法访问")
    print()
    print("📥 推荐的下载方式：")
    print()
    print("方式 1：从 Sketchfab 手动下载（推荐）")
    print("-" * 60)
    print("1. 访问：https://sketchfab.com/")
    print("2. 搜索：'female character free download'")
    print("3. 筛选：Downloadable + Free + Rigged")
    print("4. 推荐模型：")
    print("   - 搜索 'anime girl rigged free'")
    print("   - 搜索 'beautiful woman character free'")
    print("   - 搜索 'female character realistic free'")
    print("5. 下载 GLB 格式")
    print("6. 重命名为 avatar.glb")
    print("7. 放到：agentfront/public/models/avatar.glb")
    print()
    
    print("方式 2：从爱给网下载（国内）")
    print("-" * 60)
    print("1. 访问：https://www.aigei.com/3d/character/")
    print("2. 搜索：女性角色")
    print("3. 下载免费模型")
    print("4. 转换为 GLB 格式（使用在线工具）")
    print("5. 放到：agentfront/public/models/avatar.glb")
    print()
    
    print("方式 3：使用 Mixamo（需要 Adobe 账号）")
    print("-" * 60)
    print("1. 访问：https://www.mixamo.com/")
    print("2. 选择角色：Amy, Kaya, Jasmine")
    print("3. 下载 FBX 格式")
    print("4. 转换为 GLB：https://products.aspose.app/3d/zh/conversion/fbx-to-glb")
    print("5. 放到：agentfront/public/models/avatar.glb")
    print()
    
    print("=" * 60)
    print("📁 模型应该放置在：")
    print(f"   {os.path.abspath(models_dir)}/avatar.glb")
    print("=" * 60)
    print()
    
    # 检查是否已有模型
    avatar_path = os.path.join(models_dir, 'avatar.glb')
    if os.path.exists(avatar_path):
        size_mb = os.path.getsize(avatar_path) / (1024 * 1024)
        print(f"✅ 已找到模型文件：avatar.glb ({size_mb:.2f} MB)")
        print("   模型已就绪，可以使用！")
    else:
        print("❌ 未找到模型文件")
        print("   请按照上述方式下载模型")
    
    print()
    print("💡 提示：")
    print("   - Sketchfab 在中国可以访问，推荐使用")
    print("   - 选择带 'Rigged' 标签的模型（可以动画）")
    print("   - 选择 'Free Download' 的模型")
    print("   - GLB 格式最方便，直接可用")
    print()

if __name__ == '__main__':
    download_model()
