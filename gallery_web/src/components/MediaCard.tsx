import React, { useState } from "react"
import { Image as ImageIcon, Mic, Video, Play, Sparkles, FileText, ChevronRight } from "lucide-react"
import { MediaItem } from "../types"

interface MediaCardProps {
  item: MediaItem
  onClick: () => void
}

const CATEGORY_ICONS: Record<string, string> = {
  study: "🎓",
  pets: "🐶",
  food: "☕",
  receipts: "🧾",
  scenes: "🏝️",
  videos: "🎬",
  other: "📁",
}

export const MediaCard: React.FC<MediaCardProps> = ({ item, onClick }) => {
  const [imgError, setImgError] = useState(false)
  const displayThumb = item.thumbnailUrl || item.url
  const icon = CATEGORY_ICONS[item.category] || "📁"

  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      aria-label={`Mở tập tin ${item.filename}`}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") onClick()
      }}
      className="group glass-card rounded-2xl overflow-hidden cursor-pointer flex flex-col relative focus:outline-none focus:ring-2 focus:ring-emerald-400/50"
    >
      {/* Thumbnail Area */}
      <div className="relative aspect-[16/9] bg-[#080D1A] overflow-hidden flex items-center justify-center">
        {item.type === "image" && (
          <>
            {displayThumb && !imgError ? (
              <img
                src={displayThumb}
                alt=""
                loading="lazy"
                onError={() => setImgError(true)}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              />
            ) : (
              <div className="w-full h-full flex flex-col items-center justify-center text-slate-500 bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 p-4">
                <FileText className="w-8 h-8 text-cyan-400/70 mb-1" />
                <span className="text-[11px] font-mono text-slate-400 text-center truncate max-w-[180px]">
                  {item.filename}
                </span>
              </div>
            )}
          </>
        )}

        {item.type === "video" && (
          <div className="w-full h-full relative bg-slate-950 flex items-center justify-center">
            {displayThumb && !imgError ? (
              <img
                src={displayThumb}
                alt=""
                loading="lazy"
                onError={() => setImgError(true)}
                className="w-full h-full object-cover opacity-80 group-hover:scale-105 transition-transform duration-500"
              />
            ) : (
              <div className="w-full h-full bg-slate-900 flex items-center justify-center text-slate-600">
                <Video className="w-10 h-10 text-amber-400/60" />
              </div>
            )}
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent flex items-center justify-center">
              <div className="w-11 h-11 rounded-full bg-emerald-500 text-slate-950 flex items-center justify-center shadow-xl shadow-emerald-950/60 group-hover:scale-110 transition-transform">
                <Play className="w-5 h-5 fill-slate-950 ml-0.5" />
              </div>
            </div>
          </div>
        )}

        {item.type === "audio" && (
          <div className="w-full h-full bg-gradient-to-br from-[#0F172A] via-[#1E1B4B]/50 to-[#0F172A] flex flex-col items-center justify-center p-4 text-center relative overflow-hidden">
            <div className="flex items-center gap-1 mb-2">
              <div className="wave-bar"></div>
              <div className="wave-bar"></div>
              <div className="wave-bar"></div>
              <div className="wave-bar"></div>
              <div className="wave-bar"></div>
            </div>
            <div className="w-7 h-7 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 mb-1">
              <Mic className="w-3.5 h-3.5" />
            </div>
            <span className="text-xs font-bold text-slate-200">Ghi âm Bài giảng</span>
          </div>
        )}

        {/* Category Badge (Top-Left) */}
        <div className="absolute top-2 left-2 px-2 py-0.5 rounded-lg bg-black/75 backdrop-blur-md border border-white/10 text-[10px] font-semibold text-white flex items-center gap-1 shadow-md whitespace-nowrap">
          <span>{icon}</span>
          <span>{item.categoryLabel || item.category}</span>
        </div>

        {/* Media Type Badge (Top-Right) */}
        <div className="absolute top-2 right-2 w-6 h-6 rounded-lg bg-black/75 backdrop-blur-md border border-white/10 flex items-center justify-center text-slate-300 shadow-md">
          {item.type === "image" && <ImageIcon className="w-3.5 h-3.5 text-cyan-400" />}
          {item.type === "audio" && <Mic className="w-3.5 h-3.5 text-indigo-400" />}
          {item.type === "video" && <Video className="w-3.5 h-3.5 text-amber-400" />}
        </div>
      </div>

      {/* Content Area */}
      <div className="p-3.5 flex-1 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between gap-1 mb-1">
            <span className="font-mono text-xs font-bold text-slate-100 truncate" title={item.filename}>
              {item.filename}
            </span>
            <span className="text-[10px] text-slate-400 font-mono shrink-0 bg-white/5 px-1.5 py-0.5 rounded border border-white/5">
              {item.size}
            </span>
          </div>

          <p className="text-xs text-slate-400 line-clamp-2 mb-2 leading-relaxed">
            {item.summary || "Đã index vào cơ sở dữ liệu."}
          </p>

          {item.matchedOn && item.matchedOn.length > 0 && (
            <div className="flex items-center gap-1 text-[10px] text-amber-300 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-md mb-2 font-mono">
              <Sparkles className="w-3 h-3 text-amber-400 shrink-0" />
              <span className="truncate">
                {typeof item.score === "number" ? `${Math.round(item.score * 100)}% khớp: ` : ""}
                {item.matchedOn.slice(0, 3).join(", ")}
              </span>
            </div>
          )}
        </div>

        <div>
          {/* Tags */}
          <div className="flex flex-wrap gap-1 mb-2.5">
            {item.tags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 border border-white/5 text-cyan-300 font-medium"
              >
                #{tag}
              </span>
            ))}
          </div>

          {/* Footer bar */}
          <div className="pt-2 border-t border-white/5 flex items-center justify-between text-[10px] text-slate-500 font-mono">
            <span>{item.date}</span>
            <span className="text-emerald-400 group-hover:translate-x-0.5 transition-transform flex items-center gap-0.5 font-medium">
              Chi tiết <ChevronRight className="w-3 h-3" />
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
