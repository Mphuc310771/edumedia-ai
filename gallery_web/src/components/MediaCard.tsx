import React, { useState } from "react"
import {
  AlertCircle,
  Check,
  Image as ImageIcon,
  Loader2,
  Mic,
  Play,
  RotateCcw,
  Sparkles,
  Video,
} from "lucide-react"
import { isOffMajorSubject, MediaItem } from "../types"
import { HighlightText } from "./HighlightText"

interface MediaCardProps {
  item: MediaItem
  index: number
  selectMode: boolean
  selected: boolean
  searchQuery?: string
  onClick: () => void
  onRetry: () => void
}

const WAVE_HEIGHTS = [38, 62, 84, 52, 70, 44, 90, 58, 76, 48, 66, 40, 82, 56, 72, 46]

function TypeBadge({ type }: { type: MediaItem["type"] }) {
  const Icon = type === "audio" ? Mic : type === "video" ? Video : ImageIcon
  return (
    <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-black/55 text-slate-200 backdrop-blur-md">
      <Icon className="h-3.5 w-3.5" />
    </span>
  )
}

export const MediaCard: React.FC<MediaCardProps> = ({ item, index, selectMode, selected, searchQuery, onClick, onRetry }) => {
  const [imgError, setImgError] = useState(false)
  const displayThumb = item.thumbnailUrl || item.url
  const indexing = item.status === "INDEXING"
  const failed = item.status === "FAILED"
  const offMajor = isOffMajorSubject(item.subject)

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
      className={`group relative aspect-[4/3] cursor-pointer overflow-hidden rounded-2xl border bg-ink-850 shadow-card transition duration-300 focus:outline-none focus:ring-2 focus:ring-violet-400/60 animate-slide-up ${
        selected
          ? "border-violet-400/80 ring-2 ring-violet-400/70"
          : "border-white/[0.07] hover:-translate-y-1 hover:border-violet-400/40 hover:shadow-glow"
      }`}
      style={{ animationDelay: `${Math.min(index * 35, 420)}ms` }}
    >
      {/* Nội dung nền */}
      {item.type === "image" &&
        (displayThumb && !imgError ? (
          <img
            src={displayThumb}
            alt={item.filename}
            loading="lazy"
            onError={() => setImgError(true)}
            className={`absolute inset-0 h-full w-full object-cover transition duration-500 group-hover:scale-[1.06] ${
              selected ? "scale-[1.02] opacity-75" : ""
            }`}
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-ink-800 to-ink-950">
            <ImageIcon className="h-9 w-9 text-slate-700" />
          </div>
        ))}

      {item.type === "video" && (
        <>
          {displayThumb && !imgError ? (
            <img
              src={displayThumb}
              alt=""
              loading="lazy"
              onError={() => setImgError(true)}
              className="absolute inset-0 h-full w-full object-cover opacity-90 transition duration-500 group-hover:scale-[1.06]"
            />
          ) : (
            <div className="absolute inset-0 bg-gradient-to-br from-ink-700 via-ink-850 to-ink-950" />
          )}
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="flex h-12 w-12 items-center justify-center rounded-full border border-white/25 bg-black/45 backdrop-blur-md transition group-hover:scale-110 group-hover:bg-violet-500/70">
              <Play className="ml-0.5 h-5 w-5 fill-white text-white" />
            </span>
          </div>
        </>
      )}

      {item.type === "audio" && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-gradient-to-br from-violet-950/70 via-ink-900 to-ink-950 pb-8">
          <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-violet-400/25 bg-violet-500/15 text-violet-300">
            <Mic className="h-5 w-5" />
          </span>
          <div className="flex h-10 items-center gap-[3px]">
            {WAVE_HEIGHTS.map((height, i) => (
              <span
                key={i}
                className="w-[3px] rounded-full bg-gradient-to-t from-violet-400 to-sky-300 opacity-70 group-hover:animate-wave"
                style={{ height: `${height}%`, animationDelay: `${i * 70}ms` }}
              />
            ))}
          </div>
        </div>
      )}

      {/* Chip góc trên */}
      <div className="absolute left-2.5 right-2.5 top-2.5 flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-start gap-1.5">
          {selectMode && (
            <span
              className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 backdrop-blur-md transition ${
                selected
                  ? "border-violet-400 bg-violet-500 text-white"
                  : "border-white/50 bg-black/40 text-transparent"
              }`}
            >
              <Check className="h-3.5 w-3.5" strokeWidth={3} />
            </span>
          )}
          <div className="flex min-w-0 flex-wrap gap-1">
            {item.subjectLabel ? (
              <span
                className={`truncate rounded-lg border px-2 py-0.5 text-[11px] font-bold backdrop-blur-md ${
                  offMajor
                    ? "border-amber-400/30 bg-amber-500/25 text-amber-100"
                    : "border-sky-400/30 bg-sky-500/25 text-sky-100"
                }`}
              >
                {item.subjectLabel}
              </span>
            ) : (
              <span className="truncate rounded-lg border border-white/10 bg-black/55 px-2 py-0.5 text-[11px] font-semibold text-slate-200 backdrop-blur-md">
                {item.categoryLabel || item.category}
              </span>
            )}
            {(item.has_extended_transcript || item.hasExtendedTranscript || Boolean(item.transcript_s3_uri)) && (
              <span
                className="truncate rounded-lg border border-sky-400/40 bg-sky-500/25 px-1.5 py-0.5 text-[10px] font-bold text-sky-200 backdrop-blur-md"
                title="Bản ghi dài - Đã lưu trữ an toàn trên S3"
              >
                S3
              </span>
            )}
          </div>
        </div>
        <TypeBadge type={item.type} />
      </div>

      {/* Overlay tên tệp */}
      <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/95 via-black/60 to-transparent px-3 pb-2.5 pt-10">
        {item.matchedOn && item.matchedOn.length > 0 && (
          <span className="mb-1.5 inline-flex max-w-full items-center gap-1 truncate rounded-md border border-violet-400/30 bg-violet-500/25 px-1.5 py-0.5 text-[10px] font-semibold text-violet-100 backdrop-blur-md">
            <Sparkles className="h-2.5 w-2.5 shrink-0" />
            <span className="truncate">Khớp: {item.matchedOn.slice(0, 2).join(", ")}</span>
          </span>
        )}
        <p className="truncate text-[13px] font-bold text-white" title={item.filename}>
          <HighlightText text={item.filename} keywords={searchQuery || item.matchedOn} />
        </p>
        {(item.transcript || item.ocrText) && (searchQuery || (item.matchedOn && item.matchedOn.length > 0)) && (
          <p className="mt-0.5 line-clamp-1 text-[11px] font-normal text-slate-300">
            <HighlightText
              text={item.transcript ? `“${item.transcript.slice(0, 75)}...”` : item.ocrText?.slice(0, 75) || ""}
              keywords={searchQuery || item.matchedOn}
            />
          </p>
        )}
        <p className="truncate font-mono text-[11px] text-slate-400">
          {item.size} · {item.date?.split(" ")[0]}
        </p>
      </div>

      {/* Trạng thái xử lý */}
      {(indexing || failed) && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2.5 bg-ink-950/70 backdrop-blur-[2px]">
          {indexing ? (
            <span className="flex items-center gap-2 rounded-full border border-sky-400/25 bg-ink-900/90 px-3.5 py-1.5 text-xs font-semibold text-sky-200">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Đang phân tích
            </span>
          ) : (
            <>
              <span className="flex items-center gap-2 rounded-full border border-rose-400/25 bg-rose-950/90 px-3.5 py-1.5 text-xs font-semibold text-rose-200">
                <AlertCircle className="h-3.5 w-3.5" />
                Thất bại
              </span>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  onRetry()
                }}
                className="flex items-center gap-1.5 rounded-full border border-white/15 bg-white/10 px-3.5 py-1.5 text-xs font-bold text-white backdrop-blur-md transition hover:bg-violet-500/60"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Thử lại
              </button>
            </>
          )}
        </div>
      )}
    </div>
  )
}
