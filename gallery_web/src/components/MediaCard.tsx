import React, { useState } from "react"
import { Image as ImageIcon, Mic, Video, Play, Sparkles } from "lucide-react"
import { MediaItem } from "../types"

interface MediaCardProps {
  item: MediaItem
  onClick: () => void
}

const CATEGORY_ICONS: Record<string, string> = {
  study: "🎓",
  people: "👤",
  pets: "🐾",
  food: "☕",
  receipts: "🧾",
  scenes: "🏖️",
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
      aria-label={`Mở ${item.filename}`}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onClick()
      }}
      className="group bg-slate-900/60 hover:bg-slate-800/80 border border-white/10 hover:border-emerald-500/40 rounded-2xl overflow-hidden cursor-pointer flex flex-col transition-all duration-300 hover:shadow-xl hover:shadow-emerald-950/20 hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-emerald-400/50"
    >
      {/* Visual Media Cover */}
      <div className="relative aspect-[4/3] bg-slate-950 overflow-hidden flex items-center justify-center">
        {item.type === "image" && (
          <>
            {displayThumb && !imgError ? (
              <img
                src={displayThumb}
                alt={item.filename}
                loading="lazy"
                onError={() => setImgError(true)}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              />
            ) : (
              <div className="w-full h-full flex flex-col items-center justify-center text-slate-500 bg-slate-950 p-4">
                <ImageIcon className="w-8 h-8 text-cyan-400/60 mb-1" />
                <span className="text-[10px] font-mono text-slate-400 truncate max-w-[140px]">
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
                alt={item.filename}
                loading="lazy"
                onError={() => setImgError(true)}
                className="w-full h-full object-cover opacity-85 group-hover:scale-105 transition-transform duration-500"
              />
            ) : (
              <div className="w-full h-full bg-slate-950 flex items-center justify-center text-slate-600">
                <Video className="w-8 h-8 text-amber-400/60" />
              </div>
            )}
            <div className="absolute inset-0 bg-black/30 flex items-center justify-center">
              <div className="w-10 h-10 rounded-full bg-emerald-500 text-slate-950 flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
                <Play className="w-4 h-4 fill-slate-950 ml-0.5" />
              </div>
            </div>
          </div>
        )}

        {item.type === "audio" && (
          <div className="w-full h-full bg-gradient-to-br from-slate-900 via-indigo-950/40 to-slate-950 flex flex-col items-center justify-center p-4 text-center">
            <div className="w-11 h-11 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-2 shadow-inner group-hover:scale-105 transition-transform">
              <Mic className="w-5 h-5" />
            </div>
            <span className="text-xs font-semibold text-slate-200 truncate max-w-[160px]">
              Ghi âm giọng nói
            </span>
          </div>
        )}

        {/* Category Pill (Top-Left) */}
        <div className="absolute top-2 left-2 px-2 py-0.5 rounded-md bg-black/70 backdrop-blur-md border border-white/10 text-[10px] font-medium text-slate-200 flex items-center gap-1 shadow">
          <span>{icon}</span>
          <span>{item.categoryLabel || item.category}</span>
        </div>

        {/* Media Type Icon (Top-Right) */}
        <div className="absolute top-2 right-2 px-1.5 py-0.5 rounded-md bg-black/70 backdrop-blur-md border border-white/10 flex items-center justify-center text-slate-300 text-[10px] font-mono shadow">
          {item.type === "image" && "Ảnh"}
          {item.type === "audio" && "Audio"}
          {item.type === "video" && "Video"}
        </div>
      </div>

      {/* Clean Minimalist Caption Area */}
      <div className="p-3 flex flex-col justify-between gap-1">
        <span className="text-xs font-semibold text-slate-200 truncate group-hover:text-emerald-300 transition-colors" title={item.filename}>
          {item.filename}
        </span>

        <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
          <span>{item.size}</span>
          <span className="text-slate-400">{item.date?.split(" ")[0]}</span>
        </div>

        {/* Search Match Relevance Highlight */}
        {item.matchedOn && item.matchedOn.length > 0 && (
          <div className="mt-1 flex items-center gap-1 text-[10px] text-amber-300 bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.5 rounded truncate">
            <Sparkles className="w-3 h-3 text-amber-400 shrink-0" />
            <span className="truncate">Khớp: {item.matchedOn.slice(0, 2).join(", ")}</span>
          </div>
        )}
      </div>
    </div>
  )
}
