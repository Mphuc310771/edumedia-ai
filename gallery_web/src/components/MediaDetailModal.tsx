import React, { useEffect, useMemo, useRef, useState } from "react"
import {
  AlertCircle,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock,
  Copy,
  Database,
  Download,
  ExternalLink,
  FileText,
  Layers,
  Loader2,
  Mic,
  Pause,
  Play,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Trash2,
  X,
} from "lucide-react"
import { fetchContentUrl, fetchRawTranscript } from "../api/client"
import { isOffMajorSubject, MediaItem } from "../types"
import { HighlightText } from "./HighlightText"
import { formatSecondsToTime, parseTranscript } from "../utils/transcriptParser"

interface MediaDetailModalProps {
  items: MediaItem[]
  index: number
  searchQuery?: string
  onClose: () => void
  onNavigate: (delta: number) => void
  onDelete?: (fileId: string) => Promise<void>
  onRetry?: (item: MediaItem) => void
}

export const MediaDetailModal: React.FC<MediaDetailModalProps> = ({
  items,
  index,
  searchQuery,
  onClose,
  onNavigate,
  onDelete,
  onRetry,
}) => {
  const item = items[index]
  const [activeTab, setActiveTab] = useState<"content" | "tech">("content")
  const [copiedField, setCopiedField] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [contentUrl, setContentUrl] = useState("")
  const [urlLoading, setUrlLoading] = useState(false)
  const [showFullTranscriptModal, setShowFullTranscriptModal] = useState(false)
  const [fullTranscriptLoading, setFullTranscriptLoading] = useState(false)
  const [fullTranscriptContent, setFullTranscriptContent] = useState<string | null>(null)

  // Media Player State & Karaoke Sync
  const mediaRef = useRef<HTMLMediaElement | null>(null)
  const activeSegmentRef = useRef<HTMLDivElement | null>(null)
  const [currentTime, setCurrentTime] = useState(0)
  const [mediaDuration, setMediaDuration] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [transcriptMode, setTranscriptMode] = useState<"interactive" | "plain">("interactive")

  const isS3Offloaded = Boolean(
    item?.has_extended_transcript ||
    item?.hasExtendedTranscript ||
    item?.transcript_s3_uri ||
    item?.transcriptS3Uri,
  )

  const handleOpenFullTranscript = async () => {
    setShowFullTranscriptModal(true)
    if (!fullTranscriptContent && item?.id) {
      setFullTranscriptLoading(true)
      try {
        const data = await fetchRawTranscript(item.id)
        const text = typeof data === "string" ? data : data?.transcript || JSON.stringify(data, null, 2)
        setFullTranscriptContent(text)
      } catch {
        setFullTranscriptContent(item.transcript || "Không tải được toàn văn bản ghi.")
      } finally {
        setFullTranscriptLoading(false)
      }
    }
  }

  const handleDownloadRaw = async () => {
    if (!item?.id) return
    try {
      const data = await fetchRawTranscript(item.id)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `${item.id}_raw_transcript.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      const fallbackData = { file_id: item.id, transcript: item.transcript || "" }
      const blob = new Blob([JSON.stringify(fallbackData, null, 2)], { type: "application/json" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `${item.id}_raw_transcript.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }
  }

  useEffect(() => {
    if (mediaRef.current) {
      mediaRef.current.pause()
    }
    setActiveTab("content")
    setCopiedField(null)
    setShowFullTranscriptModal(false)
    setFullTranscriptContent(null)
    setCurrentTime(0)
    setMediaDuration(0)
    setIsPlaying(false)
  }, [item?.id])

  // Dọn dẹp trình phát âm thanh / video khi modal đóng
  useEffect(() => {
    return () => {
      if (mediaRef.current) {
        mediaRef.current.pause()
        mediaRef.current.src = ""
      }
    }
  }, [])

  useEffect(() => {
    if (!item?.id) return
    let cancelled = false
    setUrlLoading(true)
    setContentUrl("")
    void fetchContentUrl(item.id)
      .then((data) => {
        if (!cancelled) setContentUrl(data.url || data.thumbnailUrl || "")
      })
      .catch(() => {
        if (!cancelled) setContentUrl("")
      })
      .finally(() => {
        if (!cancelled) setUrlLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [item?.id])

  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose()
      if (event.key === "ArrowLeft") onNavigate(-1)
      if (event.key === "ArrowRight") onNavigate(1)
    }
    window.addEventListener("keydown", handleKey)
    return () => window.removeEventListener("keydown", handleKey)
  }, [onClose, onNavigate])

  // Parse structured transcript segments with timestamps
  const rawTranscriptText = fullTranscriptContent || item?.transcript || ""
  const transcriptSegments = useMemo(() => {
    return parseTranscript(rawTranscriptText, mediaDuration)
  }, [rawTranscriptText, mediaDuration])

  // Active segment identification for karaoke playback
  const activeSegmentIndex = useMemo(() => {
    if (transcriptSegments.length === 0) return -1
    return transcriptSegments.findIndex(
      (seg) => currentTime >= seg.startTime && currentTime < seg.endTime,
    )
  }, [transcriptSegments, currentTime])

  // Auto-scroll when active segment changes during playback
  useEffect(() => {
    if (activeSegmentIndex >= 0 && activeSegmentRef.current && isPlaying) {
      activeSegmentRef.current.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      })
    }
  }, [activeSegmentIndex, isPlaying])

  const handleSeek = (seconds: number) => {
    if (mediaRef.current) {
      mediaRef.current.currentTime = seconds
      mediaRef.current.play().catch(() => {})
      setIsPlaying(true)
    }
  }

  if (!item) return null

  const mediaSrc = contentUrl || item.thumbnailUrl || item.url

  const handleCopy = (field: string, text?: string) => {
    if (!text) return
    void navigator.clipboard.writeText(text)
    setCopiedField(field)
    setTimeout(() => setCopiedField(null), 2000)
  }

  const isProtected = Boolean(
    item?.is_demo_protected ||
    item?.isDemoProtected ||
    item?.filename?.toLowerCase().startsWith("sample_") ||
    item?.filename?.toLowerCase().startsWith("demo_") ||
    item?.id?.toLowerCase().startsWith("sample-") ||
    item?.id?.toLowerCase().startsWith("demo-")
  )

  const handleDelete = async () => {
    if (isProtected) {
      alert("Tệp bài giảng mẫu này được bảo vệ cho người dùng trải nghiệm demo. Không thể xóa.")
      return
    }
    if (!onDelete || !confirm(`Xóa tệp "${item.filename}"?`)) return
    setDeleting(true)
    try {
      await onDelete(item.id)
    } finally {
      setDeleting(false)
    }
  }

  const hasTranscript = Boolean(item.transcript && item.transcript.trim())
  const hasOcr = Boolean(item.ocrText && item.ocrText.trim().length > 0)
  const offMajor = isOffMajorSubject(item.subject)

  const CopyButton = ({ field, text }: { field: string; text?: string }) => (
    <button
      type="button"
      onClick={() => handleCopy(field, text)}
      className="flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-violet-300 transition hover:bg-violet-500/10"
    >
      {copiedField === field ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
      {copiedField === field ? "Đã chép" : "Sao chép"}
    </button>
  )

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink-950/90 p-3 backdrop-blur-md animate-fade-in sm:p-6"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className="relative grid h-[min(700px,92vh)] w-full max-w-6xl overflow-hidden rounded-3xl border border-white/[0.08] bg-ink-900 shadow-pop animate-scale-in md:grid-cols-[1.4fr_1fr]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Khung xem media */}
        <div className="relative flex min-h-[240px] items-center justify-center overflow-hidden bg-ink-950 md:border-r md:border-white/[0.06]">
          {item.type === "image" &&
            (mediaSrc ? (
              <img src={mediaSrc} alt={item.filename} className="max-h-full max-w-full object-contain" />
            ) : urlLoading ? (
              <Loader2 className="h-8 w-8 animate-spin text-slate-500" />
            ) : (
              <p className="text-sm text-slate-600">Không có ảnh xem trước</p>
            ))}

          {item.type === "video" &&
            (mediaSrc ? (
              <video
                ref={mediaRef as any}
                controls
                autoPlay
                src={mediaSrc}
                poster={item.thumbnailUrl}
                className="max-h-full max-w-full"
                onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
                onLoadedMetadata={(e) => setMediaDuration(e.currentTarget.duration || 0)}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
              />
            ) : urlLoading ? (
              <Loader2 className="h-8 w-8 animate-spin text-slate-500" />
            ) : (
              <p className="text-sm text-slate-600">Video không khả dụng</p>
            ))}

          {item.type === "audio" && (
            <div className="w-full max-w-md px-8 text-center">
              <div
                className={`mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-3xl border transition-all duration-300 ${
                  isPlaying
                    ? "border-violet-400 bg-violet-500/25 text-violet-200 shadow-glow ring-2 ring-violet-400/40"
                    : "border-violet-400/25 bg-violet-500/15 text-violet-300"
                }`}
              >
                <Mic className="h-7 w-7" />
              </div>
              <h4 className="mb-1 truncate text-base font-bold text-white">{item.filename}</h4>
              <p className="mb-4 font-mono text-xs text-slate-500">
                {item.size} {mediaDuration > 0 ? `· ${formatSecondsToTime(mediaDuration)}` : ""}
              </p>
              {mediaSrc ? (
                <div className="space-y-2">
                  <audio
                    ref={mediaRef as any}
                    controls
                    src={mediaSrc}
                    className="w-full"
                    onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
                    onLoadedMetadata={(e) => setMediaDuration(e.currentTarget.duration || 0)}
                    onPlay={() => setIsPlaying(true)}
                    onPause={() => setIsPlaying(false)}
                  />
                  {transcriptSegments.length > 0 && (
                    <div className="flex items-center justify-between font-mono text-[11px] text-slate-400">
                      <span>Đang phát: {formatSecondsToTime(currentTime)}</span>
                      <span>
                        Thời lượng:{" "}
                        {formatSecondsToTime(
                          mediaDuration || transcriptSegments[transcriptSegments.length - 1]?.endTime || 0,
                        )}
                      </span>
                    </div>
                  )}
                </div>
              ) : urlLoading ? (
                <Loader2 className="mx-auto h-6 w-6 animate-spin text-slate-500" />
              ) : null}
            </div>
          )}

          {/* Điều hướng trước / sau */}
          {index > 0 && (
            <button
              type="button"
              onClick={() => onNavigate(-1)}
              className="absolute left-3 top-1/2 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full border border-white/10 bg-black/55 text-white backdrop-blur-md transition hover:bg-violet-500/60"
              aria-label="Tệp trước"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
          )}
          {index < items.length - 1 && (
            <button
              type="button"
              onClick={() => onNavigate(1)}
              className="absolute right-3 top-1/2 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full border border-white/10 bg-black/55 text-white backdrop-blur-md transition hover:bg-violet-500/60"
              aria-label="Tệp sau"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
          )}
          <span className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full border border-white/10 bg-black/55 px-2.5 py-1 font-mono text-[11px] text-slate-300 backdrop-blur-md">
            {index + 1} / {items.length}
          </span>
        </div>

        {/* Bảng thông tin */}
        <div className="flex min-h-0 flex-col">
          <div className="border-b border-white/[0.06] p-4 pr-24">
            <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
              {item.subjectLabel && (
                <span
                  className={`rounded-lg border px-2 py-0.5 text-[11px] font-bold ${
                    offMajor
                      ? "border-amber-400/25 bg-amber-500/10 text-amber-200"
                      : "border-sky-400/25 bg-sky-500/10 text-sky-200"
                  }`}
                >
                  {item.subjectLabel}
                </span>
              )}
              <span className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-2 py-0.5 text-[11px] font-semibold text-slate-300">
                {item.categoryLabel || item.category}
              </span>
              <span className="font-mono text-xs text-slate-500">{item.size}</span>
            </div>
            <h3 className="truncate text-base font-bold text-white" title={item.filename}>
              <HighlightText text={item.filename} keywords={searchQuery || item.matchedOn} />
            </h3>
            <p className="mt-0.5 font-mono text-xs text-slate-400">{item.date}</p>

            {/* Các nút góc trên bên phải */}
            <div className="absolute right-4 top-4 flex items-center gap-1">
              <a
                href={mediaSrc}
                target="_blank"
                rel="noreferrer"
                download={item.filename}
                className="rounded-xl p-2 text-slate-400 transition hover:bg-white/[0.08] hover:text-white"
                title="Tải tệp về máy"
              >
                <Download className="h-4 w-4" />
              </a>
              {onDelete && (
                <button
                  type="button"
                  onClick={() => void handleDelete()}
                  disabled={deleting}
                  className={`rounded-xl p-2 transition ${
                    isProtected
                      ? "text-emerald-400 hover:bg-emerald-500/10 hover:text-emerald-300"
                      : "text-rose-400 hover:bg-rose-500/10 hover:text-rose-300 disabled:opacity-40"
                  }`}
                  title={isProtected ? "Tệp bài giảng mẫu (Được bảo vệ demo)" : "Xóa tệp"}
                >
                  {isProtected ? <ShieldCheck className="h-4 w-4" /> : <Trash2 className="h-4 w-4" />}
                </button>
              )}
              <button
                type="button"
                onClick={onClose}
                className="rounded-xl p-2 text-slate-400 transition hover:bg-white/[0.08] hover:text-white"
                aria-label="Đóng cửa sổ"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="flex border-b border-white/[0.06] px-4">
            {(["content", "tech"] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`flex items-center gap-1.5 border-b-2 px-3 py-2.5 text-sm font-semibold transition ${
                  activeTab === tab
                    ? "border-violet-400 text-violet-200"
                    : "border-transparent text-slate-500 hover:text-white"
                }`}
              >
                {tab === "content" ? <Sparkles className="h-3.5 w-3.5" /> : <Layers className="h-3.5 w-3.5" />}
                {tab === "content" ? "Nội dung" : "Thông số kỹ thuật"}
              </button>
            ))}
          </div>

          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4 text-sm">
            {activeTab === "content" && (
              <>
                {item.error && (
                  <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 p-3 text-rose-200">
                    <div className="flex gap-2">
                      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                      <span className="min-w-0 break-words">{item.error}</span>
                    </div>
                    {onRetry && item.status === "FAILED" && (
                      <button
                        type="button"
                        onClick={() => onRetry(item)}
                        className="mt-2.5 inline-flex items-center gap-1.5 rounded-lg bg-rose-500/20 px-3 py-1.5 text-xs font-bold text-rose-100 transition hover:bg-rose-500/35"
                      >
                        <RotateCcw className="h-3.5 w-3.5" />
                        Thử lại phân tích
                      </button>
                    )}
                  </div>
                )}

                <div className="rounded-2xl surface p-3.5">
                  <div className="mb-1.5 flex items-center gap-1.5 text-[13px] font-bold text-slate-100">
                    <Sparkles className="h-3.5 w-3.5 text-violet-300" />
                    Tóm tắt
                  </div>
                  <p className="leading-relaxed text-slate-300">
                    <HighlightText
                      text={item.summary || "Chưa có tóm tắt."}
                      keywords={searchQuery || item.matchedOn}
                    />
                  </p>
                </div>

                {/* Khung lời thoại Amazon Transcribe (Audio & Video) */}
                {(item.type === "audio" || item.type === "video") &&
                  (hasTranscript || isS3Offloaded || transcriptSegments.length > 0) && (
                    <div>
                      {isS3Offloaded && (
                        <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-sky-500/25 bg-sky-500/10 px-3 py-2 text-xs text-sky-200">
                          <div className="flex items-center gap-1.5 font-medium">
                            <Database className="h-3.5 w-3.5 text-sky-400" />
                            <span>Bản ghi dài - Đã lưu trữ an toàn trên S3</span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <button
                              type="button"
                              onClick={handleOpenFullTranscript}
                              className="inline-flex items-center gap-1 rounded-lg bg-white/[0.08] px-2 py-1 text-[11px] font-semibold text-slate-200 transition hover:bg-white/[0.15]"
                            >
                              <ExternalLink className="h-3 w-3" />
                              Xem toàn văn
                            </button>
                            <button
                              type="button"
                              onClick={handleDownloadRaw}
                              className="inline-flex items-center gap-1 rounded-lg bg-sky-500/25 px-2 py-1 text-[11px] font-semibold text-sky-200 transition hover:bg-sky-500/40"
                            >
                              <Download className="h-3 w-3" />
                              Tải JSON
                            </button>
                          </div>
                        </div>
                      )}

                      <div className="mb-2 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="flex items-center gap-1.5 text-[13px] font-bold text-slate-100">
                            <Mic className="h-3.5 w-3.5 text-sky-300" />
                            Lời thoại bài giảng
                          </span>
                          {transcriptSegments.length > 0 && (
                            <div className="flex rounded-lg border border-white/[0.08] bg-white/[0.04] p-0.5 text-[11px]">
                              <button
                                type="button"
                                onClick={() => setTranscriptMode("interactive")}
                                className={`rounded-md px-2 py-0.5 font-semibold transition ${
                                  transcriptMode === "interactive"
                                    ? "bg-violet-500/80 text-white shadow-sm"
                                    : "text-slate-400 hover:text-white"
                                }`}
                              >
                                Mốc thời gian
                              </button>
                              <button
                                type="button"
                                onClick={() => setTranscriptMode("plain")}
                                className={`rounded-md px-2 py-0.5 font-semibold transition ${
                                  transcriptMode === "plain"
                                    ? "bg-violet-500/80 text-white shadow-sm"
                                    : "text-slate-400 hover:text-white"
                                }`}
                              >
                                Toàn văn
                              </button>
                            </div>
                          )}
                        </div>
                        {hasTranscript && <CopyButton field="transcript" text={item.transcript} />}
                      </div>

                      {transcriptMode === "interactive" && transcriptSegments.length > 0 ? (
                        <div className="max-h-60 space-y-2 overflow-y-auto rounded-2xl border border-white/[0.06] bg-ink-950/60 p-2.5">
                          {transcriptSegments.map((seg, idx) => {
                            const isActive = activeSegmentIndex === idx
                            return (
                              <div
                                key={seg.id}
                                ref={isActive ? activeSegmentRef : null}
                                onClick={() => handleSeek(seg.startTime)}
                                className={`group flex cursor-pointer items-start gap-2.5 rounded-xl border p-2.5 text-xs transition duration-200 ${
                                  isActive
                                    ? "border-violet-400/80 bg-violet-500/20 text-white shadow-glow-sm ring-1 ring-violet-400/40"
                                    : "border-white/[0.04] bg-white/[0.02] text-slate-300 hover:border-white/10 hover:bg-white/[0.05]"
                                }`}
                              >
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleSeek(seg.startTime)
                                  }}
                                  className={`flex shrink-0 items-center gap-1 rounded-md px-2 py-0.5 font-mono text-[11px] font-bold transition ${
                                    isActive
                                      ? "bg-violet-500 text-white shadow-sm"
                                      : "bg-white/[0.08] text-violet-300 group-hover:bg-violet-500/30"
                                  }`}
                                  title="Click để phát từ mốc thời gian này"
                                >
                                  {isActive && isPlaying ? (
                                    <Pause className="h-3 w-3" />
                                  ) : (
                                    <Play className="h-3 w-3" />
                                  )}
                                  {seg.timestampStr}
                                </button>
                                <div className="min-w-0 flex-1 leading-relaxed">
                                  <HighlightText text={seg.text} keywords={searchQuery || item.matchedOn} />
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      ) : (
                        <div className="max-h-52 overflow-y-auto whitespace-pre-wrap rounded-2xl surface p-3.5 leading-relaxed text-slate-300">
                          <HighlightText
                            text={hasTranscript ? item.transcript! : "Chưa có transcript từ Amazon Transcribe."}
                            keywords={searchQuery || item.matchedOn}
                          />
                        </div>
                      )}
                    </div>
                  )}

                {item.type === "image" && hasOcr && (
                  <div>
                    <div className="mb-1.5 flex items-center justify-between">
                      <span className="flex items-center gap-1.5 text-[13px] font-bold text-slate-100">
                        <FileText className="h-3.5 w-3.5 text-sky-300" />
                        Chữ trong ảnh (OCR)
                      </span>
                      <CopyButton field="ocr" text={item.ocrText} />
                    </div>
                    <div className="max-h-44 overflow-y-auto whitespace-pre-wrap rounded-2xl surface p-3.5 font-mono text-xs leading-relaxed text-slate-300">
                      <HighlightText text={item.ocrText!} keywords={searchQuery || item.matchedOn} />
                    </div>
                  </div>
                )}

                {item.tags && item.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {item.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-2.5 py-1 text-xs text-slate-400"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
              </>
            )}

            {activeTab === "tech" && (
              <div className="space-y-4">
                {/* Thông tin kỹ thuật tệp */}
                <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-4">
                  <div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-300">
                    <Database className="h-4 w-4 text-violet-400" />
                    <span>Metadata & Định danh Tệp AWS</span>
                  </div>
                  <div className="space-y-2.5 font-mono text-xs">
                    <div className="flex items-center justify-between rounded-xl surface p-2.5">
                      <div className="min-w-0 flex-1">
                        <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">File ID</div>
                        <div className="truncate text-slate-200">{item.id}</div>
                      </div>
                      <CopyButton field="fileId" text={item.id} />
                    </div>

                    <div className="flex items-center justify-between rounded-xl surface p-2.5">
                      <div className="min-w-0 flex-1">
                        <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Định dạng & Dung lượng</div>
                        <div className="truncate text-slate-200">{item.type?.toUpperCase()} · {item.size}</div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between rounded-xl surface p-2.5">
                      <div className="min-w-0 flex-1">
                        <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Chuyên ngành & Danh mục</div>
                        <div className="truncate text-slate-200">{item.subjectLabel || item.subject || "Chung"} · {item.categoryLabel || item.category}</div>
                      </div>
                    </div>

                    <div className="rounded-xl surface p-2.5">
                      <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Pipeline Xử lý Sự kiện AWS</div>
                      <div className="mt-1 text-xs leading-relaxed text-slate-300">
                        {item.pipeline && item.pipeline.length > 0
                          ? item.pipeline.join(" → ")
                          : "S3 Uploads → SQS Ingest Queue → Lambda Ingest → AI Engine → DynamoDB Table"}
                      </div>
                    </div>

                    <div className="rounded-xl surface p-2.5">
                      <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Động cơ Phân tích & AI Model</div>
                      <div className="mt-1 text-xs text-violet-300">
                        {item.analysisSource === "amazon-nova-pro"
                          ? "Amazon Bedrock (us.amazon.nova-pro-v1:0) & Amazon Titan V2"
                          : item.analysisSource === "rekognition"
                            ? "Amazon Rekognition Computer Vision & OCR"
                            : item.analysisSource === "transcribe"
                              ? "Amazon Transcribe Speech-to-Text vi-VN"
                              : "Amazon Bedrock Nova Pro Multi-modal"}
                      </div>
                    </div>

                    {item.transcript_s3_uri && (
                      <div className="flex items-center justify-between rounded-xl surface p-2.5">
                        <div className="min-w-0 flex-1">
                          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Lưu trữ Toàn văn S3</div>
                          <div className="truncate text-slate-200">{item.transcript_s3_uri}</div>
                        </div>
                        <CopyButton field="s3Uri" text={item.transcript_s3_uri} />
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {showFullTranscriptModal && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm animate-fade-in">
          <div className="flex max-h-[85vh] w-full max-w-2xl flex-col rounded-2xl border border-white/10 bg-ink-900 p-5 shadow-2xl">
            <div className="mb-3 flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 text-sky-400" />
                <span className="font-bold text-white">Toàn văn bản ghi (S3 Storage)</span>
              </div>
              <button
                type="button"
                onClick={() => setShowFullTranscriptModal(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-white/[0.08] hover:text-white"
                aria-label="Đóng"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto whitespace-pre-wrap rounded-xl bg-ink-950 p-4 font-mono text-xs leading-relaxed text-slate-200">
              {fullTranscriptLoading ? (
                <div className="flex items-center justify-center py-10">
                  <Loader2 className="h-6 w-6 animate-spin text-sky-400" />
                </div>
              ) : (
                <HighlightText
                  text={fullTranscriptContent || item?.transcript || "Không có nội dung"}
                  keywords={searchQuery || item?.matchedOn}
                />
              )}
            </div>
            <div className="mt-4 flex items-center justify-between">
              <span className="truncate pr-2 font-mono text-[11px] text-slate-400">
                {item?.transcript_s3_uri || `s3://agentsys/transcripts/raw/${item?.id}.json`}
              </span>
              <div className="flex shrink-0 gap-2">
                <button
                  type="button"
                  onClick={handleDownloadRaw}
                  className="inline-flex items-center gap-1.5 rounded-xl bg-sky-500/20 px-3 py-1.5 text-xs font-semibold text-sky-200 hover:bg-sky-500/30"
                >
                  <Download className="h-3.5 w-3.5" />
                  Tải JSON
                </button>
                <button
                  type="button"
                  onClick={() => setShowFullTranscriptModal(false)}
                  className="rounded-xl bg-white/[0.08] px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-white/[0.15]"
                >
                  Đóng
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
