import React, { useState } from "react"
import { X, Sparkles, Eye, Mic, Server, Copy, Check, Trash2 } from "lucide-react"
import { MediaItem } from "../types"

interface MediaDetailModalProps {
  item: MediaItem
  onClose: () => void
  onDelete?: (fileId: string) => Promise<void>
}

type TabType = "summary" | "vision" | "speech" | "aws"

export const MediaDetailModal: React.FC<MediaDetailModalProps> = ({ item, onClose, onDelete }) => {
  const [activeTab, setActiveTab] = useState<TabType>("summary")
  const [copied, setCopied] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const handleCopy = (text?: string) => {
    if (!text) return
    void navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDelete = async () => {
    if (!onDelete || !confirm(`Bạn có chắc muốn xóa tệp "${item.filename}" không?`)) return
    setDeleting(true)
    try {
      await onDelete(item.id)
      onClose()
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="modal-overlay animate-fade-in" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        {/* Close & Delete Buttons */}
        <div className="absolute top-3 right-3 z-20 flex items-center gap-1.5">
          {onDelete && (
            <button
              onClick={() => void handleDelete()}
              disabled={deleting}
              aria-label="Xóa tệp"
              title="Xóa tệp này"
              className="w-8 h-8 rounded-full bg-black/70 hover:bg-rose-500/20 hover:text-rose-400 hover:border-rose-500/40 border border-white/10 text-slate-400 flex items-center justify-center transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
          <button
            onClick={onClose}
            aria-label="Đóng"
            className="w-8 h-8 rounded-full bg-black/70 hover:bg-white/20 border border-white/10 text-white flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Left Column: Media Preview */}
        <div className="modal-media-col">
          {item.type === "image" && (
            <>
              {item.url ? (
                <img
                  src={item.url}
                  alt={item.filename}
                  className="rounded-xl shadow-2xl"
                />
              ) : (
                <div className="text-center p-8 text-slate-500 font-mono text-xs">
                  Không có ảnh xem trước
                </div>
              )}
            </>
          )}

          {item.type === "video" && (
            <div className="w-full h-full flex items-center justify-center">
              {item.url ? (
                <video
                  controls
                  autoPlay
                  src={item.url}
                  poster={item.thumbnailUrl}
                  className="rounded-xl shadow-2xl"
                />
              ) : (
                <div className="text-center p-8 text-slate-500 font-mono text-xs">
                  Video không khả dụng
                </div>
              )}
            </div>
          )}

          {item.type === "audio" && (
            <div className="p-6 text-center w-full max-w-sm">
              <div className="w-16 h-16 rounded-2xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 mx-auto mb-4 shadow-xl">
                <Mic className="w-8 h-8" />
              </div>
              <h4 className="font-bold text-sm text-slate-100 mb-1 truncate">{item.filename}</h4>
              <p className="text-[11px] text-indigo-300 font-mono mb-4">Amazon Transcribe (vi-VN)</p>

              {item.url && (
                <audio
                  controls
                  src={item.url}
                  className="w-full rounded-lg"
                />
              )}
            </div>
          )}
        </div>

        {/* Right Column: AI Metadata Inspector */}
        <div className="modal-info-col">
          {/* Header Info */}
          <div className="p-4 border-b border-white/10 bg-slate-950/40">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                {item.categoryLabel || item.category}
              </span>
              <span className="text-xs text-slate-500">•</span>
              <span className="text-xs text-slate-400 font-mono">{item.size}</span>
            </div>
            <h3 className="font-mono text-sm font-bold text-white truncate" title={item.filename}>
              {item.filename}
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5 font-mono">
              {item.date} • Trạng thái: <span className="text-emerald-400 font-semibold">{item.status}</span>
            </p>
          </div>

          {/* Tab Navigation */}
          <div className="modal-tab-bar">
            <button
              onClick={() => setActiveTab("summary")}
              className={`modal-tab-btn ${activeTab === "summary" ? "active" : ""}`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              Tổng quan
            </button>
            <button
              onClick={() => setActiveTab("vision")}
              className={`modal-tab-btn ${activeTab === "vision" ? "active" : ""}`}
            >
              <Eye className="w-3.5 h-3.5" />
              Rekognition
            </button>
            <button
              onClick={() => setActiveTab("speech")}
              className={`modal-tab-btn ${activeTab === "speech" ? "active" : ""}`}
            >
              <Mic className="w-3.5 h-3.5" />
              Transcribe
            </button>
            <button
              onClick={() => setActiveTab("aws")}
              className={`modal-tab-btn ${activeTab === "aws" ? "active" : ""}`}
            >
              <Server className="w-3.5 h-3.5" />
              AWS Data
            </button>
          </div>

          {/* Tab Content Body */}
          <div className="modal-scroll-body space-y-3">
            {activeTab === "summary" && (
              <div className="space-y-3 animate-fade-in">
                <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                  <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5 mb-1">
                    <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                    Tóm tắt AI
                  </span>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {item.summary || "Đã phân tích và trích xuất đặc trưng đa phương thức."}
                  </p>
                </div>

                <div>
                  <span className="text-xs font-bold text-slate-400 block mb-1.5 font-mono">Pipeline Ingest:</span>
                  <ol className="space-y-1">
                    {(item.pipeline && item.pipeline.length > 0
                      ? item.pipeline
                      : ["S3 PutObject", "DynamoDB PutItem"]
                    ).map((step, index) => (
                      <li key={step} className="flex items-center gap-2 text-xs text-slate-300">
                        <span className="w-4 h-4 rounded bg-white/10 flex items-center justify-center font-mono text-[10px] text-emerald-400">
                          {index + 1}
                        </span>
                        {step}
                      </li>
                    ))}
                  </ol>
                </div>

                <div>
                  <span className="text-xs font-bold text-slate-400 block mb-1.5 font-mono">Thẻ nhận diện (Tags):</span>
                  <div className="flex flex-wrap gap-1">
                    {item.tags && item.tags.length > 0 ? (
                      item.tags.map((tag) => (
                        <span
                          key={tag}
                          className="text-[11px] px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 font-medium"
                        >
                          #{tag}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-slate-500">Chưa có tag</span>
                    )}
                  </div>
                </div>
              </div>
            )}

            {activeTab === "vision" && (
              <div className="space-y-3 animate-fade-in">
                <div>
                  <span className="text-xs font-bold text-slate-400 block mb-1.5 font-mono">Rekognition Labels:</span>
                  <div className="flex flex-wrap gap-1">
                    {item.labels && item.labels.length > 0 ? (
                      item.labels.map((label) => (
                        <span
                          key={label}
                          className="text-[11px] px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 font-mono"
                        >
                          {label}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-slate-500 font-mono">Không có label hình ảnh</span>
                    )}
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-bold text-slate-400 font-mono">Văn bản trích xuất OCR:</span>
                    {item.ocrText && (
                      <button
                        onClick={() => handleCopy(item.ocrText)}
                        className="text-[11px] text-cyan-400 flex items-center gap-1 hover:text-cyan-300"
                      >
                        {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        <span>{copied ? "Đã chép" : "Sao chép"}</span>
                      </button>
                    )}
                  </div>
                  {item.ocrText ? (
                    <pre className="p-3 rounded-xl bg-black/60 border border-white/10 text-slate-200 text-xs font-mono whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto">
                      {item.ocrText}
                    </pre>
                  ) : (
                    <div className="p-3 rounded-xl bg-black/30 border border-white/5 text-slate-500 text-xs font-mono">
                      Không phát hiện văn bản trong tệp này.
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === "speech" && (
              <div className="space-y-3 animate-fade-in">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-slate-400 font-mono">Bản dịch giọng nói (vi-VN):</span>
                  {item.transcript && (
                    <button
                      onClick={() => handleCopy(item.transcript)}
                      className="text-[11px] text-indigo-400 flex items-center gap-1 hover:text-indigo-300"
                    >
                      {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      <span>{copied ? "Đã chép" : "Sao chép"}</span>
                    </button>
                  )}
                </div>
                {item.transcript ? (
                  <div className="p-3 rounded-xl bg-indigo-950/20 border border-indigo-500/20 text-slate-200 text-xs leading-relaxed max-h-56 overflow-y-auto">
                    "{item.transcript}"
                  </div>
                ) : (
                  <div className="p-3 rounded-xl bg-black/30 border border-white/5 text-slate-500 text-xs font-mono">
                    Không có bản ghi âm / transcript cho tệp này.
                  </div>
                )}
              </div>
            )}

            {activeTab === "aws" && (
              <div className="space-y-3 animate-fade-in text-xs font-mono">
                <div className="p-3 rounded-xl bg-black/60 border border-white/10 space-y-2">
                  <div>
                    <span className="text-slate-500 block text-[10px]">FILE ID (PK DynamoDB)</span>
                    <span className="text-emerald-400 text-xs">{item.id}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">CATEGORY (GSI HASH)</span>
                    <span className="text-cyan-400 text-xs">{item.category}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">MEDIA TYPE</span>
                    <span className="text-indigo-400 text-xs">{item.type}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
