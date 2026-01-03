/**
 * 带回退的模型组件
 * 
 * 直接尝试加载真实 GLB 模型，如果失败则回退到程序化模型
 */
import React, { useState } from 'react';
import BeautifulAvatarModel from './BeautifulAvatarModel';
import ImprovedAvatarModel from './ImprovedAvatarModel';

interface ModelWithFallbackProps {
  emotion?: 'neutral' | 'happy' | 'thinking';
  isSpeaking?: boolean;
}

/**
 * 错误边界组件
 */
class ErrorBoundary extends React.Component<
  { children: React.ReactNode; onError: () => void },
  { hasError: boolean }
> {
  constructor(props: { children: React.ReactNode; onError: () => void }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error) {
    console.error('⚠️ 模型加载错误:', error.message);
    this.props.onError();
  }

  render() {
    if (this.state.hasError) return null;
    return this.props.children;
  }
}

/**
 * 智能模型加载器 - 简化版
 */
const ModelWithFallback: React.FC<ModelWithFallbackProps> = ({ emotion, isSpeaking }) => {
  const [useRealModel, setUseRealModel] = useState(true);

  // 模型加载失败的回调
  const handleModelError = () => {
    console.warn('⚠️ 真实模型加载失败，切换为程序化模型');
    setUseRealModel(false);
  };

  console.log('🎨 当前使用:', useRealModel ? '真实模型 (BeautifulAvatarModel)' : '程序化模型 (ImprovedAvatarModel)');

  // 直接尝试加载真实模型，失败则回退
  return useRealModel ? (
    <ErrorBoundary onError={handleModelError}>
      <BeautifulAvatarModel emotion={emotion} isSpeaking={isSpeaking || false} />
    </ErrorBoundary>
  ) : (
    <ImprovedAvatarModel emotion={emotion} isSpeaking={isSpeaking || false} />
  );
};

export default ModelWithFallback;
