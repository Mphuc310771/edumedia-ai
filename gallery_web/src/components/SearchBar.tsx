import React, { useRef } from "react"
import { Search, X } from "lucide-react"

interface SearchBarProps {
  searchQuery: string
  onSearchChange: (query: string) => void
  inputRef?: React.RefObject<HTMLInputElement>
}

const QUICK_TAGS = [
  { label: "Bài giảng", query: "bài giảng" },
  { label: "Công thức toán", query: "công thức toán" },
  { label: "Hóa đơn", query: "hóa đơn" },
  { label: "Thú cưng", query: "thú cưng" },
]

export const SearchBar: React.FC<SearchBarProps> = ({ searchQuery, onSearchChange, inputRef }) => {
  const localRef = useRef<HTMLInputElement | null>(null)
  const actualRef = inputRef || localRef

  return (
    <section className="px-6 pt-10 pb-4 max-w-3xl mx-auto w-full">
      {/* Title */}
      <div className="text-center mb-5">
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
          Tìm kiếm Media bằng <span className="text-gradient">AI</span>
        </h1>
      </div>

      {/* Main Search Input */}
      <div className="relative group">
        <div className="flex items-center bg-[#0F172A]/80 backdrop-blur-xl rounded-2xl border border-white/10 px-4 py-3 gap-3 shadow-xl focus-within:border-emerald-500/50 focus-within:ring-1 focus-within:ring-emerald-500/30 transition-all">
          <Search className="w-4 h-4 text-emerald-400 shrink-0" />
          <input
            ref={actualRef}
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Tìm kiếm nội dung trong ảnh, âm thanh, bài giảng..."
            className="w-full bg-transparent border-none text-slate-100 placeholder-slate-500 text-sm focus:outline-none"
          />
          {searchQuery ? (
            <button
              onClick={() => onSearchChange("")}
              className="p-1 text-slate-400 hover:text-white rounded-lg transition-colors shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          ) : (
            <kbd className="hidden sm:inline-block text-[11px] font-mono text-slate-400 bg-white/5 border border-white/10 px-2 py-0.5 rounded shrink-0">
              /
            </kbd>
          )}
        </div>
      </div>

      {/* Quick Search Chips */}
      <div className="flex flex-wrap items-center justify-center gap-1.5 mt-3.5">
        <span className="text-xs text-slate-500 mr-1">Gợi ý:</span>
        {QUICK_TAGS.map((tag) => {
          const isActive = searchQuery.toLowerCase() === tag.query.toLowerCase()
          return (
            <button
              key={tag.label}
              onClick={() => onSearchChange(isActive ? "" : tag.query)}
              className={`text-xs px-3 py-1 rounded-lg transition-all ${
                isActive
                  ? "bg-emerald-500 text-slate-950 font-semibold"
                  : "bg-white/5 text-slate-400 hover:text-slate-200 hover:bg-white/10"
              }`}
            >
              {tag.label}
            </button>
          )
        })}
      </div>
    </section>
  )
}
