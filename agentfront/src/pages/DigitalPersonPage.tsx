/**
 * 3D 数字人页面
 * 
 * 完美漂亮的 3D 美女数字人，支持实时语音交互
 */
import React, { useState, useRef, useEffect } from 'react';
import { Box, Paper, TextField, IconButton, Typography, Stack, Chip, Avatar } from '@mui/material';
import { Send, Mic, MicOff, VolumeUp, VolumeOff, Refresh } from '@mui/icons-material';
import DigitalPersonCanvas from '../components/DigitalPersonCanvas';
import { useWebSocket } from '../hooks/useWebSocket';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

// 生成或获取持久化的 session_id
const getSessionId = (): string => {
  let sessionId = localStorage.getItem('session_id');
  if (!sessionId) {
    sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem('session_id', sessionId);
    console.log('🆕 创建新 session:', sessionId);
  } else {
    console.log('📌 使用现有 session:', sessionId);
  }
  return sessionId;
};

const DigitalPersonPage: React.FC = () => {
  // 使用持久化的 session_id
  const [sessionId] = useState<string>(getSessionId());
  
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: '你好！我是道友，你的智能助手。有什么可以帮助你的吗？',
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [emotion, setEmotion] = useState<'neutral' | 'happy' | 'thinking'>('neutral');
  
  // 历史消息加载状态
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [hasMoreHistory, setHasMoreHistory] = useState(true);
  const [historyOffset, setHistoryOffset] = useState(0);
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  // 加载聊天历史
  const loadChatHistory = async (offset: number = 0, isInitial: boolean = false) => {
    if (isLoadingHistory || (!hasMoreHistory && !isInitial)) return;
    
    setIsLoadingHistory(true);
    
    try {
      const response = await fetch(
        `http://localhost:8001/api/v1/chat/history/${sessionId}?limit=50&offset=${offset}`
      );
      
      if (!response.ok) {
        throw new Error('加载历史失败');
      }
      
      const data = await response.json();
      
      if (data.messages && data.messages.length > 0) {
        const historyMessages: Message[] = data.messages.map((msg: any) => ({
          role: msg.role,
          content: msg.content,
          timestamp: new Date(msg.timestamp)
        }));
        
        if (isInitial) {
          // 初始加载：替换欢迎消息
          setMessages(historyMessages);
        } else {
          // 下拉加载：添加到顶部
          setMessages(prev => [...historyMessages, ...prev]);
        }
        
        setHistoryOffset(offset + data.messages.length);
        setHasMoreHistory(data.has_more);
        
        console.log(`📚 加载了 ${data.messages.length} 条历史消息`);
      } else if (isInitial) {
        // 没有历史，保持欢迎消息
        console.log('📭 没有历史消息');
      }
    } catch (error) {
      console.error('❌ 加载历史失败:', error);
    } finally {
      setIsLoadingHistory(false);
      if (isInitial) {
        setIsInitialLoad(false);
      }
    }
  };

  // 初始加载历史
  useEffect(() => {
    if (isInitialLoad) {
      loadChatHistory(0, true);
    }
  }, [sessionId]);

  // 监听滚动，实现下拉加载
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget;
    
    // 滚动到顶部时加载更多
    if (target.scrollTop === 0 && hasMoreHistory && !isLoadingHistory) {
      const previousScrollHeight = target.scrollHeight;
      
      loadChatHistory(historyOffset).then(() => {
        // 保持滚动位置
        requestAnimationFrame(() => {
          const newScrollHeight = target.scrollHeight;
          target.scrollTop = newScrollHeight - previousScrollHeight;
        });
      });
    }
  };

  // WebSocket 连接
  const { sendMessage, isConnected } = useWebSocket('ws://localhost:8001/api/v1/chat/ws', {
    onMessage: (data) => {
      console.log('📨 收到消息:', data);
      
      if (data.type === 'content') {
        // 流式接收回复 - 累积文本
        const text = data.data?.text || '';
        
        setMessages(prev => {
          const last = prev[prev.length - 1];
          
          // 如果最后一条是助手消息且不是欢迎消息，则追加文本
          if (last && last.role === 'assistant' && !last.content.includes('你好！我是道友')) {
            return [
              ...prev.slice(0, -1),
              { ...last, content: last.content + text }
            ];
          } else {
            // 否则创建新消息
            return [...prev, { 
              role: 'assistant', 
              content: text, 
              timestamp: new Date() 
            }];
          }
        });
        
        setIsSpeaking(true);
        setEmotion('happy');
      } else if (data.type === 'done') {
        // 回复完成
        console.log('✅ 回复完成');
        setIsSpeaking(false);
        setEmotion('neutral');
      } else if (data.type === 'error') {
        // 错误处理
        console.error('❌ 服务器错误:', data.error);
        setMessages(prev => [...prev, { 
          role: 'assistant', 
          content: '抱歉，处理您的消息时出现了错误。', 
          timestamp: new Date() 
        }]);
        setIsSpeaking(false);
        setEmotion('neutral');
      }
    }
  });

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 发送消息
  const handleSend = () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setEmotion('thinking');

    // 通过 WebSocket 发送（带 session_id）
    if (isConnected) {
      sendMessage({
        type: 'text',
        user_id: 'user_001',
        session_id: sessionId,  // 使用持久化的 session_id
        input: input
      });
    }

    setInput('');
  };

  // 语音输入
  const handleVoiceInput = () => {
    setIsListening(!isListening);
    // TODO: 实现语音识别
  };

  // 切换静音
  const handleToggleMute = () => {
    setIsMuted(!isMuted);
  };

  // 重置对话（创建新 session）
  const handleReset = () => {
    // 创建新的 session_id
    const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem('session_id', newSessionId);
    
    // 重置所有状态
    setMessages([
      {
        role: 'assistant',
        content: '你好！我是道友，你的智能助手。有什么可以帮助你的吗？',
        timestamp: new Date()
      }
    ]);
    setEmotion('neutral');
    setHistoryOffset(0);
    setHasMoreHistory(true);
    setIsInitialLoad(true);
    
    console.log('🔄 已重置对话，新 session:', newSessionId);
    
    // 刷新页面以使用新 session
    window.location.reload();
  };

  return (
    <Box sx={{ height: '100vh', display: 'flex', bgcolor: '#0a0a0a' } as const}>
      {/* 左侧：3D 数字人 */}
      <Box sx={{ flex: 1, position: 'relative' } as const}>
        <DigitalPersonCanvas 
          emotion={emotion}
          isSpeaking={isSpeaking}
        />
        
        {/* 状态指示器 */}
        <Box sx={{ position: 'absolute', top: 20, left: 20 } as const}>
          <Stack direction="row" spacing={1}>
            <Chip 
              label={isConnected ? '已连接' : '未连接'} 
              color={isConnected ? 'success' : 'error'}
              size="small"
              sx={{ backdropFilter: 'blur(10px)', bgcolor: 'rgba(0,0,0,0.6)' } as const}
            />
            {isSpeaking && (
              <Chip 
                label="正在说话" 
                color="primary"
                size="small"
                icon={<VolumeUp />}
                sx={{ backdropFilter: 'blur(10px)', bgcolor: 'rgba(102, 126, 234, 0.6)' } as const}
              />
            )}
          </Stack>
        </Box>

        {/* 数字人信息卡片 */}
        <Box sx={{ 
          position: 'absolute', 
          bottom: 20, 
          left: 20,
          bgcolor: 'rgba(0,0,0,0.7)',
          backdropFilter: 'blur(20px)',
          borderRadius: 3,
          p: 2.5,
          color: 'white',
          border: '1px solid rgba(255,255,255,0.1)',
          minWidth: 200
        }}>
          <Stack direction="row" spacing={2} alignItems="center">
            <Avatar 
              sx={{ 
                width: 56, 
                height: 56,
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
              }}
            >
              👩
            </Avatar>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
                道友
              </Typography>
              <Typography variant="body2" sx={{ opacity: 0.8, fontSize: '0.875rem' }}>
                你的智能助手
              </Typography>
              <Stack direction="row" spacing={0.5} sx={{ mt: 1 }}>
                <Chip 
                  label="AI" 
                  size="small" 
                  sx={{ 
                    height: 20, 
                    fontSize: '0.7rem',
                    bgcolor: 'rgba(102, 126, 234, 0.2)',
                    color: '#667eea'
                  }} 
                />
                <Chip 
                  label="3D" 
                  size="small" 
                  sx={{ 
                    height: 20, 
                    fontSize: '0.7rem',
                    bgcolor: 'rgba(118, 75, 162, 0.2)',
                    color: '#764ba2'
                  }} 
                />
              </Stack>
            </Box>
          </Stack>
        </Box>

        {/* 提示文字 */}
        <Box sx={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          textAlign: 'center',
          pointerEvents: 'none',
          opacity: messages.length <= 1 ? 0.5 : 0,
          transition: 'opacity 0.3s'
        }}>
          <Typography variant="h5" sx={{ color: 'white', mb: 1, fontWeight: 300 }}>
            👋 欢迎来到 AI 数字人世界
          </Typography>
          <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)' }}>
            开始对话，体验智能交互
          </Typography>
        </Box>
      </Box>

      {/* 右侧：聊天界面 */}
      <Paper 
        elevation={0}
        sx={{ 
          width: 420, 
          display: 'flex', 
          flexDirection: 'column',
          bgcolor: '#1a1a1a',
          borderLeft: '1px solid rgba(255,255,255,0.1)'
        }}
      >
        {/* 标题栏 */}
        <Box sx={{ 
          p: 2.5, 
          borderBottom: '1px solid rgba(255,255,255,0.1)',
          bgcolor: '#0f0f0f',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <Typography variant="h6" sx={{ color: 'white', fontWeight: 600 }}>
            💬 对话记录
          </Typography>
          <IconButton 
            size="small" 
            onClick={handleReset}
            sx={{ color: 'rgba(255,255,255,0.6)' }}
          >
            <Refresh />
          </IconButton>
        </Box>

        {/* 消息列表 */}
        <Box 
          ref={messagesContainerRef}
          onScroll={handleScroll}
          sx={{ 
            flex: 1, 
            overflowY: 'auto', 
            p: 2.5,
            '&::-webkit-scrollbar': {
              width: '6px',
            },
            '&::-webkit-scrollbar-thumb': {
              bgcolor: 'rgba(255,255,255,0.2)',
              borderRadius: '3px',
            }
          }}
        >
          {/* 加载更多提示 */}
          {isLoadingHistory && (
            <Box sx={{ textAlign: 'center', py: 2 }}>
              <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                加载历史消息中...
              </Typography>
            </Box>
          )}
          
          {/* 没有更多历史提示 */}
          {!hasMoreHistory && messages.length > 1 && !isInitialLoad && (
            <Box sx={{ textAlign: 'center', py: 2 }}>
              <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.3)' }}>
                已加载全部历史消息
              </Typography>
            </Box>
          )}
          
          {messages.map((msg, idx) => (
            <Box
              key={idx}
              sx={{
                mb: 2.5,
                display: 'flex',
                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start'
              }}
            >
              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  maxWidth: '85%',
                  background: msg.role === 'user' 
                    ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                    : 'rgba(255,255,255,0.05)',
                  color: 'white',
                  borderRadius: 2.5,
                  wordBreak: 'break-word',
                  border: msg.role === 'assistant' ? '1px solid rgba(255,255,255,0.1)' : 'none'
                }}
              >
                <Typography variant="body1" sx={{ lineHeight: 1.6 }}>
                  {msg.content}
                </Typography>
                <Typography 
                  variant="caption" 
                  sx={{ opacity: 0.6, display: 'block', mt: 1, fontSize: '0.75rem' }}
                >
                  {msg.timestamp.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                </Typography>
              </Paper>
            </Box>
          ))}
          <div ref={messagesEndRef} />
        </Box>

        {/* 输入框 */}
        <Box sx={{ 
          p: 2.5, 
          borderTop: '1px solid rgba(255,255,255,0.1)',
          bgcolor: '#0f0f0f'
        }}>
          <Stack direction="row" spacing={1.5}>
            <TextField
              fullWidth
              multiline
              maxRows={3}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="输入消息... (Enter 发送)"
              variant="outlined"
              sx={{
                '& .MuiOutlinedInput-root': {
                  color: 'white',
                  bgcolor: 'rgba(255,255,255,0.05)',
                  borderRadius: 2,
                  '& fieldset': {
                    borderColor: 'rgba(255,255,255,0.1)',
                  },
                  '&:hover fieldset': {
                    borderColor: 'rgba(255,255,255,0.2)',
                  },
                  '&.Mui-focused fieldset': {
                    borderColor: '#667eea',
                  },
                }
              }}
            />
            <Stack spacing={1}>
              <IconButton 
                onClick={handleVoiceInput}
                sx={{ 
                  color: isListening ? '#667eea' : 'white',
                  bgcolor: isListening ? 'rgba(102, 126, 234, 0.2)' : 'rgba(255,255,255,0.05)',
                  '&:hover': {
                    bgcolor: isListening ? 'rgba(102, 126, 234, 0.3)' : 'rgba(255,255,255,0.1)'
                  }
                }}
              >
                {isListening ? <Mic /> : <MicOff />}
              </IconButton>
              <IconButton 
                onClick={handleToggleMute}
                sx={{ 
                  color: 'white', 
                  bgcolor: 'rgba(255,255,255,0.05)',
                  '&:hover': {
                    bgcolor: 'rgba(255,255,255,0.1)'
                  }
                }}
              >
                {isMuted ? <VolumeOff /> : <VolumeUp />}
              </IconButton>
            </Stack>
            <IconButton 
              onClick={handleSend}
              disabled={!input.trim() || !isConnected}
              sx={{ 
                color: 'white',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                width: 48,
                height: 48,
                '&:hover': {
                  background: 'linear-gradient(135deg, #764ba2 0%, #667eea 100%)',
                },
                '&:disabled': {
                  bgcolor: 'rgba(255,255,255,0.05)',
                  color: 'rgba(255,255,255,0.3)',
                  background: 'none'
                }
              }}
            >
              <Send />
            </IconButton>
          </Stack>
        </Box>
      </Paper>
    </Box>
  );
};

export default DigitalPersonPage;
