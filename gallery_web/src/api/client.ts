import { AgentQueryResponse, MediaItem } from "../types"

const API_BASE = (import.meta.env.VITE_API_BASE || "").replace(/\/$/, "")
const API_KEY = import.meta.env.VITE_API_KEY || ""

function headers(): HeadersInit {
  const value: Record<string, string> = { "Content-Type": "application/json" }
  if (API_KEY) value["X-API-Key"] = API_KEY
  return value
}

async function parseError(response: Response): Promise<string> {
  try {
    const body = await response.json()
    return body.detail || body.message || response.statusText
  } catch {
    return response.statusText
  }
}

export async function fetchHealth(): Promise<{ status: string; provider: string }> {
  const response = await fetch(`${API_BASE}/health`)
  if (!response.ok) throw new Error("Health check failed")
  return response.json()
}

export async function listMedia(): Promise<MediaItem[]> {
  const response = await fetch(`${API_BASE}/api/v1/media/items`, { headers: headers() })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function queryMedia(userQuery: string): Promise<AgentQueryResponse> {
  const response = await fetch(`${API_BASE}/api/v1/media/agent/query`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ user_query: userQuery }),
  })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function uploadMedia(file: File): Promise<MediaItem> {
  const form = new FormData()
  form.append("file", file)
  const response = await fetch(`${API_BASE}/api/v1/media/upload`, {
    method: "POST",
    headers: API_KEY ? { "X-API-Key": API_KEY } : undefined,
    body: form,
  })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function uploadMultipleMedia(files: File[]): Promise<MediaItem[]> {
  const form = new FormData()
  for (const file of files) {
    form.append("files", file)
  }
  const response = await fetch(`${API_BASE}/api/v1/media/upload-batch`, {
    method: "POST",
    headers: API_KEY ? { "X-API-Key": API_KEY } : undefined,
    body: form,
  })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function deleteMedia(fileId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1/media/${fileId}`, {
    method: "DELETE",
    headers: headers(),
  })
  if (!response.ok) throw new Error(await parseError(response))
}

export async function clearAllMedia(): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1/media/clear`, {
    method: "DELETE",
    headers: headers(),
  })
  if (!response.ok) throw new Error(await parseError(response))
}

