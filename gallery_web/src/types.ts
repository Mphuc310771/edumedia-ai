export type MediaType = "image" | "audio" | "video" | "other"

export type SmartCategory =
  | "all"
  | "study"
  | "pets"
  | "people"
  | "food"
  | "receipts"
  | "scenes"
  | "videos"
  | "other"

export interface MediaItem {
  id: string
  filename: string
  type: MediaType
  url: string
  thumbnailUrl?: string
  size: string
  date: string
  category: SmartCategory | string
  categoryLabel: string
  labels: string[]
  ocrText?: string
  transcript?: string
  summary: string
  status: string
  tags: string[]
  source: string
  score?: number
  matchedOn?: string[]
  matchedFields?: string[]
  pipeline?: string[]
  error?: string | null
  analysisSource?: string
  subject?: string
  subjectLabel?: string
  transcript_s3_uri?: string
  has_extended_transcript?: boolean
  transcriptS3Uri?: string
  hasExtendedTranscript?: boolean
  is_demo_protected?: boolean
  isDemoProtected?: boolean
}

export const OFF_MAJOR_SUBJECTS = new Set([
  "english",
  "physics",
  "chemistry",
  "biology",
  "economics",
  "law",
  "philosophy",
  "pe",
  "off_major",
  "finance",
  "accounting",
  "marketing",
  "logistics",
  "management",
  "medicine",
  "pharmacy",
  "nursing",
  "public_health",
  "media",
  "psychology",
  "mechanical",
  "electrical",
  "construction",
  "pedagogy",
])

export function isOffMajorSubject(subject?: string) {
  return Boolean(subject && OFF_MAJOR_SUBJECTS.has(subject))
}

export type DisciplineId =
  | "it"
  | "business"
  | "healthcare"
  | "social_law"
  | "engineering"
  | "natural_sciences"
  | "general"

export interface SearchPlan {
  keywords: string[]
  media_type: string | null
  category: string | null
  subject?: string | null
  rationale: string
  planner_source?: "bedrock" | "bedrock_throttled" | "bedrock_rate_limited" | "bedrock_error" | "heuristic" | string
  embedding_source?: string
}

export interface AgentQueryResponse {
  user_query: string
  execution_status: string
  plan: SearchPlan
  results: MediaItem[]
}

export interface HealthResponse {
  status: string
  provider: string
  environment?: string
  ingest_mode?: "sync" | "event"
  components?: Record<string, string>
  component_errors?: Record<string, string>
  message?: string
}
