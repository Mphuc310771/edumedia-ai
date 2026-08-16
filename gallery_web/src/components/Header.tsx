import React, { useRef, useState } from "react"
import { Sparkles, Upload, Search, X, CheckCircle2 } from "lucide-react"

interface HeaderProps {
  provider?: string
  searchQuery: string
  onSearchChange: (query: string) => void
  onUploaded: (count: number) => void
  onUploadFiles: (files: File[]) => Promise<void>
  searchInputRef?: React.RefObject<HTMLInputElement>
}

export const Header: React.FC<HeaderProps> = ({
  provider = "memory",
  searchQuery,
  onSearchChange,
  onUploaded,
  onUploadFiles,
  searchInputRef,
}) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const localSearchRef = useRef<HTMLInputElement | null>(null)
  const actualSearchRef = searchInputRef || localSearchRef

  const [uploading, setUploading] = useState(false)
  const [uploadCount, setUploadCount] = useState(0)
  const [uploadSuccess, setUploadSuccess] = useState(false)

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return
    const fileList = Array.from(files)
    setUploading(true)
    setUploadCount(fileList.length)
    try {
      await onUploadFiles(fileList)
      setUploadSuccess(true)
      onUploaded(fileList.length)
      setTimeout(() => {
        setUploadSuccess(false)
        setUploadCount(0)
      }, 2500)
    } finally {
      setUploading(false)
    }
  }

  const isAws = provider === "aws"

  return (
    <header className="sticky top-0 z-40 glass-header px-6 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-2.5 shrink-0">
          <div className="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-emerald-400" />
          </div>
          <span className="font-bold text-base text-white tracking-tight">AgentSys</span>
          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-mono border ${
              isAws
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                : "bg-white/5 text-slate-400 border-white/10"
            }`}
          >
            {isAws ? "AWS Cloud" : "Local GPU"}
          </span>
        </div>

        {/* Integrated Center Search Bar */}
        <div className="flex-1 max-w-lg">
          <div className="flex items-center bg-white/[0.04] hover:bg-white/[0.07] rounded-xl border border-white/10 px-3.5 py-1.5 gap-2.5 transition-all focus-within:border-emerald-500/50 focus-within:bg-[#080D1A]">
            <Search className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <input
              ref={actualSearchRef}
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Tìm kiếm: bài giảng, hóa đơn, thú cưng..."
              style={{ border: "none", outline: "none", background: "transparent", boxShadow: "none" }}
              className="w-full text-slate-200 placeholder-slate-500 text-xs"
            />
            {searchQuery ? (
              <button
                onClick={() => onSearchChange("")}
                className="text-slate-400 hover:text-white p-0.5 rounded transition-colors shrink-0"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            ) : (
              <kbd className="hidden sm:inline-block text-[10px] font-mono text-slate-500 bg-white/5 border border-white/10 px-1.5 py-0.5 rounded shrink-0">
                /
              </kbd>
            )}
          </div>
        </div>

        {/* Action Button */}
        <div className="shrink-0">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            style={{ display: "none" }}
            className="hidden"
            accept="image/*,audio/*,video/*"
            onChange={(event) => {
              void handleFiles(event.target.files)
              event.target.value = ""
            }}
          />

          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className={`px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all ${
              uploadSuccess
                ? "bg-emerald-600 text-white"
                : "bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold"
            }`}
          >
            {uploading ? (
              <>
                <div className="w-3 h-3 border-2 border-slate-950 border-t-transparent rounded-full animate-spin"></div>
                <span>Đang xử lý {uploadCount > 1 ? `${uploadCount} tệp...` : "..."}</span>
              </>
            ) : uploadSuccess ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-white" />
                <span>Đã thêm!</span>
              </>
            ) : (
              <>
                <Upload className="w-3.5 h-3.5" />
                <span>Tải Media lên</span>
              </>
            )}
          </button>
        </div>
      </div>
    </header>
  )
}
