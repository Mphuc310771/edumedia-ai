import React, { useRef } from "react"
import { CornerDownLeft, Loader2, Menu, Search, Sparkles, Upload, X } from "lucide-react"
import { SmartCategory } from "../types"

export interface QuickPrompt {
  label: string
  query: string
  category?: SmartCategory
}

export const QUICK_PROMPTS: QuickPrompt[] = [
  { label: "📐 Đề thi Giải tích", query: "đề thi giải tích môn toán", category: "study" },
  { label: "📝 Slide bài giảng môn Lý", query: "slide bài giảng vật lý", category: "study" },
  { label: "🐱 Nhận diện động vật", query: "ảnh thú cưng chó mèo", category: "pets" },
  { label: "🧾 Hóa đơn thanh toán", query: "hóa đơn thanh toán biên lai", category: "receipts" },
  { label: "🎙️ Thầy dặn thi cuối kỳ", query: "đoạn ghi âm thầy dặn thi cuối kỳ", category: "study" },
]

interface TopBarProps {
  searchQuery: string
  onSearchChange: (query: string) => void
  onSubmitAi: () => void
  onSelectPrompt?: (query: string, category?: SmartCategory) => void
  aiLoading: boolean
  aiActive: boolean
  searchInputRef?: React.RefObject<HTMLInputElement | null>
  onUploadFiles: (files: File[]) => void
  uploading: boolean
  onOpenMenu: () => void
}

export const TopBar: React.FC<TopBarProps> = ({
  searchQuery,
  onSearchChange,
  onSubmitAi,
  onSelectPrompt,
  aiLoading,
  aiActive,
  searchInputRef,
  onUploadFiles,
  uploading,
  onOpenMenu,
}) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const localRef = useRef<HTMLInputElement | null>(null)
  const inputRef = (searchInputRef || localRef) as React.RefObject<HTMLInputElement>

  return (
    <header className="sticky top-0 z-30 border-b border-white/[0.06] bg-ink-950/80 px-4 py-3 backdrop-blur-xl sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-[1600px] flex-col gap-2.5">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onOpenMenu}
            className="rounded-xl p-2 text-slate-400 transition hover:bg-white/[0.06] hover:text-white lg:hidden"
            aria-label="Mở menu"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="min-w-0 flex-1">
            <div
              className={`group flex items-center gap-2.5 rounded-2xl border px-3.5 py-2.5 transition focus-within:bg-ink-900 focus-within:shadow-glow ${
                aiActive
                  ? "border-violet-400/50 bg-violet-500/[0.06]"
                  : "border-white/[0.08] bg-white/[0.04] focus-within:border-violet-400/50"
              }`}
            >
              {aiLoading ? (
                <Loader2 className="h-4 w-4 shrink-0 animate-spin text-violet-300" />
              ) : aiActive ? (
                <Sparkles className="h-4 w-4 shrink-0 text-violet-300" />
              ) : (
                <Search className="h-4 w-4 shrink-0 text-slate-500 transition group-focus-within:text-violet-300" />
              )}
              <input
                ref={inputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => onSearchChange(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && searchQuery.trim()) {
                    e.preventDefault()
                    onSubmitAi()
                  }
                }}
                placeholder="Gõ để lọc tức thì · Enter để hỏi AI: đoạn thầy dặn thi cuối kỳ..."
                className="w-full bg-transparent text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none"
              />
              {searchQuery ? (
                <span className="flex shrink-0 items-center gap-1.5">
                  {!aiActive && !aiLoading && (
                    <button
                      type="button"
                      onClick={onSubmitAi}
                      className="hidden items-center gap-1 rounded-lg border border-violet-400/25 bg-violet-500/15 px-2 py-1 text-[11px] font-bold text-violet-200 transition hover:bg-violet-500/30 sm:flex"
                      title="Tìm sâu bằng AI (Bedrock)"
                    >
                      <Sparkles className="h-3 w-3" />
                      Hỏi AI
                      <CornerDownLeft className="h-3 w-3 opacity-70" />
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => onSearchChange("")}
                    className="rounded-lg p-1 text-slate-500 transition hover:bg-white/10 hover:text-white"
                    aria-label="Xóa tìm kiếm"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </span>
              ) : (
                <span className="hidden items-center gap-1.5 sm:flex">
                  <span className="flex items-center gap-1 rounded-md border border-violet-400/20 bg-violet-500/10 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-violet-300">
                    <Sparkles className="h-3 w-3" />
                    AI
                  </span>
                  <kbd className="rounded-md border border-white/10 bg-white/[0.06] px-1.5 py-0.5 font-mono text-[11px] text-slate-500">
                    /
                  </kbd>
                </span>
              )}
            </div>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            accept="image/*,audio/*,video/*"
            onChange={(event) => {
              if (event.target.files?.length) onUploadFiles(Array.from(event.target.files))
              event.target.value = ""
            }}
          />
          <button type="button" onClick={() => fileInputRef.current?.click()} className="btn-primary shrink-0">
            {uploading ? (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/90 border-t-transparent" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            <span className="hidden sm:inline">{uploading ? "Đang xử lý" : "Tải lên"}</span>
          </button>
        </div>

        {/* Quick Prompt Chips */}
        <div className="flex items-center gap-2 overflow-x-auto pb-0.5 text-xs no-scrollbar">
          <span className="shrink-0 text-[11px] font-semibold text-slate-500">Gợi ý câu hỏi:</span>
          {QUICK_PROMPTS.map((p) => (
            <button
              key={p.label}
              type="button"
              onClick={() => onSelectPrompt?.(p.query, p.category)}
              className="group flex shrink-0 items-center gap-1.5 rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-1 text-[11px] font-medium text-slate-300 transition hover:border-violet-400/40 hover:bg-violet-500/15 hover:text-white"
            >
              <span>{p.label}</span>
            </button>
          ))}
        </div>
      </div>
    </header>
  )
}
