import { useEffect, useMemo, useState } from "react"
import { listMedia, queryMedia } from "../api/client"
import { MediaItem, SmartCategory } from "../types"

export function useMediaCatalog(activeCategory: SmartCategory, searchQuery: string) {
  const [items, setItems] = useState<MediaItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [planRationale, setPlanRationale] = useState<string>("")
  const [planKeywords, setPlanKeywords] = useState<string[]>([])

  const reload = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await listMedia()
      setItems(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không gọi được API")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void reload()
  }, [])

  useEffect(() => {
    const q = searchQuery.trim()
    if (!q) {
      setPlanRationale("")
      setPlanKeywords([])
      void reload()
      return
    }
    const handle = window.setTimeout(async () => {
      setLoading(true)
      setError(null)
      try {
        const result = await queryMedia(q)
        setItems(result.results)
        setPlanRationale(result.plan.rationale)
        setPlanKeywords(result.plan.keywords || [])
      } catch (err) {
        setError(err instanceof Error ? err.message : "Query thất bại")
      } finally {
        setLoading(false)
      }
    }, 350)
    return () => window.clearTimeout(handle)
  }, [searchQuery])

  const visible = useMemo(() => {
    if (activeCategory === "all") return items
    return items.filter((item) => item.category === activeCategory)
  }, [items, activeCategory])

  return { items: visible, allItems: items, loading, error, planRationale, planKeywords, reload }
}
