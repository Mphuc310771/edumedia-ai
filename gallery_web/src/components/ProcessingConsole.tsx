import React, { useEffect, useRef } from "react"
import { Terminal, CheckCircle2, AlertTriangle, Loader2, X, Minimize2, Maximize2, Cloud, Database, Cpu, Image as ImageIcon } from "lucide-react"

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
  isMinimized,
  onToggleMinimize,
  onClose,
  totalFiles,
  completedFiles,
  currentFileName,
  logs,
  provider = "aws",
}) => {
  const logContainerRef = useRef<HTMLDivElement | null>(null)

  // Auto-scroll to bottom of logs
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [logs])

  if (!isOpen) return null

  const progressPercent = totalFiles > 0 ? Math.round((completedFiles / totalFiles) * 100) : 0
  const isFinished = totalFiles > 0 && completedFiles >= totalFiles

  // Minimized floating status pill
  if (isMinimized) {
    return (
      <div className="fixed bottom-6 right-6 z-50 animate-fade-in">
        <div
          onClick={onToggleMinimize}
          className="cursor-pointer bg-slate-950/90 border border-emerald-500/40 hover:border-emerald-400/70 text-slate-100 px-4 py-3 rounded-2xl shadow-2xl backdrop-blur-xl flex items-center gap-3 transition-all hover:scale-105"
        >
          {isFinished ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          ) : (
            <Loader2 className="w-5 h-5 text-emerald-400 animate-spin shrink-0" />
          )}
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-white">
                {isFinished ? "Hoàn tất xử lý" : `Đang xử lý Cloud (${completedFiles}/${totalFiles})`}
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300">
                {progressPercent}%
              </span>
            </div>
            <span className="text-[11px] text-slate-400 max-w-[200px] truncate">
              {isFinished ? "57 tệp đã sẵn sàng trong kho" : currentFileName || "Đang truyền tải..."}
            </span>
          </div>
          <Maximize2 className="w-4 h-4 text-slate-400 hover:text-white shrink-0 ml-2" />
        </div>
      </div>
    )
  }

  // Full Terminal Console Modal
  return (
    <div className="fixed bottom-6 right-6 z-50 w-full max-w-xl animate-fade-in">
      <div className="bg-[#070C18]/95 border border-white/15 rounded-2xl shadow-2xl backdrop-blur-2xl overflow-hidden flex flex-col max-h-[500px] border-t-emerald-500/50">
        {/* Terminal Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-white/[0.03] border-b border-white/10">
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center">
              <Terminal className="w-3.5 h-3.5 text-emerald-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-white tracking-wide">AWS Cloud Processing Terminal</span>
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  {provider === "aws" ? "LIVE AWS US-EAST-1" : "LOCAL GPU"}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={onToggleMinimize}
              title="Thu nhỏ"
              className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
            >
              <Minimize2 className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              title="Đóng console"
              className="p-1 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-white/5 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Progress Bar & Current File */}
        <div className="px-4 py-3 bg-white/[0.015] border-b border-white/5 flex flex-col gap-2">
          <div className="flex items-center justify-between text-xs font-medium">
            <div className="flex items-center gap-2 text-slate-300">
              {isFinished ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              ) : (
                <Loader2 className="w-4 h-4 text-emerald-400 animate-spin shrink-0" />
              )}
              <span className="truncate max-w-[340px]">
                {isFinished ? "Hoàn tất xử lý toàn bộ tệp" : `Đang xử lý: ${currentFileName || "Chuẩn bị..."}`}
              </span>
            </div>
            <span className="font-mono text-emerald-400 text-xs">
              {completedFiles}/{totalFiles} ({progressPercent}%)
            </span>
          </div>

          {/* Progress Bar */}
          <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-emerald-500 via-teal-400 to-cyan-400 rounded-full transition-all duration-300 ease-out shadow-[0_0_10px_rgba(16,185,129,0.5)]"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          {/* Micro pipeline indicators */}
          <div className="flex items-center gap-3 text-[10px] text-slate-400 pt-1">
            <span className="flex items-center gap-1">
              <Cloud className="w-3 h-3 text-cyan-400" /> S3 Bucket
            </span>
            <span className="text-slate-600">→</span>
            <span className="flex items-center gap-1">
              <ImageIcon className="w-3 h-3 text-emerald-400" /> Rekognition OCR
            </span>
            <span className="text-slate-600">→</span>
            <span className="flex items-center gap-1">
              <Database className="w-3 h-3 text-amber-400" /> DynamoDB Index
            </span>
          </div>
        </div>

        {/* Live Terminal Log Stream */}
        <div
          ref={logContainerRef}
          className="flex-1 p-3.5 overflow-y-auto space-y-1.5 font-mono text-xs max-h-[280px] bg-black/40 scrollbar-thin scrollbar-thumb-white/10"
        >
          {logs.length === 0 ? (
            <div className="text-slate-500 text-center py-6">Đang lắng nghe sự kiện từ AWS Cloud...</div>
          ) : (
            logs.map((log) => {
              let color = "text-slate-300"
              let badge = "INFO"
              if (log.type === "success") {
                color = "text-emerald-400"
                badge = "OK"
              } else if (log.type === "aws") {
                color = "text-cyan-300"
                badge = "AWS"
              } else if (log.type === "warn") {
                color = "text-amber-300"
                badge = "WARN"
              } else if (log.type === "error") {
                color = "text-rose-400"
                badge = "ERR"
              }

              return (
                <div key={log.id} className="flex items-start gap-2 leading-relaxed hover:bg-white/[0.02] px-1 py-0.5 rounded transition-colors">
                  <span className="text-slate-500 text-[10px] shrink-0">{log.timestamp}</span>
                  <span
                    className={`text-[9px] px-1 py-0.2 rounded font-bold shrink-0 ${
                      log.type === "success"
                        ? "bg-emerald-500/20 text-emerald-300"
                        : log.type === "aws"
                        ? "bg-cyan-500/20 text-cyan-300"
                        : log.type === "warn"
                        ? "bg-amber-500/20 text-amber-300"
                        : log.type === "error"
                        ? "bg-rose-500/20 text-rose-300"
                        : "bg-white/10 text-slate-400"
                    }`}
                  >
                    {badge}
                  </span>
                  <span className={`${color} break-all flex-1 text-[11px]`}>{log.message}</span>
                </div>
              )
            })
          )}
        </div>

        {/* Footer info */}
        <div className="px-4 py-2 bg-white/[0.02] border-t border-white/5 flex items-center justify-between text-[10px] text-slate-400">
          <span>Tài nguyên: S3 • DynamoDB GSI • Rekognition</span>
          <span className="font-mono">{isFinished ? "Tất cả tệp đã hoàn thành" : "Đang xử lý tuần tự..."}</span>
        </div>
      </div>
    </div>
  )
}
