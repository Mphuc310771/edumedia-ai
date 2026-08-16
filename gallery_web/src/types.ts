export type MediaType = "image" | "audio" | "video" | "other"

export type SmartCategory =
  | "all"
  | "study"
  | "pets"
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
}

export interface AgentQueryResponse {
  user_query: string
  execution_status: string
  plan: {
    keywords: string[]
    media_type: string | null
    category: string | null
    rationale: string
  }
  results: MediaItem[]
}
