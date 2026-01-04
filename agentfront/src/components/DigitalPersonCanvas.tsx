/**
 * 3D 数字人画布组件
 * 
 * 使用 Three.js + React Three Fiber 渲染真实的 3D 美女模型
 */
import React, { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { Box, CircularProgress } from '@mui/material';
import BeautifulAvatarModel from './BeautifulAvatarModel';

interface DigitalPersonCanvasProps {
  emotion?: 'neutral' | 'happy' | 'thinking';
  isSpeaking?: boolean;
}

/**
 * 场景灯光 - 优化以减少塑料感
 */
const Lights: React.FC = () => {
  return (
    <>
      {/* 主光源（模拟自然光，柔和一些） */}
      <directionalLight 
        position={[5, 8, 5]} 
        intensity={1.2}
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
        color="#fff5e6"
      />
      
      {/* 补光（从侧面，减少阴影） */}
      <directionalLight 
        position={[-5, 4, -3]} 
        intensity={0.8}
        color="#e6f2ff"
      />
      
      {/* 环境光（增强，减少对比度） */}
      <ambientLight intensity={0.8} />
      
      {/* 半球光（模拟天空和地面反射） */}
      <hemisphereLight 
        color="#ffffff"
        groundColor="#444444"
        intensity={0.6}
      />
    </>
  );
};

/**
 * 简洁渐变背景
 */
const SimpleBackground: React.FC = () => {
  return (
    <>
      {/* 渐变背景墙 */}
      <mesh position={[0, 1, -4]} scale={[25, 25, 1]} receiveShadow>
        <planeGeometry />
        <meshBasicMaterial>
          <primitive 
            attach="map" 
            object={(() => {
              const canvas = document.createElement('canvas');
              canvas.width = 512;
              canvas.height = 512;
              const ctx = canvas.getContext('2d')!;
              const gradient = ctx.createLinearGradient(0, 0, 0, 512);
              gradient.addColorStop(0, '#0f0c29');
              gradient.addColorStop(0.5, '#302b63');
              gradient.addColorStop(1, '#24243e');
              ctx.fillStyle = gradient;
              ctx.fillRect(0, 0, 512, 512);
              return new THREE.CanvasTexture(canvas);
            })()} 
          />
        </meshBasicMaterial>
      </mesh>
      
      {/* 地板（反射效果） */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.2, 0]} receiveShadow>
        <planeGeometry args={[15, 15]} />
        <meshStandardMaterial 
          color="#1a1a2e" 
          roughness={0.3}
          metalness={0.6}
        />
      </mesh>
    </>
  );
};

/**
 * 加载提示
 */
const LoadingFallback: React.FC = () => {
  return (
    <Box 
      sx={{ 
        display: 'flex', 
        flexDirection: 'column',
        alignItems: 'center', 
        justifyContent: 'center',
        height: '100%',
        bgcolor: '#0a0a0a'
      }}
    >
      <CircularProgress sx={{ color: '#667eea' }} size={60} />
      <Box sx={{ color: 'white', opacity: 0.8, mt: 2 }}>加载 3D 模型中...</Box>
    </Box>
  );
};

/**
 * 主画布组件
 */
const DigitalPersonCanvas: React.FC<DigitalPersonCanvasProps> = ({ 
  emotion = 'neutral', 
  isSpeaking = false 
}) => {
  return (
    <Box sx={{ width: '100%', height: '100%', bgcolor: '#0a0a0a' }}>
      <Suspense fallback={<LoadingFallback />}>
        <Canvas shadows camera={{ position: [0, 0.8, 4], fov: 50 }}>
          {/* 灯光 */}
          <Lights />
          
          {/* 背景 */}
          <SimpleBackground />
          
          {/* 3D 美女模型 - 直接使用真实模型测试 */}
          <BeautifulAvatarModel emotion={emotion} isSpeaking={isSpeaking} />
          
          {/* 轨道控制（允许用户旋转视角） */}
          <OrbitControls 
            enableZoom={true}
            enablePan={false}
            minDistance={2}
            maxDistance={8}
            minPolarAngle={Math.PI / 6}
            maxPolarAngle={Math.PI / 2}
            target={[0, 0.8, 0]}
          />
        </Canvas>
      </Suspense>
    </Box>
  );
};

export default DigitalPersonCanvas;
