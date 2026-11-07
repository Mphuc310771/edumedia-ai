import React from "react"
import { ArrowUpDown, CheckSquare, LayoutGrid, List, RefreshCw, Trash2 } from "lucide-react"
import { categoryMeta, RELEVANCE_OPTION, SORT_OPTIONS, SortMode, subjectMeta, ViewMode } from "../catalog"
import { SmartCategory } from "../types"

interface ToolbarProps {
  activeCategory: SmartCategory
  activeSubject: string
  searchQuery: string
  count: number
  loading: boolean
  sort: SortMode
  onSortChange: (sort: SortMode) => void
  view: ViewMode
  onViewChange: (view: ViewMode) => void
  aiActive: boolean
  selectMode: boolean
  onToggleSelectMode: () => void
  onRefresh: () => void
  onClearAll: () => void
}

function resolveTitle(activeCategory: SmartCategory, activeSubject: string, searchQuery: string): string {
  if (searchQuery.trim()) return `Kết quả cho “${searchQuery.trim()}”`
  if (activeSubject === "off_major") return "Môn ngoài ngành"
  const subject = subjectMeta(activeSubject)
  if (activeSubject !== "all" && subject) return subject.label
  const category = categoryMeta(activeCategory)
  if (activeCategory !== "all" && category) return category.label
  return "Toàn bộ thư viện"
}

export const Toolbar: React.FC<ToolbarProps> = ({
  activeCategory,
  activeSubject,
  searchQuery,
  count,
  loading,
  sort,
  onSortChange,
  view,
  onViewChange,
  aiActive,
  selectMode,
  onToggleSelectMode,
  onRefresh,
  onClearAll,
}) => {
  const title = resolveTitle(activeCategory, activeSubject, searchQuery)
  const options = aiActive ? [RELEVANCE_OPTION, ...SORT_OPTIONS] : SORT_OPTIONS

  return (
    <div className="mb-5 flex flex-wrap items-center gap-x-4 gap-y-3">
      <div className="flex min-w-0 items-baseline gap-2.5">
        <h1 className="truncate text-xl font-extrabold tracking-tight text-white">{title}</h1>
        <span className="shrink-0 text-sm font-medium text-slate-500">
          {loading ? "đang tải..." : `${count} tệp`}
        </span>
      </div>

      <div className="ml-auto flex items-center gap-2">
        <label className="flex items-center gap-1.5 rounded-xl border border-white/[0.08] bg-white/[0.03] px-2.5 py-1.5 text-sm text-slate-300 transition focus-within:border-violet-400/40">
          <ArrowUpDown className="h-3.5 w-3.5 text-slate-500" />
          <select
            value={sort}
            onChange={(e) => onSortChange(e.target.value as SortMode)}
            className="cursor-pointer bg-transparent text-sm font-medium text-slate-200 focus:outline-none [&>option]:bg-ink-800"
            aria-label="Sắp xếp"
          >
            {options.map((option) => (
              <option key={option.key} value={option.key}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <div className="flex items-center rounded-xl border border-white/[0.08] bg-white/[0.03] p-1">
          <button
            type="button"
            onClick={() => onViewChange("grid")}
            className={`rounded-lg p-1.5 transition ${
              view === "grid" ? "bg-violet-500/20 text-violet-200" : "text-slate-500 hover:text-white"
            }`}
            aria-label="Xem dạng lưới"
            title="Dạng lưới"
          >
            <LayoutGrid className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => onViewChange("list")}
            className={`rounded-lg p-1.5 transition ${
              view === "list" ? "bg-violet-500/20 text-violet-200" : "text-slate-500 hover:text-white"
            }`}
            aria-label="Xem dạng danh sách"
            title="Dạng danh sách"
          >
            <List className="h-4 w-4" />
          </button>
        </div>

        <button
          type="button"
          onClick={onToggleSelectMode}
          className={`flex items-center gap-1.5 rounded-xl border px-2.5 py-2 text-sm font-medium transition ${
            selectMode
              ? "border-violet-400/40 bg-violet-500/15 text-violet-200"
              : "border-white/[0.08] bg-white/[0.03] text-slate-400 hover:text-white"
          }`}
          aria-label="Chọn nhiều tệp"
          title="Chọn nhiều tệp"
        >
          <CheckSquare className="h-4 w-4" />
          <span className="hidden md:inline">{selectMode ? "Đang chọn" : "Chọn"}</span>
        </button>

        <button
          type="button"
          onClick={onRefresh}
          className="rounded-xl border border-white/[0.08] bg-white/[0.03] p-2 text-slate-400 transition hover:text-white"
          aria-label="Làm mới"
          title="Làm mới"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
        </button>

        <button
          type="button"
          onClick={onClearAll}
          className="rounded-xl border border-white/[0.08] bg-white/[0.03] p-2 text-slate-400 transition hover:border-rose-400/30 hover:bg-rose-500/10 hover:text-rose-300"
          aria-label="Dọn sạch thư viện"
          title="Dọn sạch thư viện"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
