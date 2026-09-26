export interface Paginated<T> {
  items: T[]
  page: number
  page_size: number
  total: number
  total_pages: number
}

export type CaseStatus = 'open' | 'closed' | 'archived'
export type EvidenceStatus =
  | 'uploaded'
  | 'hashed'
  | 'metadata_extracted'
  | 'analyzed'
  | 'archived'
  | 'deleted'
export type AnalysisType =
  | 'hashing'
  | 'metadata'
  | 'video_structure'
  | 'frame_sampling'
  | 'scene_change'
  | 'comparison'
export type AnalysisStatus = 'queued' | 'processing' | 'completed' | 'failed'
export type UserRole = 'admin' | 'investigator' | 'viewer'

export interface User {
  id: string
  name: string
  email: string
  role: UserRole
  created_at: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface PaginatedUsers {
  items: User[]
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface CaseSummary {
  id: string
  case_number: string
  title: string
  description: string | null
  status: CaseStatus
  investigator_id: string | null
  created_at: string
}

export interface CaseRead {
  id: string
  case_number: string
  title: string
  description: string | null
  status: CaseStatus
  investigator_id: string | null
  created_at: string
  updated_at: string
}

export interface EvidenceListItem {
  id: string
  evidence_number: string
  case_id: string
  case_number: string | null
  case_title: string | null
  original_filename: string
  file_size: number
  mime_type: string
  sha256: string | null
  status: EvidenceStatus
  uploaded_at: string
}

export interface PaginatedEvidence {
  items: EvidenceListItem[]
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface VideoMetadata {
  evidence_id: string
  container_format: string | null
  duration: number | null
  width: number | null
  height: number | null
  frame_rate: number | null
  frame_count: number | null
  video_codec: string | null
  audio_codec: string | null
  bitrate: number | null
  pixel_format: string | null
  stream_count: number | null
  creation_time: string | null
  encoder: string | null
  analyzed_at: string
}

export interface Analysis {
  id: string
  evidence_id: string
  analysis_type: AnalysisType
  status: AnalysisStatus
  params: Record<string, unknown>
  started_at: string | null
  completed_at: string | null
  error_message: string | null
  // Compact counts derived server-side, present on list endpoints. `result` is
  // only returned by the detail endpoint because it embeds every event's
  // per-frame metrics, which is far too heavy to send per list row.
  summary?: Record<string, unknown> | null
  result?: Record<string, unknown> | null
}

export interface EvidenceDetail {
  id: string
  case_id: string
  evidence_number: string
  original_filename: string
  file_size: number
  mime_type: string
  sha256: string | null
  sha512: string | null
  hash_calculated_at: string | null
  status: EvidenceStatus
  uploaded_by: string
  uploaded_at: string
  video_metadata: VideoMetadata | null
  analyses: Analysis[]
}

export interface AuditLog {
  id: string
  user_id: string | null
  action: string
  entity_type: string
  entity_id: string | null
  timestamp: string
  ip_address: string | null
  user_agent: string | null
  details: Record<string, unknown>
}

export interface DashboardStats {
  cases: { total: number; open: number; closed: number; archived: number }
  evidence: {
    total: number
    total_size: number
    by_status: Record<EvidenceStatus, number>
  }
  analyses: { total: number; completed: number; pending: number; failed: number }
  recent_evidence: EvidenceListItem[]
  recent_activity: AuditLog[]
}

export type TimelineSegmentKind = 'normal' | 'anomaly'

export interface TimelineSegment {
  kind: TimelineSegmentKind
  start: number
  end: number
  severity: string | null
  event_index: number | null
}

export interface TimelineEvent {
  timestamp: number
  severity: string
  detection_method: string
  diff_score: number
  prev_frame: number | null
  current_frame: number | null
  metrics: Record<string, number>
  analysis_id: string
  analysis_type: AnalysisType
}

export interface EvidenceTimeline {
  evidence_id: string
  duration: number | null
  analysis_id: string | null
  analysis_status: AnalysisStatus | null
  segments: TimelineSegment[]
  events: TimelineEvent[]
}

export type AnomalyCategory = 'low' | 'moderate' | 'high' | 'very_high'

export interface ScoringFactor {
  name: string
  label: string
  max_points: number
  points: number
  reason: string
}

export interface AnomalyScore {
  evidence_id: string
  analysis_id: string | null
  score: number | null
  category: AnomalyCategory | null
  factors: ScoringFactor[]
  computed_at: string | null
}

export interface Report {
  id: string
  case_id: string
  evidence_id: string | null
  comparison_id: string | null
  generated_by: string
  generated_at: string
  case_number: string | null
  evidence_number: string | null
}
