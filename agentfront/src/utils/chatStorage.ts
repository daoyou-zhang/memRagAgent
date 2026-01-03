/**
 * 聊天历史存储工具
 * 
 * 使用 localStorage 持久化聊天记录
 */

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

const STORAGE_KEY = 'chatHistory';
const MAX_MESSAGES = 100; // 最多保存 100 条消息

/**
 * 加载聊天历史
 */
export const loadChatHistory = (): Message[] => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      // 转换 timestamp 字符串回 Date 对象
      return parsed.map((msg: any) => ({
        ...msg,
        timestamp: new Date(msg.timestamp)
      }));
    }
  } catch (error) {
    console.error('❌ 加载聊天历史失败:', error);
  }
  
  // 返回默认欢迎消息
  return getWelcomeMessage();
};

/**
 * 保存聊天历史
 */
export const saveChatHistory = (messages: Message[]): void => {
  try {
    // 限制保存的消息数量
    const messagesToSave = messages.slice(-MAX_MESSAGES);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messagesToSave));
    console.log(`💾 已保存 ${messagesToSave.length} 条聊天记录`);
  } catch (error) {
    console.error('❌ 保存聊天历史失败:', error);
    
    // 如果存储空间不足，尝试清理旧消息
    if (error instanceof DOMException && error.name === 'QuotaExceededError') {
      console.warn('⚠️ 存储空间不足，清理旧消息...');
      const reducedMessages = messages.slice(-50); // 只保留最近 50 条
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(reducedMessages));
        console.log(`💾 已保存 ${reducedMessages.length} 条聊天记录（已清理）`);
      } catch (retryError) {
        console.error('❌ 清理后仍然保存失败:', retryError);
      }
    }
  }
};

/**
 * 清除聊天历史
 */
export const clearChatHistory = (): void => {
  try {
    localStorage.removeItem(STORAGE_KEY);
    console.log('🗑️ 聊天历史已清除');
  } catch (error) {
    console.error('❌ 清除聊天历史失败:', error);
  }
};

/**
 * 重置为欢迎消息
 */
export const resetChatHistory = (): Message[] => {
  const welcomeMessage = getWelcomeMessage();
  saveChatHistory(welcomeMessage);
  return welcomeMessage;
};

/**
 * 获取欢迎消息
 */
export const getWelcomeMessage = (): Message[] => {
  return [
    {
      role: 'assistant',
      content: '你好！我是道友，你的智能助手。有什么可以帮助你的吗？',
      timestamp: new Date()
    }
  ];
};

/**
 * 导出聊天历史为 JSON 文件
 */
export const exportChatHistory = (messages: Message[]): void => {
  try {
    const dataStr = JSON.stringify(messages, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `chat-history-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    
    URL.revokeObjectURL(url);
    console.log('📥 聊天历史已导出');
  } catch (error) {
    console.error('❌ 导出聊天历史失败:', error);
  }
};

/**
 * 导入聊天历史
 */
export const importChatHistory = (file: File): Promise<Message[]> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    
    reader.onload = (e) => {
      try {
        const content = e.target?.result as string;
        const parsed = JSON.parse(content);
        
        // 验证数据格式
        if (!Array.isArray(parsed)) {
          throw new Error('无效的聊天历史格式');
        }
        
        const messages: Message[] = parsed.map((msg: any) => ({
          role: msg.role,
          content: msg.content,
          timestamp: new Date(msg.timestamp)
        }));
        
        saveChatHistory(messages);
        console.log('📤 聊天历史已导入');
        resolve(messages);
      } catch (error) {
        console.error('❌ 导入聊天历史失败:', error);
        reject(error);
      }
    };
    
    reader.onerror = () => {
      reject(new Error('读取文件失败'));
    };
    
    reader.readAsText(file);
  });
};

/**
 * 获取聊天统计信息
 */
export const getChatStats = (messages: Message[]): {
  totalMessages: number;
  userMessages: number;
  assistantMessages: number;
  firstMessageTime: Date | null;
  lastMessageTime: Date | null;
} => {
  return {
    totalMessages: messages.length,
    userMessages: messages.filter(m => m.role === 'user').length,
    assistantMessages: messages.filter(m => m.role === 'assistant').length,
    firstMessageTime: messages.length > 0 ? messages[0].timestamp : null,
    lastMessageTime: messages.length > 0 ? messages[messages.length - 1].timestamp : null
  };
};
