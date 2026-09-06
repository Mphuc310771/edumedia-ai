import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { listMedia, queryMedia } from "../api/client"
import { isOffMajorSubject, MediaItem, SearchPlan, SmartCategory } from "../types"

/** Bỏ dấu tiếng Việt + thường hóa để so khớp không phân biệt dấu. */
function fold(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "d")
    .toLowerCase()
}

function localHaystack(item: MediaItem): string {
  return fold(
    [
      item.filename,
      item.subjectLabel || "",
      item.categoryLabel || "",
      (item.tags || []).join(" "),
      (item.labels || []).join(" "),
      item.summary || "",
      item.ocrText || "",
      item.transcript || "",
    ].join(" "),
  )
}

/**
 * Hai tầng tìm kiếm:
 * - Gõ chữ → lọc cục bộ tức thì (0ms, không gọi mạng) trên tên tệp, môn, nhãn, OCR, transcript.
 * - Nhấn Enter → hỏi agent AI (Bedrock planner + hybrid search) phía server.
 */
export function useMediaCatalog(
  activeCategory: SmartCategory,
  activeSubject: string,
  searchQuery: string,
  enabled = true,
) {
  const [allItems, setAllItems] = useState<MediaItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [aiResults, setAiResults] = useState<MediaItem[] | null>(null)
  const [aiQuery, setAiQuery] = useState("")
  const [aiLoading, setAiLoading] = useState(false)
  const [plan, setPlan] = useState<SearchPlan | null>(null)
  const reloadTimer = useRef<number | null>(null)

  const reload = useCallback(async () => {
    if (!enabled) {
      setAllItems([])
      setLoading(false)
      setError(null)
      return
    }
    setError(null)
    try {
      const data = await listMedia()
      setAllItems(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không gọi được API")
    } finally {
      setLoading(false)
    }
  }, [enabled])

  useEffect(() => {
    setLoading(true)
    void reload()
  }, [reload])

  // Còn tệp đang phân tích (kể cả từ event mode / máy khác) → tự làm mới nhẹ nhàng
  useEffect(() => {
    const hasIndexing = allItems.some((item) => item.status === "INDEXING")
    if (!hasIndexing) return
    reloadTimer.current = window.setTimeout(() => void reload(), 5000)
    return () => {
      if (reloadTimer.current) window.clearTimeout(reloadTimer.current)
    }
  }, [allItems, reload])

  const clearAi = useCallback(() => {
    setAiResults(null)
    setAiQuery("")
    setPlan(null)
  }, [])

  const runAiSearch = useCallback(async (query: string) => {
    const q = query.trim()
    if (!q) return
    setAiLoading(true)
    setError(null)
    try {
      const result = await queryMedia(q)
      setAiResults(result.results)
      setPlan(result.plan)
      setAiQuery(q)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Tìm kiếm AI thất bại")
    } finally {
      setAiLoading(false)
    }
  }, [])

  // Người dùng sửa ô tìm kiếm sau khi đã hỏi AI → quay về chế độ lọc cục bộ
  useEffect(() => {
    if (aiQuery && searchQuery.trim() !== aiQuery) clearAi()
  }, [searchQuery, aiQuery, clearAi])

  const aiActive = aiResults !== null

  const items = useMemo(() => {
    const base = aiActive ? (aiResults as MediaItem[]) : allItems

    const structural = base.filter((item) => {
      const catOk = activeCategory === "all" || item.category === activeCategory
      const subOk =
        activeSubject === "all" ||
        item.subject === activeSubject ||
        (activeSubject === "off_major" && isOffMajorSubject(item.subject))
      return catOk && subOk
    })

    const q = searchQuery.trim()
    if (aiActive || !q) return structural

    const tokens = fold(q).split(/\s+/).filter(Boolean)
    if (tokens.length === 0) return structural
    return structural.filter((item) => {
      const haystack = localHaystack(item)
      return tokens.every((token) => haystack.includes(token))
    })
  }, [aiActive, aiResults, allItems, activeCategory, activeSubject, searchQuery])

  return {
    items,
    allItems,
    loading,
    aiLoading,
    error,
    plan,
    planRationale: plan?.rationale || "",
    aiActive,
    runAiSearch,
    clearAi,
    reload,
  }
}
