import React, { useState } from "react"
import { AlertCircle, Check, ChevronRight, Image as ImageIcon, Loader2, Mic, Video } from "lucide-react"
import { isOffMajorSubject, MediaItem } from "../types"
import { HighlightText } from "./HighlightText"

interface MediaListRowProps {
  item: MediaItem
  index: number
  selectMode: boolean
  selected: boolean
  searchQuery?: string
  onClick: () => void
}

export const MediaListRow: React.FC<MediaListRowProps> = ({ item, index, selectMode, selected, searchQuery, onClick }) => {
  const [imgError, setImgError] = useState(false)
  const displayThumb = item.thumbnailUrl || item.url
  const offMajor = isOffMajorSubject(item.subject)
  const TypeIcon = item.type === "audio" ? Mic : item.type === "video" ? Video : ImageIcon

  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      aria-label={`Mở ${item.filename}`}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault()
          onClick()
        }
      }}
      className={`group flex cursor-pointer items-center gap-3.5 border-b border-white/[0.05] px-3.5 py-3 transition last:border-b-0 focus:outline-none sm:px-4 animate-fade-in ${
        selected ? "bg-violet-500/[0.08]" : "hover:bg-white/[0.04] focus:bg-white/[0.05]"
      }`}
      style={{ animationDelay: `${Math.min(index * 25, 350)}ms` }}
    >
      {selectMode && (
        <span
          className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 transition ${
            selected ? "border-violet-400 bg-violet-500 text-white" : "border-white/25 text-transparent"
          }`}
        >
          <Check className="h-3 w-3" strokeWidth={3} />
        </span>
      )}
      <div className="relative h-14 w-20 shrink-0 overflow-hidden rounded-lg border border-white/[0.06] bg-ink-900">
        {(item.type === "image" || item.type === "video") && displayThumb && !imgError ? (
          <img
            src={displayThumb}
            alt=""
            loading="lazy"
            onError={() => setImgError(true)}
            className="h-full w-full object-cover"
          />
        ) : (
          <div
            className={`flex h-full w-full items-center justify-center ${
              item.type === "audio" ? "bg-gradient-to-br from-violet-950/60 to-ink-900 text-violet-300" : "text-slate-600"
            }`}
          >
            <TypeIcon className="h-5 w-5" />
          </div>
        )}
        {item.status === "INDEXING" && (
          <div className="absolute inset-0 flex items-center justify-center bg-ink-950/70">
            <Loader2 className="h-4 w-4 animate-spin text-sky-300" />
          </div>
        )}
      </div>

      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-white group-hover:text-violet-200" title={item.filename}>
          <HighlightText text={item.filename} keywords={searchQuery || item.matchedOn} />
        </p>
        <p className="truncate text-xs text-slate-500">
          <HighlightText text={item.summary || item.categoryLabel} keywords={searchQuery || item.matchedOn} />
        </p>
      </div>

      <div className="hidden shrink-0 items-center gap-1.5 md:flex">
        {item.subjectLabel && (
          <span
            className={`rounded-lg border px-2 py-0.5 text-[11px] font-semibold ${
              offMajor
                ? "border-amber-400/25 bg-amber-500/10 text-amber-200"
                : "border-sky-400/25 bg-sky-500/10 text-sky-200"
            }`}
          >
            {item.subjectLabel}
          </span>
        )}
        <span className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-2 py-0.5 text-[11px] text-slate-400">
          {item.categoryLabel || item.category}
        </span>
      </div>

      <div className="hidden shrink-0 text-right font-mono text-[11px] leading-relaxed text-slate-500 sm:block">
        <p>{item.size}</p>
        <p>{item.date?.split(" ")[0]}</p>
      </div>

      {item.status === "FAILED" && <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />}
      <ChevronRight className="h-4 w-4 shrink-0 text-slate-700 transition group-hover:translate-x-0.5 group-hover:text-slate-400" />
    </div>
  )
}
