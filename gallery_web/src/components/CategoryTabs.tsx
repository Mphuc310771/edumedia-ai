import React from "react"
import { SmartCategory, MediaItem } from "../types"

interface CategoryTabsProps {
  activeCategory: SmartCategory
  onCategoryChange: (cat: SmartCategory) => void
  items: MediaItem[]
}

const TABS: { key: SmartCategory; label: string }[] = [
  { key: "all", label: "Tất cả" },
  { key: "study", label: "Học tập" },
  { key: "pets", label: "Thú cưng" },
  { key: "food", label: "Ăn uống" },
  { key: "receipts", label: "Hóa đơn" },
  { key: "scenes", label: "Cảnh quan" },
  { key: "videos", label: "Video" },
]

export const CategoryTabs: React.FC<CategoryTabsProps> = ({
  activeCategory,
  onCategoryChange,
  items,
}) => {
  const getCount = (catKey: SmartCategory) => {
    if (catKey === "all") return items.length
    return items.filter((item) => item.category === catKey).length
  }

  return (
    <section className="px-6 max-w-5xl mx-auto w-full mt-4" aria-label="Bộ lọc">
      <div className="flex items-center justify-center gap-1.5 overflow-x-auto pb-2 scrollbar-none" role="tablist">
        {TABS.map((tab) => {
          const count = getCount(tab.key)
          const selected = activeCategory === tab.key
          return (
            <button
              key={tab.key}
              role="tab"
              aria-selected={selected}
              onClick={() => onCategoryChange(tab.key)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap flex items-center gap-1.5 transition-all ${
                selected
                  ? "bg-white/15 text-white font-semibold shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
              }`}
            >
              <span>{tab.label}</span>
              {count > 0 && (
                <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                  selected ? "bg-emerald-500/20 text-emerald-300" : "bg-white/10 text-slate-400"
                }`}>
                  {count}
                </span>
              )}
            </button>
          )
        })}
      </div>
    </section>
  )
}
