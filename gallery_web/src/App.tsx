import React, { useEffect, useMemo, useRef, useState } from "react"
import { Sidebar } from "./components/Sidebar"
import { TopBar } from "./components/TopBar"
import { Toolbar } from "./components/Toolbar"
import { PlanBanner } from "./components/PlanBanner"
import { EmptyState } from "./components/EmptyState"
import { MediaCard } from "./components/MediaCard"
import { MediaListRow } from "./components/MediaListRow"
import { MediaDetailModal } from "./components/MediaDetailModal"
import { ProcessingConsole } from "./components/ProcessingConsole"
import { DevPanel } from "./components/DevPanel"
import { useMediaCatalog } from "./hooks/useMediaCatalog"
import { useUploadQueue } from "./hooks/useUploadQueue"
import { fetchHealth, deleteMedia, clearAllMedia, getSessionToken, clearSession } from "./api/client"
import { LoginScreen } from "./components/LoginScreen"
import { parseSize, SortMode, ViewMode } from "./catalog"
import { HealthResponse, MediaItem, SmartCategory } from "./types"
import { AlertCircle, CheckCircle2, CheckSquare, SearchX, Trash2, UploadCloud, X } from "lucide-react"

export default function App() {
  const [authed, setAuthed] = useState(() => Boolean(getSessionToken()))
  const [activeCategory, setActiveCategory] = useState<SmartCategory>("all")
  const [activeSubject, setActiveSubject] = useState("all")
  const [searchQuery, setSearchQuery] = useState("")
  const [sort, setSort] = useState<SortMode>("newest")
  const [view, setView] = useState<ViewMode>("grid")
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectMode, setSelectMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [statusOpen, setStatusOpen] = useState(false)
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [toastMessage, setToastMessage] = useState<string | null>(null)
  const [isDraggingFile, setIsDraggingFile] = useState(false)
  const [consoleOpen, setConsoleOpen] = useState(false)
  const searchInputRef = useRef<HTMLInputElement | null>(null)
  const dragCounter = useRef(0)

  const {
    items,
    allItems,
    loading,
    aiLoading,
    error,
    plan,
    planRationale,
    aiActive,
    runAiSearch,
    clearAi,
    reload,
  } = useMediaCatalog(activeCategory, activeSubject, searchQuery, authed)

  const triggerToast = (msg: string) => {
    setToastMessage(msg)
    setTimeout(() => setToastMessage(null), 3200)
  }

  const { tasks, enqueue, retryIngest, busy } = useUploadQueue(
    () => void reload(),
    (ok, total) => triggerToast(ok ? `Đã xử lý xong ${ok}/${total} tệp` : "Không xử lý được tệp nào"),
  )

  const handleUploadFiles = (files: File[]) => {
    if (files.length === 0) return
    enqueue(files)
    setConsoleOpen(true)
  }

  const handleRetry = (item: MediaItem) => {
    void retryIngest(item.id, item.filename)
    setConsoleOpen(true)
    triggerToast(`Đang phân tích lại ${item.filename}`)
  }

  useEffect(() => {
    const load = () =>
      fetchHealth()
        .then(setHealth)
        .catch(() => setHealth({ status: "OFFLINE", provider: "offline", components: { api: "OFFLINE" } }))
    load()
    const timer = window.setInterval(load, 300000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    const onUnauthorized = () => setAuthed(false)
    window.addEventListener("agentsys-unauthorized", onUnauthorized)
    return () => window.removeEventListener("agentsys-unauthorized", onUnauthorized)
  }, [])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (
        (event.key === "/" || (event.key === "k" && (event.metaKey || event.ctrlKey))) &&
        document.activeElement?.tagName !== "INPUT" &&
        document.activeElement?.tagName !== "TEXTAREA"
      ) {
        event.preventDefault()
        searchInputRef.current?.focus()
      }
      if (event.key === "Escape" && !selectedId) {
        setSelectMode(false)
        setSelectedIds(new Set())
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [selectedId])

  // Kéo-thả tệp ở bất kỳ đâu trên màn hình
  useEffect(() => {
    const hasFiles = (event: DragEvent) => Array.from(event.dataTransfer?.types || []).includes("Files")
    const onDragEnter = (event: DragEvent) => {
      if (!hasFiles(event)) return
      event.preventDefault()
      dragCounter.current += 1
      setIsDraggingFile(true)
    }
    const onDragOver = (event: DragEvent) => {
      if (hasFiles(event)) event.preventDefault()
    }
    const onDragLeave = (event: DragEvent) => {
      if (!hasFiles(event)) return
      dragCounter.current = Math.max(0, dragCounter.current - 1)
      if (dragCounter.current === 0) setIsDraggingFile(false)
    }
    const onDrop = (event: DragEvent) => {
      if (!hasFiles(event)) return
      event.preventDefault()
      dragCounter.current = 0
      setIsDraggingFile(false)
      if (!authed) return
      const files = Array.from(event.dataTransfer?.files || [])
      if (files.length) handleUploadFiles(files)
    }
    window.addEventListener("dragenter", onDragEnter)
    window.addEventListener("dragover", onDragOver)
    window.addEventListener("dragleave", onDragLeave)
    window.addEventListener("drop", onDrop)
    return () => {
      window.removeEventListener("dragenter", onDragEnter)
      window.removeEventListener("dragover", onDragOver)
      window.removeEventListener("dragleave", onDragLeave)
      window.removeEventListener("drop", onDrop)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authed])

  // Kết quả AI giữ thứ tự liên quan; thoát AI thì quay về mới nhất
  useEffect(() => {
    setSort((current) => {
      if (aiActive && (current === "newest" || current === "oldest")) return "relevance"
      if (!aiActive && current === "relevance") return "newest"
      return current
    })
  }, [aiActive])

  const sortedItems = useMemo(() => {
    const list = [...items]
    switch (sort) {
      case "newest":
        return list.sort((a, b) => (b.date || "").localeCompare(a.date || ""))
      case "oldest":
        return list.sort((a, b) => (a.date || "").localeCompare(b.date || ""))
      case "name":
        return list.sort((a, b) => a.filename.localeCompare(b.filename, "vi"))
      case "size":
        return list.sort((a, b) => parseSize(b.size) - parseSize(a.size))
      default:
        return list // relevance: giữ thứ tự server trả về
    }
  }, [items, sort])

  const selectedIndex = useMemo(
    () => (selectedId ? sortedItems.findIndex((item) => item.id === selectedId) : -1),
    [selectedId, sortedItems],
  )

  const handleClearAll = async () => {
    if (!confirm("Xóa toàn bộ thư viện? Hành động này không thể hoàn tác.")) return
    await clearAllMedia()
    await reload()
    triggerToast("Đã dọn sạch thư viện")
  }

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const exitSelectMode = () => {
    setSelectMode(false)
    setSelectedIds(new Set())
  }

  const handleDeleteSelected = async () => {
    const ids = Array.from(selectedIds)
    if (ids.length === 0) return
    if (!confirm(`Xóa ${ids.length} tệp đã chọn?`)) return
    const results = await Promise.allSettled(ids.map((id) => deleteMedia(id)))
    const okCount = results.filter((result) => result.status === "fulfilled").length
    await reload()
    exitSelectMode()
    triggerToast(`Đã xóa ${okCount}/${ids.length} tệp`)
  }

  const handleSelectCategory = (category: SmartCategory) => {
    setActiveCategory(category)
    setActiveSubject("all")
    setSidebarOpen(false)
  }

  const handleSelectSubject = (subject: string) => {
    setActiveSubject(subject)
    setActiveCategory("all")
    setSidebarOpen(false)
  }

  const resetFilters = () => {
    setActiveCategory("all")
    setActiveSubject("all")
    setSearchQuery("")
    clearAi()
  }

  const handleLogout = () => {
    clearSession()
    setAuthed(false)
  }

  const hasLibrary = allItems.length > 0
  const filtered = Boolean(searchQuery.trim()) || activeCategory !== "all" || activeSubject !== "all"

  if (!authed) {
    return <LoginScreen onSuccess={() => setAuthed(true)} />
  }

  return (
    <div className="min-h-screen">
      {/* Lớp phủ khi kéo tệp vào màn hình */}
      {isDraggingFile && (
        <div className="pointer-events-none fixed inset-0 z-[70] flex items-center justify-center bg-ink-950/85 backdrop-blur-sm animate-fade-in">
          <div className="flex flex-col items-center gap-4 rounded-3xl border-2 border-dashed border-violet-400/60 bg-violet-500/10 px-16 py-12">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-sky-400 shadow-glow">
              <UploadCloud className="h-8 w-8 text-white" />
            </div>
            <p className="text-xl font-bold text-white">Thả tệp để tải lên</p>
            <p className="text-sm text-slate-400">Ảnh, ghi âm hoặc video bài giảng</p>
          </div>
        </div>
      )}

      {toastMessage && (
        <div className="fixed bottom-6 left-1/2 z-[65] flex -translate-x-1/2 items-center gap-2.5 rounded-2xl border border-white/10 bg-ink-800/95 px-5 py-3 text-sm font-medium text-white shadow-pop backdrop-blur-xl animate-slide-up">
          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          {toastMessage}
        </div>
      )}

      <ProcessingConsole isOpen={consoleOpen} onClose={() => setConsoleOpen(false)} tasks={tasks} />

      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        items={allItems}
        activeCategory={activeCategory}
        activeSubject={activeSubject}
        onSelectCategory={handleSelectCategory}
        onSelectSubject={handleSelectSubject}
        health={health}
        onOpenStatus={() => setStatusOpen(true)}
        onLogout={handleLogout}
      />

      {statusOpen && <DevPanel health={health} onClose={() => setStatusOpen(false)} />}

      <div className="flex min-h-screen flex-col lg:pl-[280px]">
        <TopBar
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onSubmitAi={() => void runAiSearch(searchQuery)}
          aiLoading={aiLoading}
          aiActive={aiActive}
          searchInputRef={searchInputRef}
          onUploadFiles={handleUploadFiles}
          uploading={busy}
          onOpenMenu={() => setSidebarOpen(true)}
        />

        <main className="mx-auto flex w-full max-w-[1600px] flex-1 flex-col px-4 pb-10 pt-5 sm:px-6 lg:px-8">
          {aiActive && planRationale && <PlanBanner plan={plan} rationale={planRationale} onClear={clearAi} />}

          {error && (
            <div className="mb-5 flex items-center gap-2.5 rounded-2xl border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-200 animate-fade-in">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}

          {hasLibrary && (
            <Toolbar
              activeCategory={activeCategory}
              activeSubject={activeSubject}
              searchQuery={searchQuery}
              count={sortedItems.length}
              loading={loading || aiLoading}
              sort={sort}
              onSortChange={setSort}
              view={view}
              onViewChange={setView}
              aiActive={aiActive}
              selectMode={selectMode}
              onToggleSelectMode={() => (selectMode ? exitSelectMode() : setSelectMode(true))}
              onRefresh={() => void reload()}
              onClearAll={() => void handleClearAll()}
            />
          )}

          {!hasLibrary && !loading && <EmptyState onFiles={handleUploadFiles} />}

          {loading && !hasLibrary && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
              {Array.from({ length: 10 }).map((_, i) => (
                <div key={i} className="skeleton aspect-[4/3]" style={{ animationDelay: `${i * 60}ms` }} />
              ))}
            </div>
          )}

          {hasLibrary && sortedItems.length === 0 && !loading && (
            <div className="flex flex-1 flex-col items-center justify-center gap-4 py-20 text-center animate-fade-in">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl surface text-slate-500">
                <SearchX className="h-6 w-6" />
              </div>
              <div>
                <p className="text-lg font-bold text-white">Không tìm thấy tệp phù hợp</p>
                <p className="mx-auto mt-1.5 max-w-md text-sm text-slate-400">
                  {searchQuery.trim()
                    ? "Thử từ khóa khác, hoặc nhấn Enter để tìm sâu bằng AI theo ngữ nghĩa."
                    : "Thử chọn danh mục hoặc môn học khác."}
                </p>
              </div>
              {filtered && (
                <button type="button" onClick={resetFilters} className="btn-ghost surface">
                  Xóa mọi bộ lọc
                </button>
              )}
            </div>
          )}

          {sortedItems.length > 0 && view === "grid" && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
              {sortedItems.map((item, index) => (
                <MediaCard
                  key={item.id}
                  item={item}
                  index={index}
                  selectMode={selectMode}
                  selected={selectedIds.has(item.id)}
                  onClick={() => (selectMode ? toggleSelect(item.id) : setSelectedId(item.id))}
                  onRetry={() => handleRetry(item)}
                />
              ))}
            </div>
          )}

          {sortedItems.length > 0 && view === "list" && (
            <div className="overflow-hidden rounded-2xl surface">
              {sortedItems.map((item, index) => (
                <MediaListRow
                  key={item.id}
                  item={item}
                  index={index}
                  selectMode={selectMode}
                  selected={selectedIds.has(item.id)}
                  onClick={() => (selectMode ? toggleSelect(item.id) : setSelectedId(item.id))}
                />
              ))}
            </div>
          )}
        </main>

        <footer className="border-t border-white/[0.05] py-4 text-center text-xs text-slate-600">
          AgentSys · First Cloud AI Journey · AWS Serverless
        </footer>
      </div>

      {/* Thanh hành động khi đang chọn nhiều */}
      {selectMode && (
        <div className="fixed bottom-6 left-1/2 z-[60] flex -translate-x-1/2 items-center gap-2 rounded-2xl border border-white/10 bg-ink-800/95 p-2 pl-4 shadow-pop backdrop-blur-xl animate-slide-up">
          <span className="text-sm font-semibold text-white">
            {selectedIds.size} đã chọn
          </span>
          <button
            type="button"
            onClick={() => setSelectedIds(new Set(sortedItems.map((item) => item.id)))}
            className="btn-ghost"
          >
            <CheckSquare className="h-4 w-4" />
            Chọn tất cả
          </button>
          <button
            type="button"
            onClick={() => void handleDeleteSelected()}
            disabled={selectedIds.size === 0}
            className="inline-flex items-center gap-1.5 rounded-xl bg-rose-500/90 px-3.5 py-2 text-sm font-bold text-white transition hover:bg-rose-500 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Trash2 className="h-4 w-4" />
            Xóa
          </button>
          <button type="button" onClick={exitSelectMode} className="btn-ghost" aria-label="Thoát chế độ chọn">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {selectedIndex >= 0 && (
        <MediaDetailModal
          items={sortedItems}
          index={selectedIndex}
          onClose={() => setSelectedId(null)}
          onNavigate={(delta) => {
            const next = sortedItems[selectedIndex + delta]
            if (next) setSelectedId(next.id)
          }}
          onDelete={async (id) => {
            await deleteMedia(id)
            setSelectedId(null)
            await reload()
            triggerToast("Đã xóa tệp")
          }}
          onRetry={(item) => {
            setSelectedId(null)
            handleRetry(item)
          }}
        />
      )}
    </div>
  )
}
