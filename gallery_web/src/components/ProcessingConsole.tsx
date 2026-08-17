import React, { useEffect, useRef, useState } from "react"
import { CheckCircle2, Loader2, X, ChevronUp, ChevronDown } from "lucide-react"

export interface ConsoleLog {
  id: string
  timestamp: string
  message: string
  type: "info" | "success" | "warn" | "error" | "aws"
  service?: "s3" | "rekognition" | "transcribe" | "dynamodb" | "bedrock"
}

interface ProcessingConsoleProps {
  isOpen: boolean
  isMinimized: boolean
  onToggleMinimize: () => void
  onClose: () => void
  totalFiles: number
  completedFiles: number
  currentFileName: string
  logs: ConsoleLog[]
  provider?: string
}

export const ProcessingConsole: React.FC<ProcessingConsoleProps> = ({
  isOpen,
  onClose,
  totalFiles,
  completedFiles,
  currentFileName,
  logs,
}) => {
  const logContainerRef = useRef<HTMLDivElement | null>(null)
  const [isExpanded, setIsExpanded] = useState(false)

  // Auto-scroll to bottom of logs
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [logs])

  // Auto-close 5s after 100% completion
  useEffect(() => {
    if (totalFiles > 0 && completedFiles >= totalFiles) {
      const timer = setTimeout(() => {
        onClose()
      }, 5000)
      return () => clearTimeout(timer)
    }
  }, [completedFiles, totalFiles, onClose])

  if (!isOpen) return null

  const progressPercent = totalFiles > 0 ? Math.round((completedFiles / totalFiles) * 100) : 0
  const isFinished = totalFiles > 0 && completedFiles >= totalFiles

  return (
    <div
      style={{
        position: "fixed",
        bottom: "24px",
        right: "24px",
        top: "auto",
        left: "auto",
        zIndex: 9999,
      }}
      className="animate-fade-in max-w-sm w-[380px] pointer-events-auto select-none"
    >
      <div className="bg-slate-950/95 border border-white/20 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.8)] backdrop-blur-2xl overflow-hidden flex flex-col">
        {/* Compact Floating Status Header (Default View) */}
        <div className="p-3 flex items-center justify-between gap-2.5 bg-white/[0.03]">
          <div className="flex items-center gap-2.5 min-w-0 flex-1">
            {isFinished ? (
              <div className="w-7 h-7 rounded-lg bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center shrink-0">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              </div>
            ) : (
              <div className="w-7 h-7 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center shrink-0">
                <Loader2 className="w-4 h-4 text-emerald-400 animate-spin" />
              </div>
            )}

            <div className="flex flex-col min-w-0 flex-1">
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-semibold text-white truncate">
                  {isFinished ? "Đã tải lên hoàn tất" : `Đang tải lên AWS (${completedFiles}/${totalFiles})`}
                </span>
                <span className="text-[10px] font-mono font-bold px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 shrink-0">
                  {progressPercent}%
                </span>
              </div>
              <span className="text-[10px] text-slate-400 truncate">
                {isFinished ? "Tất cả tệp đã sẵn sàng trong kho" : currentFileName || "Đang truyền tải dữ liệu..."}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-0.5 shrink-0">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="px-2 py-1 rounded-md text-[10px] font-medium text-slate-400 hover:text-white hover:bg-white/10 transition-colors flex items-center gap-1"
            >
              <span>{isExpanded ? "Thu gọn" : "Nhật ký"}</span>
              {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
            </button>
            <button
              onClick={onClose}
              className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Minimal Progress Bar */}
        <div className="w-full h-1 bg-white/10 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-300 ease-out"
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        {/* Expandable Activity Log Stream (Clean & Pure Vietnamese) */}
        {isExpanded && (
          <div
            ref={logContainerRef}
            className="p-3 overflow-y-auto space-y-1.5 font-mono text-[10px] max-h-40 bg-black/70 border-t border-white/10 scrollbar-thin"
          >
            {logs.map((log) => (
              <div key={log.id} className="flex items-start gap-1.5 leading-relaxed text-slate-300">
                <span className="text-slate-500 text-[9px] shrink-0">{log.timestamp}</span>
                <span
                  className={`text-[9px] px-1 py-0.2 rounded font-bold shrink-0 ${
                    log.type === "success"
                      ? "bg-emerald-500/20 text-emerald-300"
                      : log.type === "warn"
                      ? "bg-amber-500/20 text-amber-300"
                      : "bg-white/10 text-slate-400"
                  }`}
                >
                  {log.type === "success" ? "XONG" : log.type === "warn" ? "LƯU" : "TIẾP"}
                </span>
                <span className="break-all flex-1 text-slate-300">{log.message}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
