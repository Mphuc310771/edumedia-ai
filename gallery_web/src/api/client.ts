import axios from "axios"
import { AgentQueryResponse, HealthResponse, MediaItem } from "../types"

const API_BASE = (
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_BASE ||
  ""
).replace(/\/$/, "")
const DEFAULT_API_KEY = (import.meta.env.VITE_API_KEY || "").trim()
const TOKEN_KEY = "agentsys_token"

export function hasDefaultApiKey(): boolean {
  return Boolean(DEFAULT_API_KEY)
}

export function getSessionToken(): string {
  try {
    return sessionStorage.getItem(TOKEN_KEY) || ""
  } catch {
    return ""
  }
}

export function setSessionToken(token: string) {
  sessionStorage.setItem(TOKEN_KEY, token)
}

export function clearSession() {
  sessionStorage.removeItem(TOKEN_KEY)
}

function headers(): HeadersInit {
  const value: Record<string, string> = { "Content-Type": "application/json" }
  const token = getSessionToken()
  if (token) {
    value.Authorization = `Bearer ${token}`
  }
  if (DEFAULT_API_KEY) {
    value["X-API-Key"] = DEFAULT_API_KEY
  }
  return value
}

function notifyUnauthorized() {
  clearSession()
  window.dispatchEvent(new Event("agentsys-unauthorized"))
}

async function readOk(response: Response): Promise<Response> {
  if (response.status === 401) {
    notifyUnauthorized()
    throw new Error(await parseError(response))
  }
  if (!response.ok) throw new Error(await parseError(response))
  return response
}

function resolveUrl(pathOrUrl: string): string {
  if (pathOrUrl.startsWith("http://") || pathOrUrl.startsWith("https://")) return pathOrUrl
  return `${API_BASE}${pathOrUrl}`
}

async function parseError(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body.detail === "string") return body.detail
    if (Array.isArray(body.detail)) return body.detail.map((item: { msg?: string }) => item.msg).join("; ")
    return body.message || response.statusText
  } catch {
    return response.statusText
  }
}

export async function login(username: string, password: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  })
  if (!response.ok) throw new Error(await parseError(response))
  const body = (await response.json()) as { token: string }
  setSessionToken(body.token)
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`)
  const body = await response.json().catch(() => ({}))
  if (!response.ok && !body.provider) throw new Error("Health check failed")
  return body as HealthResponse
}

export async function listMedia(): Promise<MediaItem[]> {
  const response = await readOk(await fetch(`${API_BASE}/api/v1/media/items`, { headers: headers() }))
  return response.json()
}

export async function fetchContentUrl(fileId: string): Promise<{ url: string; thumbnailUrl?: string }> {
  const response = await readOk(
    await fetch(`${API_BASE}/api/v1/media/items/${fileId}/url`, { headers: headers() }),
  )
  return response.json()
}

export async function queryMedia(userQuery: string): Promise<AgentQueryResponse> {
  const response = await readOk(
    await fetch(`${API_BASE}/api/v1/media/agent/query`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ user_query: userQuery }),
    }),
  )
  return response.json()
}

export async function requestUploadUrl(filename: string, contentType: string, sizeBytes?: number) {
  const payload: Record<string, unknown> = {
    filename,
    content_type: contentType || "application/octet-stream",
  }
  if (typeof sizeBytes === "number") {
    payload.size_bytes = sizeBytes
  }
  let response = await fetch(`${API_BASE}/api/upload-url`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(payload),
  })
  if (response.status === 404) {
    response = await fetch(`${API_BASE}/api/v1/media/upload-url`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify(payload),
    })
  }
  const okResp = await readOk(response)
  return okResp.json() as Promise<{
    file_id: string
    presigned_url: string
    upload_url?: string
    object_key: string
  }>
}

export async function putPresigned(
  url: string,
  file: File,
  contentType?: string,
  onProgress?: (percent: number) => void,
): Promise<void> {
  const targetUrl = resolveUrl(url)
  const ct = contentType || file.type || "application/octet-stream"
  try {
    await axios.put(targetUrl, file, {
      headers: {
        "Content-Type": ct,
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percent)
        }
      },
    })
  } catch (err: unknown) {
    if (axios.isAxiosError(err)) {
      const status = err.response?.status
      throw new Error(`Upload thất bại (${status || "lỗi mạng"}). Kiểm tra CORS bucket S3.`)
    }
    throw err
  }
}

export async function fetchRawTranscript(fileId: string): Promise<any> {
  const response = await readOk(
    await fetch(`${API_BASE}/api/v1/media/items/${fileId}/transcript-raw`, { headers: headers() }),
  )
  return response.json()
}

export async function triggerProcess(payload: {
  file_id: string
  object_key: string
  filename: string
  content_type: string
}): Promise<{ file_id: string; status: string; error?: string | null }> {
  const response = await readOk(
    await fetch(`${API_BASE}/api/v1/media/process`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify(payload),
    }),
  )
  return response.json()
}

export async function fetchStatus(fileId: string): Promise<{ file_id: string; status: string; error?: string | null }> {
  const response = await readOk(
    await fetch(`${API_BASE}/api/v1/media/status/${fileId}`, { headers: headers() }),
  )
  return response.json()
}

export async function reprocessMedia(fileId: string): Promise<{ file_id: string; status: string }> {
  const response = await readOk(
    await fetch(`${API_BASE}/api/v1/media/reprocess/${fileId}`, {
      method: "POST",
      headers: headers(),
    }),
  )
  return response.json()
}

export async function deleteMedia(fileId: string): Promise<void> {
  await readOk(
    await fetch(`${API_BASE}/api/v1/media/${fileId}`, {
      method: "DELETE",
      headers: headers(),
    }),
  )
}

export async function clearAllMedia(): Promise<void> {
  await readOk(
    await fetch(`${API_BASE}/api/v1/media/clear`, {
      method: "DELETE",
      headers: headers(),
    }),
  )
}
