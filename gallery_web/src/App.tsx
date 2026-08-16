import React, { useEffect, useRef, useState } from "react"
import { Header } from "./components/Header"
import { CategoryTabs } from "./components/CategoryTabs"
import { MediaCard } from "./components/MediaCard"
import { MediaDetailModal } from "./components/MediaDetailModal"
import { useMediaCatalog } from "./hooks/useMediaCatalog"
import { fetchHealth, uploadMedia, uploadMultipleMedia, deleteMedia, clearAllMedia } from "./api/client"
import { MediaItem, SmartCategory } from "./types"
import { Search, Sparkles, AlertCircle, RefreshCw, CheckCircle2, Trash2, UploadCloud, Cpu, Mic, Brain } from "lucide-react"

export default function App() {
  const [activeCategory, setActiveCategory] = useState<SmartCategory>("all")
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedItem, setSelectedItem] = useState<MediaItem | null>(null)
  const [provider, setProvider] = useState("memory")
  const [toastMessage, setToastMessage] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const searchInputRef = useRef<HTMLInputElement | null>(null)
  const dropzoneInputRef = useRef<HTMLInputElement | null>(null)

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

  const handleUploadFiles = async (files: File[]) => {
    if (files.length === 0) return
    if (files.length === 1) {
      await uploadMedia(files[0])
    } else {
      await uploadMultipleMedia(files)
    }
    await reload()
    triggerToast(files.length > 1 ? `Đã thêm ${files.length} tệp!` : "Đã thêm tệp thành công!")
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
                <span className="flex items-center gap-1 text-emerald-400 font-medium">
                  <RefreshCw className="w-3 h-3 animate-spin" />
                  Đang tìm...
                </span>
              )}
            </div>

            <div className="flex items-center gap-3">
              {searchQuery && planRationale && (
                <span className="text-[11px] text-slate-400 truncate max-w-sm">
                  {planRationale}
                </span>
              )}
              <button
                onClick={() => void handleClearAll()}
                className="text-[11px] text-slate-500 hover:text-rose-400 flex items-center gap-1 transition-colors"
                title="Xóa toàn bộ kho media"
              >
                <Trash2 className="w-3 h-3" />
                <span>Dọn sạch</span>
              </button>
            </div>
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div className="glass-panel rounded-2xl p-4 mb-5 text-xs text-amber-300 border border-amber-500/30 flex items-center gap-3">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
            <div>
              <strong>Lỗi kết nối API:</strong> {error}. Hãy đảm bảo backend đang chạy tại port 8000.
            </div>
          </div>
        )}

        {/* Empty State vs Media Grid */}
        {items.length === 0 && !loading ? (
          <div className="py-12 flex flex-col items-center justify-center">
            {searchQuery ? (
              <div className="glass-panel rounded-3xl p-12 text-center max-w-md mx-auto border border-white/10 shadow-2xl">
                <Search className="w-8 h-8 text-slate-500 mx-auto mb-3" />
                <h3 className="text-sm font-bold text-slate-200 mb-1">Không tìm thấy kết quả</h3>
                <p className="text-xs text-slate-400 mb-5">
                  Không có tệp nào khớp với "{searchQuery}". Thử từ khóa ngắn gọn hơn.
                </p>
                <button
                  onClick={() => setSearchQuery("")}
                  className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-semibold transition-all"
                >
                  Xóa tìm kiếm
                </button>
              </div>
            ) : (
              /* Premium Dropzone */
              <div className="w-full flex flex-col items-center">
                <div
                  onDragOver={(e) => {
                    e.preventDefault()
                    setIsDragging(true)
                  }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={handleDrop}
                  onClick={() => dropzoneInputRef.current?.click()}
                  className={`dropzone-container ${isDragging ? "dragging" : ""}`}
                >
                  <input
                    ref={dropzoneInputRef}
                    type="file"
                    multiple
                    style={{ display: "none" }}
                    accept="image/*,audio/*,video/*"
                    onChange={(e) => {
                      if (e.target.files) void handleUploadFiles(Array.from(e.target.files))
                      e.target.value = ""
                    }}
                  />
                  <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mx-auto mb-4 shadow-lg shadow-emerald-950/30">
                    <UploadCloud className="w-7 h-7" />
                  </div>
                  <h2 className="text-base font-bold text-white mb-1.5">
                    Kéo thả tệp Media vào đây
                  </h2>
                  <p className="text-xs text-slate-400 mb-4">
                    hoặc <span className="text-emerald-400 font-semibold underline">chọn tệp từ máy tính</span> của bạn
                  </p>
                  <span className="inline-block text-[11px] font-mono text-slate-400 bg-white/5 border border-white/10 px-3 py-1 rounded-lg">
                    Hỗ trợ: JPG, PNG, MP3, WAV, MP4
                  </span>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {items.map((item) => (
              <MediaCard key={item.id} item={item} onClick={() => setSelectedItem(item)} />
            ))}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 py-3.5 px-6 text-center text-[11px] text-slate-500 font-mono">
        <p>AgentSys AI Studio • First Cloud AI Journey (FCAJ)</p>
      </footer>

      {/* Detail Modal */}
      {selectedItem && (
        <MediaDetailModal
          item={selectedItem}
          onClose={() => setSelectedItem(null)}
          onDelete={async (fileId) => {
            await deleteMedia(fileId)
            await reload()
            triggerToast("Đã xóa tệp!")
          }}
        />
      )}
    </div>
  )
}
