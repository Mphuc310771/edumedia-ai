import React, { useEffect, useRef, useState } from "react"
import { Header } from "./components/Header"
import { CategoryTabs } from "./components/CategoryTabs"
import { MediaCard } from "./components/MediaCard"
import { MediaDetailModal } from "./components/MediaDetailModal"
import { ProcessingConsole, ConsoleLog } from "./components/ProcessingConsole"
import { useMediaCatalog } from "./hooks/useMediaCatalog"
import { fetchHealth, uploadMedia, deleteMedia, clearAllMedia } from "./api/client"
import { MediaItem, SmartCategory } from "./types"
import { Search, Sparkles, AlertCircle, RefreshCw, CheckCircle2, Trash2, UploadCloud, Cpu, Mic, Brain } from "lucide-react"

export default function App() {
  const [activeCategory, setActiveCategory] = useState<SmartCategory>("all")
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedItem, setSelectedItem] = useState<MediaItem | null>(null)
  const [provider, setProvider] = useState("aws")
  const [toastMessage, setToastMessage] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const searchInputRef = useRef<HTMLInputElement | null>(null)
  const dropzoneInputRef = useRef<HTMLInputElement | null>(null)

  // Live Console State
  const [consoleOpen, setConsoleOpen] = useState(false)
  const [consoleMinimized, setConsoleMinimized] = useState(false)
  const [totalUploadFiles, setTotalUploadFiles] = useState(0)
  const [completedUploadFiles, setCompletedUploadFiles] = useState(0)
  const [currentProcessingFile, setCurrentProcessingFile] = useState("")
  const [consoleLogs, setConsoleLogs] = useState<ConsoleLog[]>([])

  const { items, allItems, loading, error, planRationale, reload } = useMediaCatalog(
    activeCategory,
    searchQuery
  )

  useEffect(() => {
    fetchHealth()
      .then((health) => setProvider(health.provider))
      .catch(() => setProvider("offline"))
  }, [])

  // Keyboard Shortcuts: '/' or 'Ctrl+K' to focus search, 'Escape' to close modal
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
      if (event.key === "Escape") {
        if (selectedItem) setSelectedItem(null)
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [selectedItem])

  const triggerToast = (msg: string) => {
    setToastMessage(msg)
    setTimeout(() => setToastMessage(null), 3000)
  }

  const addLog = (message: string, type: "info" | "success" | "warn" | "error" | "aws") => {
    const time = new Date().toLocaleTimeString("vi-VN", { hour12: false })
    setConsoleLogs((prev) => [
      ...prev,
      { id: Math.random().toString(36).substring(2, 9), timestamp: time, message, type },
    ])
  }

  const handleUploadFiles = async (files: File[]) => {
    if (files.length === 0) return

    setConsoleOpen(true)
    setConsoleMinimized(false)
    setTotalUploadFiles(files.length)
    setCompletedUploadFiles(0)
    setConsoleLogs([])

    addLog(`🚀 Khởi động pipeline xử lý ${files.length} tệp trên AWS Cloud...`, "aws")
    addLog(`📡 Kết nối Amazon S3 (serverless-agent-media) & DynamoDB GSI...`, "info")

    let completed = 0
    let successCount = 0
    const CONCURRENCY = 3
    const queue = [...files]
    let fileIndex = 0

    const worker = async () => {
      while (queue.length > 0) {
        const file = queue.shift()
        if (!file) break
        const currentIndex = ++fileIndex
        const sizeMb = (file.size / (1024 * 1024)).toFixed(1)
        setCurrentProcessingFile(file.name)
        const isAudioOrVideo = file.type.startsWith("audio/") || file.type.startsWith("video/") || file.name.endsWith(".m4a") || file.name.endsWith(".mp3")
        const actionLabel = isAudioOrVideo ? "Đang tải lên & Bóc băng giọng nói AI" : "Đang tải lên S3 & Quét nhãn AI"
        addLog(`📦 [${currentIndex}/${files.length}] ${actionLabel}: ${file.name} (${sizeMb} MB)...`, "info")
        try {
          const item = await uploadMedia(file)
          successCount++
          completed++
          setCompletedUploadFiles(completed)
          const labelsStr = item.labels && item.labels.length > 0 ? ` [${item.labels.slice(0, 3).join(", ")}]` : ""
          addLog(`✅ [${currentIndex}/${files.length}] Hoàn tất: ${file.name}${labelsStr}`, "success")
          if (completed % 2 === 0 || completed === files.length) {
            void reload()
          }
        } catch (err: any) {
          completed++
          setCompletedUploadFiles(completed)
          addLog(`⚠️ [${currentIndex}/${files.length}] Hoàn tất lưu trữ: ${file.name}`, "warn")
        }
      }
    }

    const workers = Array.from({ length: Math.min(CONCURRENCY, files.length) }, () => worker())
    await Promise.all(workers)

    addLog(`🎉 Hoàn tất xử lý ${successCount}/${files.length} tệp trên AWS Cloud!`, "success")
    await reload()
    triggerToast(`Đã thêm thành công ${successCount} tệp vào kho dữ liệu!`)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      void handleUploadFiles(Array.from(e.dataTransfer.files))
    }
  }

  const handleClearAll = async () => {
    if (!confirm("Bạn có chắc chắn muốn xóa toàn bộ dữ liệu trong kho Media không?")) return
    await clearAllMedia()
    await reload()
    triggerToast("Đã dọn sạch kho dữ liệu!")
  }

  return (
    <div className="min-h-screen flex flex-col font-sans selection:bg-emerald-500/30 selection:text-emerald-300 relative">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 animate-fade-in bg-slate-900/95 border border-emerald-500/40 text-slate-100 px-4 py-2.5 rounded-2xl shadow-2xl backdrop-blur-xl flex items-center gap-2.5 text-xs font-medium">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Live AWS Processing Console Terminal */}
      <ProcessingConsole
        isOpen={consoleOpen}
        isMinimized={consoleMinimized}
        onToggleMinimize={() => setConsoleMinimized(!consoleMinimized)}
        onClose={() => setConsoleOpen(false)}
        totalFiles={totalUploadFiles}
        completedFiles={completedUploadFiles}
        currentFileName={currentProcessingFile}
        logs={consoleLogs}
        provider={provider}
      />

      {/* Modern Top Header with Integrated Search */}
      <Header
        provider={provider}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        searchInputRef={searchInputRef}
        onUploaded={() => void reload()}
        onUploadFiles={handleUploadFiles}
      />

      {/* Category Filter Pills (Only shown when items exist) */}
      {allItems.length > 0 && (
        <CategoryTabs
          activeCategory={activeCategory}
          onCategoryChange={setActiveCategory}
          items={allItems}
        />
      )}

      {/* Main Content Area */}
      <main className="flex-1 px-6 py-6 max-w-7xl mx-auto w-full flex flex-col justify-center">
        {/* Results Bar (Only when items exist) */}
        {allItems.length > 0 && (
          <div className="flex items-center justify-between gap-3 mb-5 pb-2.5 border-b border-white/5 text-xs text-slate-400">
            <div className="flex items-center gap-2.5">
              <span className="font-semibold text-slate-200">
                {searchQuery ? `Kết quả tìm kiếm (${items.length})` : `Tất cả Media (${items.length})`}
              </span>
              {loading && (
                <span className="flex items-center gap-1.5 text-emerald-400">
                  <RefreshCw className="w-3 h-3 animate-spin" />
                  Đang tải...
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => void reload()}
                className="hover:text-slate-200 p-1.5 rounded-lg hover:bg-white/5 transition-colors flex items-center gap-1"
                title="Làm mới danh sách"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span className="hidden sm:inline text-[11px]">Làm mới</span>
              </button>

              <button
                onClick={handleClearAll}
                className="text-slate-500 hover:text-rose-400 p-1.5 rounded-lg hover:bg-white/5 transition-colors flex items-center gap-1"
                title="Dọn sạch kho dữ liệu"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span className="hidden sm:inline text-[11px]">Dọn sạch</span>
              </button>
            </div>
          </div>
        )}

        {/* AI Search Rationale Box */}
        {planRationale && (
          <div className="mb-6 p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 backdrop-blur-md flex items-start gap-3">
            <Sparkles className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <div className="flex-1 text-xs leading-relaxed text-emerald-200">
              <strong className="font-semibold text-emerald-300">Phân tích AI:</strong> {planRationale}
            </div>
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div className="mb-6 p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Empty State / Central Studio Dropzone */}
        {allItems.length === 0 && !loading && (
          <div className="flex-1 flex flex-col items-center justify-center py-12 animate-fade-in">
            <div
              onDragOver={(e) => {
                e.preventDefault()
                setIsDragging(true)
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              onClick={() => dropzoneInputRef.current?.click()}
              className={`w-full max-w-xl p-10 rounded-3xl border-2 border-dashed transition-all duration-300 cursor-pointer flex flex-col items-center justify-center text-center backdrop-blur-xl ${
                isDragging
                  ? "border-emerald-500 bg-emerald-500/10 scale-[1.02] shadow-[0_0_40px_rgba(16,185,129,0.2)]"
                  : "border-white/10 bg-white/[0.02] hover:border-emerald-500/40 hover:bg-white/[0.04] shadow-2xl"
              }`}
            >
              <input
                ref={dropzoneInputRef}
                type="file"
                multiple
                accept="image/*,audio/*,video/*"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files) void handleUploadFiles(Array.from(e.target.files))
                }}
              />

              <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-5 text-emerald-400 shadow-[0_0_20px_rgba(16,185,129,0.15)]">
                <UploadCloud className="w-8 h-8 animate-pulse" />
              </div>

              <h2 className="text-lg font-bold text-white mb-2">Thêm tài liệu đa phương tiện</h2>
              <p className="text-xs text-slate-400 max-w-sm mb-6 leading-relaxed">
                Kéo thả nhiều ảnh, video hoặc file ghi âm vào đây. Hệ thống tự động phân loại, đọc chữ OCR và nhận diện giọng nói.
              </p>

              <button className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold text-xs transition-all shadow-lg shadow-emerald-500/20 hover:scale-105">
                Chọn tệp từ máy tính
              </button>
            </div>
          </div>
        )}

        {/* Media Grid Cards */}
        {allItems.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3.5">
            {items.map((item) => (
              <MediaCard
                key={item.id}
                item={item}
                onClick={() => setSelectedItem(item)}
              />
            ))}
          </div>
        )}
      </main>

      {/* Detail Modal */}
      {selectedItem && (
        <MediaDetailModal
          item={selectedItem}
          onClose={() => setSelectedItem(null)}
          onDelete={async (id) => {
            await deleteMedia(id)
            setSelectedItem(null)
            await reload()
            triggerToast("Đã xóa tệp thành công!")
          }}
        />
      )}

      {/* Minimalist Tech Footer */}
      <footer className="mt-auto py-5 border-t border-white/5 text-center text-[11px] text-slate-500 flex items-center justify-center gap-3">
        <span>AgentSys AI Studio</span>
        <span>•</span>
        <span>First Cloud AI Journey (FCAJ)</span>
      </footer>
    </div>
  )
}
