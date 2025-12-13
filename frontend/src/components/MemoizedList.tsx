/**
 * 可复用的列表组件，使用 React.memo 优化性能
 */
import React, { memo, useCallback } from 'react'

// ============================================================
// 记忆项组件
// ============================================================

interface MemoryItemProps {
  id: number
  text: string
  type: string
  importance?: number
  createdAt?: string
  tags?: string[]
  onDelete?: (id: number) => void
}

export const MemoryItem = memo(function MemoryItem({
  id,
  text,
  type,
  importance,
  createdAt,
  tags,
  onDelete,
}: MemoryItemProps) {
  const handleDelete = useCallback(() => {
    onDelete?.(id)
  }, [id, onDelete])

  return (
    <div className="card" style={{ marginBottom: '0.75rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
          <div style={{ marginBottom: '0.5rem' }}>
            <span className="badge" style={{ marginRight: '0.5rem' }}>{type}</span>
            {importance !== undefined && (
              <span className="badge badge-secondary">
                重要性: {(importance * 100).toFixed(0)}%
              </span>
            )}
          </div>
          <p style={{ margin: '0.5rem 0', lineHeight: 1.6 }}>{text}</p>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            {createdAt && <span>创建于: {new Date(createdAt).toLocaleString()}</span>}
            {tags && tags.length > 0 && (
              <span style={{ marginLeft: '1rem' }}>标签: {tags.join(', ')}</span>
            )}
          </div>
        </div>
        {onDelete && (
          <button
            onClick={handleDelete}
            className="btn-danger"
            style={{ marginLeft: '1rem', padding: '0.25rem 0.5rem', fontSize: '0.8rem' }}
          >
            删除
          </button>
        )}
      </div>
    </div>
  )
})

// ============================================================
// 知识文档项组件
// ============================================================

interface DocumentItemProps {
  id: number
  title: string
  status: string
  chunkCount?: number
  createdAt?: string
  onIndex?: (id: number) => void
  onDelete?: (id: number) => void
}

export const DocumentItem = memo(function DocumentItem({
  id,
  title,
  status,
  chunkCount,
  createdAt,
  onIndex,
  onDelete,
}: DocumentItemProps) {
  const handleIndex = useCallback(() => {
    onIndex?.(id)
  }, [id, onIndex])

  const handleDelete = useCallback(() => {
    onDelete?.(id)
  }, [id, onDelete])

  return (
    <div className="card" style={{ marginBottom: '0.75rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <strong>{title}</strong>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            状态: <span className={`badge ${status === 'indexed' ? 'badge-success' : ''}`}>{status}</span>
            {chunkCount !== undefined && <span style={{ marginLeft: '1rem' }}>分块: {chunkCount}</span>}
            {createdAt && <span style={{ marginLeft: '1rem' }}>{new Date(createdAt).toLocaleDateString()}</span>}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {onIndex && status !== 'indexed' && (
            <button onClick={handleIndex} style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }}>
              索引
            </button>
          )}
          {onDelete && (
            <button onClick={handleDelete} className="btn-danger" style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }}>
              删除
            </button>
          )}
        </div>
      </div>
    </div>
  )
})

// ============================================================
// 图谱实体项组件
// ============================================================

interface EntityItemProps {
  name: string
  type: string
  isCenter?: boolean
  onClick?: (name: string) => void
}

export const EntityItem = memo(function EntityItem({
  name,
  type,
  isCenter,
  onClick,
}: EntityItemProps) {
  const handleClick = useCallback(() => {
    onClick?.(name)
  }, [name, onClick])

  return (
    <div
      className={`card ${isCenter ? 'card-highlight' : ''}`}
      style={{
        marginBottom: '0.5rem',
        cursor: onClick ? 'pointer' : 'default',
        borderLeft: isCenter ? '3px solid var(--primary-color)' : undefined,
      }}
      onClick={onClick ? handleClick : undefined}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <span className="badge">{type}</span>
        <strong>{name}</strong>
        {isCenter && <span className="badge badge-secondary">中心节点</span>}
      </div>
    </div>
  )
})

// ============================================================
// 任务项组件
// ============================================================

interface JobItemProps {
  id: number
  jobType: string
  status: string
  sessionId?: string
  createdAt?: string
  onRun?: (id: number) => void
}

export const JobItem = memo(function JobItem({
  id,
  jobType,
  status,
  sessionId,
  createdAt,
  onRun,
}: JobItemProps) {
  const handleRun = useCallback(() => {
    onRun?.(id)
  }, [id, onRun])

  const statusColor = {
    pending: 'badge-warning',
    running: 'badge-info',
    completed: 'badge-success',
    failed: 'badge-danger',
  }[status] || ''

  return (
    <div className="card" style={{ marginBottom: '0.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <span className="badge" style={{ marginRight: '0.5rem' }}>{jobType}</span>
          <span className={`badge ${statusColor}`}>{status}</span>
          {sessionId && (
            <span style={{ marginLeft: '1rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {sessionId.substring(0, 20)}...
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {createdAt && (
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {new Date(createdAt).toLocaleString()}
            </span>
          )}
          {onRun && status === 'pending' && (
            <button onClick={handleRun} style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }}>
              执行
            </button>
          )}
        </div>
      </div>
    </div>
  )
})

// ============================================================
// 通用列表包装器
// ============================================================

interface ListWrapperProps<T> {
  items: T[]
  renderItem: (item: T, index: number) => React.ReactNode
  keyExtractor: (item: T) => string | number
  emptyText?: string
  loading?: boolean
}

export function MemoizedList<T>({
  items,
  renderItem,
  keyExtractor,
  emptyText = '暂无数据',
  loading,
}: ListWrapperProps<T>) {
  if (loading) {
    return <div className="loading">加载中...</div>
  }

  if (items.length === 0) {
    return (
      <div className="empty-state">
        <p>{emptyText}</p>
      </div>
    )
  }

  return (
    <div>
      {items.map((item, index) => (
        <React.Fragment key={keyExtractor(item)}>
          {renderItem(item, index)}
        </React.Fragment>
      ))}
    </div>
  )
}

export default MemoizedList
