/**
 * 真实 3D 美女模型组件
 * 
 * 加载本地 GLB 模型，支持自动缩放和动画
 */
import React, { useRef, useEffect, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import { useGLTF, useAnimations } from '@react-three/drei';
import * as THREE from 'three';

interface BeautifulAvatarProps {
  emotion?: 'neutral' | 'happy' | 'thinking';
  isSpeaking?: boolean;
  modelUrl?: string;
}

/**
 * 真实 3D 美女模型
 * 
 * 使用本地 GLB 模型，自动调整大小和位置
 */
const BeautifulAvatarModel: React.FC<BeautifulAvatarProps> = ({ 
  emotion = 'neutral', 
  isSpeaking = false,
  modelUrl = '/models/avatar.glb'  // 本地模型路径
}) => {
  const groupRef = useRef<THREE.Group>(null);
  const headRef = useRef<THREE.Object3D | null>(null);
  const [modelScale, setModelScale] = useState(1.0);
  const [modelOffset, setModelOffset] = useState(0);
  const currentAnimationRef = useRef<string | null>(null);
  
  // 加载 GLB 模型
  const { scene, animations } = useGLTF(modelUrl);
  const { actions, mixer } = useAnimations(animations, groupRef);
  
  // 自动调整模型大小和位置
  useEffect(() => {
    if (scene) {
      // 计算模型的边界框
      const box = new THREE.Box3().setFromObject(scene);
      const size = box.getSize(new THREE.Vector3());
      
      // 调整缩放，使模型高度约为 2 个单位
      const targetHeight = 2.0;
      const scale = targetHeight / size.y;
      setModelScale(scale);
      
      // 调整位置，使模型居中显示
      const offset = -box.min.y * scale;
      setModelOffset(offset - 0.2); // 稍微下移一点点，确保脚部完全可见
      
      console.log('✅ 模型加载成功！');
      console.log(`📏 原始尺寸: ${size.x.toFixed(2)} x ${size.y.toFixed(2)} x ${size.z.toFixed(2)}`);
      console.log(`📦 边界框: min(${box.min.y.toFixed(2)}) max(${box.max.y.toFixed(2)})`);
      console.log(`🔍 缩放比例: ${scale.toFixed(2)}`);
      console.log(`📍 位置偏移: ${(offset - 0.2).toFixed(2)}`);
      console.log(`📐 模型中心: ${box.getCenter(new THREE.Vector3()).y.toFixed(2)}`);
      
      // 遍历场景，修复材质和纹理
      scene.traverse((child) => {
        const name = child.name.toLowerCase();
        const materialName = (child as THREE.Mesh).material?.name?.toLowerCase() || '';
        
        // 查找头部骨骼
        if (name.includes('head') || name.includes('neck')) {
          headRef.current = child;
          console.log('👤 找到头部骨骼:', child.name);
        }
        
        // 修复材质
        if (child instanceof THREE.Mesh) {
          // 禁用视锥体裁剪，防止模型被裁掉
          child.frustumCulled = false;
          
          // 启用阴影
          child.castShadow = true;
          child.receiveShadow = true;
          
          console.log(`🔍 网格: ${child.name}`, {
            hasMaterial: !!child.material,
            materialType: child.material?.type,
            materialName: (child.material as THREE.Material)?.name,
            geometry: child.geometry?.type
          });
          
          // 确保材质正确渲染
          if (child.material) {
            const materials = Array.isArray(child.material) ? child.material : [child.material];
            
            materials.forEach((mat: THREE.Material, index: number) => {
              const matName = mat.name.toLowerCase();
              
              // 强制更新材质
              mat.needsUpdate = true;
              
              if (mat instanceof THREE.MeshStandardMaterial || mat instanceof THREE.MeshPhysicalMaterial) {
                // 强制开启颜色写入
                mat.colorWrite = true;
                
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
                
                // 设置双面渲染（头发、衣服等）
                if (needsDoubleSide) {
                  mat.side = THREE.DoubleSide;
                  console.log(`🔄 材质 ${mat.name} 设置为双面渲染`);
                }
                
                // 如果材质是透明的但 opacity 很低，可能是转换问题
                if (mat.transparent && mat.opacity < 0.1) {
                  console.log(`⚠️  材质 ${mat.name} 几乎完全透明，强制设置为可见`);
                  mat.opacity = 1.0;
                  mat.transparent = false;
                }
                
                // 如果有贴图，确保正确加载
                if (mat.map) {
                  mat.map.needsUpdate = true;
                  mat.map.colorSpace = THREE.SRGBColorSpace;
                  console.log(`🖼️  材质 ${mat.name} 有颜色贴图:`, mat.map.image?.src || '内嵌纹理');
                }
                
                // 法线贴图
                if (mat.normalMap) {
                  mat.normalMap.needsUpdate = true;
                  console.log(`🗺️  材质 ${mat.name} 有法线贴图`);
                }
                
                // 粗糙度贴图
                if (mat.roughnessMap) {
                  mat.roughnessMap.needsUpdate = true;
                }
                
                // 金属度贴图
                if (mat.metalnessMap) {
                  mat.metalnessMap.needsUpdate = true;
                }
                
                // 调整材质属性以获得更好的视觉效果（减少塑料感）
                // 增加粗糙度，减少金属度
                if (mat.roughness !== undefined) {
                  mat.roughness = Math.max(mat.roughness, 0.6); // 至少 0.6 的粗糙度
                }
                if (mat.metalness !== undefined) {
                  mat.metalness = Math.min(mat.metalness, 0.1); // 最多 0.1 的金属度
                }
                
                // 确保非透明材质完全不透明
                if (!mat.transparent) {
                  mat.opacity = 1.0;
                }
                
                console.log(`🎨 材质 ${mat.name || '未命名'}`, {
                  type: mat.type,
                  hasMap: !!mat.map,
                  hasNormalMap: !!mat.normalMap,
                  hasRoughnessMap: !!mat.roughnessMap,
                  hasMetalnessMap: !!mat.metalnessMap,
                  color: mat.color?.getHexString(),
                  transparent: mat.transparent,
                  opacity: mat.opacity,
                  side: mat.side === THREE.DoubleSide ? 'DoubleSide' : 'FrontSide',
                  roughness: mat.roughness,
                  metalness: mat.metalness
                });
              } else {
                console.log(`⚠️  材质 ${mat.name} 类型: ${mat.type} (非标准材质)`);
              }
            });
          }
        }
      });
    }
  }, [scene]);
  
  // 播放动画 - 顺次循环播放
  useEffect(() => {
    if (actions && Object.keys(actions).length > 0) {
      console.log(`🎬 找到 ${Object.keys(actions).length} 个动画:`, Object.keys(actions));
      
      const animationNames = Object.keys(actions);
      let currentIndex = 0;
      
      // 播放下一个动画的函数
      const playNextAnimation = () => {
        const animName = animationNames[currentIndex];
        const action = actions[animName];
        
        if (action) {
          // 停止所有其他动画
          Object.values(actions).forEach(a => a?.stop());
          
          // 播放当前动画
          action.reset().play();
          action.setLoop(THREE.LoopOnce, 1); // 只播放一次
          console.log(`🎭 播放动画 ${currentIndex + 1}/${animationNames.length}: ${animName}`);
          
          // 移动到下一个动画索引
          currentIndex = (currentIndex + 1) % animationNames.length;
        }
      };
      
      // 监听动画结束事件
      const onFinished = () => {
        setTimeout(() => {
          playNextAnimation();
        }, 500); // 等待 0.5 秒后播放下一个
      };
      
      if (mixer) {
        mixer.addEventListener('finished', onFinished);
      }
      
      // 开始播放第一个动画
      playNextAnimation();
      
      return () => {
        if (mixer) {
          mixer.removeEventListener('finished', onFinished);
        }
        Object.values(actions).forEach(action => action?.stop());
      };
    } else {
      console.log('ℹ️  模型没有动画（这是正常的）');
    }
  }, [actions, mixer]);
  
  // 动画循环
  useFrame((state, delta) => {
    if (groupRef.current) {
      // 轻微的呼吸效果
      groupRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.8) * 0.03 + modelOffset;
    }
    
    // 说话时的头部动画
    if (headRef.current && isSpeaking) {
      headRef.current.rotation.y = Math.sin(state.clock.elapsedTime * 8) * 0.08;
      headRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 6) * 0.03;
    } else if (headRef.current) {
      // 平滑回到原位
      headRef.current.rotation.y *= 0.9;
      headRef.current.rotation.x *= 0.9;
    }
    
    // 更新动画混合器
    if (mixer) {
      mixer.update(delta);
    }
  });
  
  return (
    <group ref={groupRef} position={[0, 0, 0]}>
      <primitive 
        object={scene} 
        scale={modelScale}
        castShadow
        receiveShadow
        frustumCulled={false}
      />
    </group>
  );
};

export default BeautifulAvatarModel;
