import axios from 'axios'

import type {
  AnomalyScore,
  AuditLog,
  CaseRead,
  CaseSummary,
  DashboardStats,
  EvidenceDetail,
  EvidenceListItem,
  EvidenceTimeline,
  Paginated,
  PaginatedEvidence,
  Report,
  TokenResponse,
  User,
} from '../types'

const TOKEN_STORAGE_KEY = 'cctv_access_token'

export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      localStorage.removeItem(TOKEN_STORAGE_KEY)
      if (window.location.pathname !== '/login') {
        window.location.assign('/login')
      }
    }
    return Promise.reject(error)
  },
)

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function storeToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token)
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY)
}

export async function login(
  email: string,
  password: string,
): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>('/auth/login', { email, password })
  return data
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<User>('/auth/me')
  return data
}

export async function listUsers(
  params: { page?: number; page_size?: number } = {},
): Promise<{ items: User[]; page: number; page_size: number; total: number; total_pages: number }> {
  const { data } = await api.get('/users', { params })
  return data
}

export async function createUser(body: {
  name: string
  email: string
  password: string
  role: string
}): Promise<User> {
  const { data } = await api.post<User>('/users', body)
  return data
}

export async function updateUser(
  id: string,
  body: { name?: string; role?: string; password?: string },
): Promise<User> {
  const { data } = await api.patch<User>(`/users/${id}`, body)
  return data
}

export interface EvidenceListParams {
  page?: number
  page_size?: number
  case_id?: string
  status?: string
  search?: string
}

export interface AnalysisStart {
  analysis_type: 'frame_sampling' | 'scene_change'
  sampling_rate?: number
  threshold?: number
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await api.get<DashboardStats>('/dashboard/stats')
  return data
}

export async function listCases(
  params: { page?: number; page_size?: number; search?: string } = {},
): Promise<Paginated<CaseSummary>> {
  const cleanParams = Object.fromEntries(
    Object.entries(params).filter(
      ([, v]) => v !== undefined && v !== null && v !== '',
    ),
  )
  const { data } = await api.get<Paginated<CaseSummary>>('/cases', { params: cleanParams })
  return data
}

export async function getCase(id: string): Promise<CaseRead> {
  const { data } = await api.get<CaseRead>(`/cases/${id}`)
  return data
}

export async function createCase(body: {
  title: string
  description?: string
  case_number?: string
}): Promise<CaseRead> {
  const { data } = await api.post<CaseRead>('/cases', body)
  return data
}

export async function listEvidence(
  params: EvidenceListParams = {},
): Promise<PaginatedEvidence> {
  const cleanParams = Object.fromEntries(
    Object.entries(params).filter(
      ([, v]) => v !== undefined && v !== null && v !== '',
    ),
  )
  const { data } = await api.get<PaginatedEvidence>('/evidence', {
    params: cleanParams,
  })
  return data
}

export async function getEvidence(id: string): Promise<EvidenceDetail> {
  const { data } = await api.get<EvidenceDetail>(`/evidence/${id}`)
  return data
}

export async function listEvidenceAnalyses(id: string): Promise<EvidenceDetail['analyses']> {
  const { data } = await api.get<EvidenceDetail['analyses']>(`/evidence/${id}/analysis`)
  return data
}

export async function deleteEvidence(id: string): Promise<void> {
  await api.delete(`/evidence/${id}`)
}

export async function getEvidenceTimeline(id: string): Promise<EvidenceTimeline> {
  const { data } = await api.get<EvidenceTimeline>(`/evidence/${id}/timeline`)
  return data
}

export async function getEvidenceAnomalyScore(id: string): Promise<AnomalyScore> {
  const { data } = await api.get<AnomalyScore>(`/evidence/${id}/anomaly-score`)
  return data
}

export async function runAnalysis(
  id: string,
  body: AnalysisStart,
): Promise<EvidenceDetail['analyses'][number]> {
  const { data } = await api.post<EvidenceDetail['analyses'][number]>(
    `/evidence/${id}/analyze`,
    body,
  )
  return data
}

export interface MetadataTaskAccepted {
  evidence_id: string
  status: 'queued'
}

export async function extractMetadata(id: string): Promise<MetadataTaskAccepted> {
  const { data } = await api.post<MetadataTaskAccepted>(`/evidence/${id}/metadata`)
  return data
}

export interface AuditLogListParams {
  page?: number
  page_size?: number
  user_id?: string
  entity_type?: string
  action?: string
}

export async function listAuditLogs(
  params: AuditLogListParams = {},
): Promise<Paginated<AuditLog>> {
  const { data } = await api.get<Paginated<AuditLog>>('/audit-logs', { params })
  return data
}

export async function listReports(
  params: { page?: number; page_size?: number; case_id?: string } = {},
): Promise<{ items: Report[]; page: number; page_size: number; total: number; total_pages: number }> {
  const { data } = await api.get<{ items: Report[]; page: number; page_size: number; total: number; total_pages: number }>('/reports', { params })
  return data
}

export async function generateReport(
  body: { case_id: string; evidence_id?: string; comparison_id?: string },
): Promise<Report> {
  const { data } = await api.post<Report>('/reports', body)
  return data
}

export async function downloadReport(
  reportId: string,
): Promise<Blob> {
  const { data } = await api.get<Blob>(`/reports/${reportId}/download`, {
    responseType: 'blob',
  })
  return data
}

export type { EvidenceListItem }
