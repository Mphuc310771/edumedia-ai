import React, { useEffect, useRef } from "react"
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Loader2,
  Sparkles,
  UploadCloud,
  X,
} from "lucide-react"
import { UploadTask } from "../hooks/useUploadQueue"

interface ProcessingConsoleProps {
  isOpen: boolean
  onClose: () => void
  tasks: UploadTask[]
}

function TaskIcon({ status }: { status: UploadTask["status"] }) {
  switch (status) {
    case "queued":
      return <Clock className="h-3.5 w-3.5 text-slate-500" />
    case "uploading":
      return <UploadCloud className="h-3.5 w-3.5 animate-pulse text-sky-300" />
    case "processing":
      return <Sparkles className="h-3.5 w-3.5 animate-pulse text-violet-300" />
    case "done":
      return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
    case "failed":
      return <AlertCircle className="h-3.5 w-3.5 text-rose-400" />
  }
}

const STATUS_TEXT: Record<UploadTask["status"], string> = {
  queued: "Chờ đến lượt",
  uploading: "Đang tải lên S3",
  processing: "AI đang phân tích",
  done: "Hoàn tất",
  failed: "Thất bại",
}

export const ProcessingConsole: React.FC<ProcessingConsoleProps> = ({ isOpen, onClose, tasks }) => {
  const listRef = useRef<HTMLDivElement | null>(null)
  const [isExpanded, setIsExpanded] = React.useState(true)

  const total = tasks.length
  const settled = tasks.filter((task) => task.status === "done" || task.status === "failed").length
  const okCount = tasks.filter((task) => task.status === "done").length
  const isFinished = total > 0 && settled >= total
  const progressPercent = total > 0 ? Math.round((settled / total) * 100) : 0
  const active = tasks.find((task) => task.status === "processing") || tasks.find((task) => task.status === "uploading")

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight
  }, [tasks])

  useEffect(() => {
    if (isFinished) {
      const timer = setTimeout(() => onClose(), 8000)
      return () => clearTimeout(timer)
    }
  }, [isFinished, onClose])

  if (!isOpen || total === 0) return null

  return (
    <div className="pointer-events-auto fixed bottom-5 right-5 z-[60] w-[min(420px,calc(100vw-2rem))] animate-slide-up">
      <div className="overflow-hidden rounded-2xl border border-white/[0.09] bg-ink-900/95 shadow-pop backdrop-blur-xl">
        <div className="flex items-center justify-between gap-3 p-3">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <div
              className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${
                isFinished
                  ? okCount > 0
                    ? "bg-emerald-500/15 text-emerald-400"
                    : "bg-rose-500/15 text-rose-400"
                  : "bg-gradient-to-br from-violet-500/25 to-sky-400/25 text-violet-300"
              }`}
            >
              {isFinished ? (
                okCount > 0 ? (
                  <CheckCircle2 className="h-5 w-5" />
                ) : (
                  <AlertCircle className="h-5 w-5" />
                )
              ) : (
                <Loader2 className="h-4 w-4 animate-spin" />
              )}
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="truncate text-sm font-bold text-white">
                  {isFinished ? `Xong ${okCount}/${total} tệp` : `Đang xử lý ${settled}/${total} tệp`}
                </span>
                <span className="rounded-md bg-violet-500/20 px-1.5 py-0.5 font-mono text-[11px] font-bold text-violet-200">
                  {progressPercent}%
                </span>
              </div>
              <p className="truncate text-xs text-slate-500">
                {isFinished
                  ? "Bạn có thể tiếp tục dùng thư viện"
                  : active
                    ? `${STATUS_TEXT[active.status]}: ${active.fileName}`
                    : "Đang chuẩn bị..."}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-0.5">
            <button
              type="button"
              onClick={() => setIsExpanded(!isExpanded)}
              className="flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-slate-500 transition hover:bg-white/[0.06] hover:text-white"
            >
              Chi tiết
              {isExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronUp className="h-3 w-3" />}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-1.5 text-slate-500 transition hover:bg-white/[0.06] hover:text-white"
              aria-label="Đóng"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="h-1 bg-white/[0.06]">
          <div
            className="h-full bg-gradient-to-r from-violet-500 to-sky-400 transition-all duration-500"
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        {isExpanded && (
          <div ref={listRef} className="max-h-56 overflow-y-auto border-t border-white/[0.06] bg-ink-950/80">
            {tasks.map((task) => (
              <div
                key={task.id}
                className="flex items-start gap-2.5 border-b border-white/[0.04] px-3.5 py-2.5 last:border-b-0"
              >
                <span className="mt-0.5 shrink-0">
                  <TaskIcon status={task.status} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-xs font-semibold text-slate-200">{task.fileName}</span>
                  <span
                    className={`block truncate text-[11px] ${
                      task.status === "failed" ? "text-rose-300" : "text-slate-500"
                    }`}
                  >
                    {task.status === "failed" && task.error ? task.error : STATUS_TEXT[task.status]}
                  </span>
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
