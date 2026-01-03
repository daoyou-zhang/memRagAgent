/**
 * 改进的程序化 3D 美女模型
 * 
 * 不依赖外部模型文件，使用 Three.js 程序化生成
 * 效果比简单几何体好很多，适合作为临时方案或后备方案
 */
import React, { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface ImprovedAvatarProps {
  emotion?: 'neutral' | 'happy' | 'thinking';
  isSpeaking: boolean;
}

/**
 * 改进的 3D 美女模型
 * 
 * 使用更精细的几何体和材质，创造更逼真的效果
 */
const ImprovedAvatarModel: React.FC<ImprovedAvatarProps> = ({ emotion, isSpeaking }) => {
  const groupRef = useRef<THREE.Group>(null);
  const headRef = useRef<THREE.Mesh>(null);
  const leftEyeRef = useRef<THREE.Mesh>(null);
  const rightEyeRef = useRef<THREE.Mesh>(null);
  const mouthRef = useRef<THREE.Mesh>(null);
  
  // 创建皮肤材质
  const skinMaterial = useMemo(() => new THREE.MeshStandardMaterial({
    color: '#ffd4b8',
    roughness: 0.4,
    metalness: 0.1,
    flatShading: false,
  }), []);
  
  // 创建头发材质
  const hairMaterial = useMemo(() => new THREE.MeshStandardMaterial({
    color: '#2c1810',
    roughness: 0.7,
    metalness: 0.05,
  }), []);
  
  // 创建服装材质
  const dressMaterial = useMemo(() => new THREE.MeshStandardMaterial({
    color: '#ffffff',
    roughness: 0.3,
    metalness: 0.1,
  }), []);
  
  // 动画
  useFrame((state) => {
    if (groupRef.current) {
      // 呼吸效果
      groupRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.8) * 0.03 - 0.8;
    }
    
    // 说话动画
    if (headRef.current && isSpeaking) {
      headRef.current.rotation.y = Math.sin(state.clock.elapsedTime * 8) * 0.08;
      headRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 6) * 0.03;
    }
    
    // 眨眼动画
    const blinkTime = state.clock.elapsedTime % 4;
    if (blinkTime > 3.8 && blinkTime < 3.9) {
      if (leftEyeRef.current) leftEyeRef.current.scale.y = 0.3;
      if (rightEyeRef.current) rightEyeRef.current.scale.y = 0.3;
    } else {
      if (leftEyeRef.current) leftEyeRef.current.scale.y = 1;
      if (rightEyeRef.current) rightEyeRef.current.scale.y = 1;
    }
    
    // 嘴巴动画（说话时）
    if (mouthRef.current && isSpeaking) {
      const mouthScale = 1 + Math.sin(state.clock.elapsedTime * 10) * 0.3;
      mouthRef.current.scale.y = mouthScale;
    } else if (mouthRef.current) {
      mouthRef.current.scale.y = 1;
    }
  });
  
  return (
    <group ref={groupRef} position={[0, 0, 0]}>
      {/* 头部 */}
      <mesh ref={headRef} position={[0, 1.6, 0]} castShadow material={skinMaterial}>
        <sphereGeometry args={[0.18, 32, 32]} />
      </mesh>
      
      {/* 眼睛 */}
      <mesh ref={leftEyeRef} position={[-0.06, 1.65, 0.15]} castShadow>
        <sphereGeometry args={[0.025, 16, 16]} />
        <meshStandardMaterial color="#2c1810" />
      </mesh>
      <mesh ref={rightEyeRef} position={[0.06, 1.65, 0.15]} castShadow>
        <sphereGeometry args={[0.025, 16, 16]} />
        <meshStandardMaterial color="#2c1810" />
      </mesh>
      
      {/* 眼睛高光 */}
      <mesh position={[-0.055, 1.66, 0.17]}>
        <sphereGeometry args={[0.008, 8, 8]} />
        <meshBasicMaterial color="#ffffff" />
      </mesh>
      <mesh position={[0.065, 1.66, 0.17]}>
        <sphereGeometry args={[0.008, 8, 8]} />
        <meshBasicMaterial color="#ffffff" />
      </mesh>
      
      {/* 眉毛 */}
      <mesh position={[-0.06, 1.7, 0.14]} rotation={[0, 0, -0.2]}>
        <boxGeometry args={[0.05, 0.01, 0.01]} />
        <meshStandardMaterial color="#2c1810" />
      </mesh>
      <mesh position={[0.06, 1.7, 0.14]} rotation={[0, 0, 0.2]}>
        <boxGeometry args={[0.05, 0.01, 0.01]} />
        <meshStandardMaterial color="#2c1810" />
      </mesh>
      
      {/* 嘴巴 */}
      <mesh ref={mouthRef} position={[0, 1.54, 0.15]}>
        <sphereGeometry args={[0.035, 16, 16, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <meshStandardMaterial color="#ff6b9d" />
      </mesh>
      
      {/* 鼻子 */}
      <mesh position={[0, 1.59, 0.17]}>
        <sphereGeometry args={[0.015, 16, 16]} />
        <meshStandardMaterial color="#ffc4a8" />
      </mesh>
      
      {/* 脖子 */}
      <mesh position={[0, 1.4, 0]} castShadow material={skinMaterial}>
        <cylinderGeometry args={[0.08, 0.1, 0.15, 32]} />
      </mesh>
      
      {/* 身体（优雅的连衣裙） */}
      <mesh position={[0, 0.95, 0]} castShadow material={dressMaterial}>
        <cylinderGeometry args={[0.22, 0.32, 0.9, 32]} />
      </mesh>
      
      {/* 腰带装饰 */}
      <mesh position={[0, 1.0, 0]}>
        <cylinderGeometry args={[0.23, 0.23, 0.05, 32]} />
        <meshStandardMaterial color="#667eea" roughness={0.2} metalness={0.5} />
      </mesh>
      
      {/* 手臂 */}
      <mesh position={[-0.28, 1.05, 0]} rotation={[0, 0, 0.4]} castShadow material={skinMaterial}>
        <cylinderGeometry args={[0.045, 0.04, 0.65, 16]} />
      </mesh>
      <mesh position={[0.28, 1.05, 0]} rotation={[0, 0, -0.4]} castShadow material={skinMaterial}>
        <cylinderGeometry args={[0.045, 0.04, 0.65, 16]} />
      </mesh>
      
      {/* 手掌 */}
      <mesh position={[-0.38, 0.75, 0]} castShadow material={skinMaterial}>
        <sphereGeometry args={[0.05, 16, 16]} />
      </mesh>
      <mesh position={[0.38, 0.75, 0]} castShadow material={skinMaterial}>
        <sphereGeometry args={[0.05, 16, 16]} />
      </mesh>
      
      {/* 腿部 */}
      <mesh position={[-0.12, 0.15, 0]} castShadow material={skinMaterial}>
        <cylinderGeometry args={[0.09, 0.08, 0.7, 16]} />
      </mesh>
      <mesh position={[0.12, 0.15, 0]} castShadow material={skinMaterial}>
        <cylinderGeometry args={[0.09, 0.08, 0.7, 16]} />
      </mesh>
      
      {/* 鞋子 */}
      <mesh position={[-0.12, -0.18, 0.03]} castShadow>
        <boxGeometry args={[0.12, 0.08, 0.18]} />
        <meshStandardMaterial color="#764ba2" />
      </mesh>
      <mesh position={[0.12, -0.18, 0.03]} castShadow>
        <boxGeometry args={[0.12, 0.08, 0.18]} />
        <meshStandardMaterial color="#764ba2" />
      </mesh>
      
      {/* 头发（长发） */}
      <mesh position={[0, 1.72, -0.08]} castShadow material={hairMaterial}>
        <sphereGeometry args={[0.2, 32, 32, 0, Math.PI * 2, 0, Math.PI * 0.65]} />
      </mesh>
      
      {/* 头发（侧面） */}
      <mesh position={[-0.15, 1.6, 0]} castShadow material={hairMaterial}>
        <sphereGeometry args={[0.12, 16, 16]} />
      </mesh>
      <mesh position={[0.15, 1.6, 0]} castShadow material={hairMaterial}>
        <sphereGeometry args={[0.12, 16, 16]} />
      </mesh>
      
      {/* 头发（后面长发） */}
      <mesh position={[0, 1.3, -0.15]} castShadow material={hairMaterial}>
        <cylinderGeometry args={[0.08, 0.12, 0.6, 16]} />
      </mesh>
      
      {/* 头发（刘海） */}
      <mesh position={[0, 1.7, 0.1]} castShadow material={hairMaterial}>
        <boxGeometry args={[0.25, 0.08, 0.08]} />
      </mesh>
    </group>
  );
};

export default ImprovedAvatarModel;
