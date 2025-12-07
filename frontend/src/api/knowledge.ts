import { http } from './http'

export type KnowledgeCollection = {
  id: number
  project_id: string | null
  name: string
  domain: string
  description?: string | null
  default_language?: string | null
  extra_metadata?: unknown
  created_at: string
  updated_at: string
}

export type KnowledgeDocument = {
  id: number
  collection_id: number
  external_id?: string | null
  title: string
  source_uri?: string | null
  extra_metadata?: unknown
  status: string
  created_at: string
  updated_at: string
}

export type KnowledgeChunk = {
  id: number
  document_id: number
  chunk_index: number
  section_label?: string | null
  text: string
  tags?: unknown
  importance?: number | null
  metadata?: unknown
}

export type CreateCollectionPayload = {
  project_id?: string
  name: string
  domain: string
  description?: string
  default_language?: string
  metadata?: unknown
}

export type CreateDocumentPayload = {
  collection_id: number
  external_id?: string
  title: string
  source_uri?: string
  metadata?: unknown
}

export async function listCollections(params?: {
  project_id?: string
  domain?: string
}): Promise<{ items: KnowledgeCollection[] }> {
  const query = new URLSearchParams()
  if (params?.project_id) query.set('project_id', params.project_id)
  if (params?.domain) query.set('domain', params.domain)
  const qs = query.toString()
  const url = '/api/knowledge/collections' + (qs ? `?${qs}` : '')
  return http.get<{ items: KnowledgeCollection[] }>(url)
}

export async function createCollection(
  payload: CreateCollectionPayload,
): Promise<KnowledgeCollection> {
  return http.post<KnowledgeCollection>('/api/knowledge/collections', payload)
}

export async function listDocuments(params?: {
  collection_id?: number
  status?: string
}): Promise<{ items: KnowledgeDocument[] }> {
  const query = new URLSearchParams()
  if (params?.collection_id) query.set('collection_id', String(params.collection_id))
  if (params?.status) query.set('status', params.status)
  const qs = query.toString()
  const url = '/api/knowledge/documents' + (qs ? `?${qs}` : '')
  return http.get<{ items: KnowledgeDocument[] }>(url)
}

export async function createDocument(
  payload: CreateDocumentPayload,
): Promise<KnowledgeDocument> {
  return http.post<KnowledgeDocument>('/api/knowledge/documents', payload)
}

export async function deleteDocument(documentId: number): Promise<{
  document_id: number
  deleted_chunks: number
  status: string
}> {
  return http.delete<{ document_id: number; deleted_chunks: number; status: string }>(
    `/api/knowledge/documents/${documentId}`,
  )
}

export async function indexDocument(documentId: number): Promise<{
  document_id: number
  chunk_count: number
  status: string
}> {
  return http.post<{ document_id: number; chunk_count: number; status: string }>(
    `/api/knowledge/documents/${documentId}/index`,
    {},
  )
}

export async function listChunks(documentId: number): Promise<{
  items: KnowledgeChunk[]
}> {
  return http.get<{ items: KnowledgeChunk[] }>(`/api/knowledge/documents/${documentId}/chunks`)
}

export async function resetCollection(collectionId: number): Promise<{
  collection_id: number
  deleted_documents: number
  deleted_chunks: number
  status: string
}> {
  return http.post<{
    collection_id: number
    deleted_documents: number
    deleted_chunks: number
    status: string
  }>(`/api/knowledge/collections/${collectionId}/reset`, {})
}
