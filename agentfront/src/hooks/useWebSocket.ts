/**
 * WebSocket Hook
 * 
 * 用于与后端建立 WebSocket 连接
 */
import { useEffect, useRef, useState, useCallback } from 'react';

interface UseWebSocketOptions {
  onMessage?: (data: any) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export const useWebSocket = (url: string, options: UseWebSocketOptions = {}) => {
  const {
    onMessage,
    onOpen,
    onClose,
    onError,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [reconnectCount, setReconnectCount] = useState(0);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const shouldReconnectRef = useRef(true);

  const connect = useCallback(() => {
    // 如果已经有连接，先关闭
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('⚠️ 已有活跃连接，跳过重连');
      return;
    }

    try {
      console.log('🔌 尝试连接 WebSocket:', url);
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log('✅ WebSocket 连接成功');
        setIsConnected(true);
        setReconnectCount(0);
        shouldReconnectRef.current = true;
        onOpen?.();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage?.(data);
        } catch (error) {
          console.error('❌ 解析消息失败:', error);
        }
      };

      ws.onclose = () => {
        console.log('🔌 WebSocket 连接关闭');
        setIsConnected(false);
        onClose?.();

        // 只有在应该重连且未达到最大次数时才重连
        if (shouldReconnectRef.current && reconnectCount < maxReconnectAttempts) {
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log(`🔄 尝试重连 (${reconnectCount + 1}/${maxReconnectAttempts})...`);
            setReconnectCount(prev => prev + 1);
            connect();
          }, reconnectInterval);
        } else if (reconnectCount >= maxReconnectAttempts) {
          console.log('❌ 达到最大重连次数，停止重连');
        }
      };

      ws.onerror = (error) => {
        console.error('❌ WebSocket 错误:', error);
        onError?.(error);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('❌ 创建 WebSocket 连接失败:', error);
    }
  }, [url, onMessage, onOpen, onClose, onError, reconnectCount, maxReconnectAttempts, reconnectInterval]);

  useEffect(() => {
    shouldReconnectRef.current = true;
    connect();

    return () => {
      console.log('🧹 清理 WebSocket 连接');
      shouldReconnectRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [url]); // 只在 URL 变化时重新连接

  const sendMessage = useCallback((data: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      console.warn('⚠️ WebSocket 未连接，无法发送消息');
    }
  }, []);

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    if (wsRef.current) {
      wsRef.current.close();
    }
  }, []);

  return {
    isConnected,
    sendMessage,
    disconnect,
    reconnectCount
  };
};
