import React, { useState } from "react"
import { X, Sparkles, Copy, Check, Trash2, Cloud, FileText, Mic } from "lucide-react"
import { MediaItem } from "../types"

interface MediaDetailModalProps {
  item: MediaItem
  onClose: () => void
  onDelete?: (fileId: string) => Promise<void>
}

export const MediaDetailModal: React.FC<MediaDetailModalProps> = ({ item, onClose, onDelete }) => {
  const [activeTab, setActiveTab] = useState<"content" | "tech">("content")
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

  const hasTranscript = Boolean(item.transcript && !item.transcript.startsWith("Bản ghi đa phương tiện"))
  const hasOcr = Boolean(item.ocrText && item.ocrText.trim().length > 0)

  return (
    <div className="modal-overlay animate-fade-in" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        {/* Top Control Buttons */}
        <div className="absolute top-3 right-3 z-20 flex items-center gap-1.5">
          {onDelete && (
            <button
              onClick={() => void handleDelete()}
              disabled={deleting}
              title="Xóa tệp này"
              className="w-8 h-8 rounded-full bg-black/60 hover:bg-rose-500/20 hover:text-rose-400 border border-white/10 text-slate-400 flex items-center justify-center transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
          <button
            onClick={onClose}
            title="Đóng"
            className="w-8 h-8 rounded-full bg-black/60 hover:bg-white/20 border border-white/10 text-white flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Left Column: Media Player / Preview */}
        <div className="modal-media-col bg-slate-950">
          {item.type === "image" && (
            <>
              {item.url ? (
                <img
                  src={item.url}
                  alt={item.filename}
                  className="rounded-xl max-h-[75vh] object-contain shadow-2xl"
                />
              ) : (
                <div className="text-center p-8 text-slate-500 text-xs">
                  Không có hình ảnh xem trước
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
                  className="rounded-xl shadow-2xl max-h-[75vh]"
                />
              ) : (
                <div className="text-center p-8 text-slate-500 text-xs">
                  Video không khả dụng
                </div>
              )}
            </div>
          )}

          {item.type === "audio" && (
            <div className="p-6 text-center w-full max-w-sm">
              <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mx-auto mb-4 shadow-inner">
                <Mic className="w-8 h-8" />
              </div>
              <h4 className="font-semibold text-sm text-slate-100 mb-1 truncate">{item.filename}</h4>
              <p className="text-xs text-slate-400 mb-4 font-mono">{item.size}</p>

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

        {/* Right Column: Information Panel */}
        <div className="modal-info-col bg-slate-900/90 flex flex-col justify-between">
          {/* Header */}
          <div className="p-4 border-b border-white/10 bg-slate-950/40">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20">
                {item.categoryLabel || item.category}
              </span>
              <span className="text-xs text-slate-500">•</span>
              <span className="text-xs text-slate-400 font-mono">{item.size}</span>
            </div>
            <h3 className="text-sm font-bold text-white truncate" title={item.filename}>
              {item.filename}
            </h3>
            <p className="text-[11px] text-slate-400 mt-1 font-mono">
              Ngày tải lên: {item.date}
            </p>
          </div>

          {/* Simple Tab Bar */}
          <div className="flex border-b border-white/10 px-4 bg-white/[0.02]">
            <button
              onClick={() => setActiveTab("content")}
              className={`py-2.5 px-3 text-xs font-semibold border-b-2 flex items-center gap-1.5 transition-colors ${
                activeTab === "content"
                  ? "border-emerald-400 text-emerald-300"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              Thông tin & Nội dung
            </button>
            <button
              onClick={() => setActiveTab("tech")}
              className={`py-2.5 px-3 text-xs font-semibold border-b-2 flex items-center gap-1.5 transition-colors ${
                activeTab === "tech"
                  ? "border-emerald-400 text-emerald-300"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <Cloud className="w-3.5 h-3.5" />
              Thông số đám mây
            </button>
          </div>

          {/* Tab Body */}
          <div className="p-4 overflow-y-auto space-y-4 flex-1 max-h-[60vh]">
            {activeTab === "content" && (
              <div className="space-y-4 animate-fade-in">
                {/* AI Summary Box */}
                <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/10">
                  <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5 mb-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                    Tóm tắt nội dung
                  </span>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {item.summary || "Tài liệu đã được lưu trữ và lập chỉ mục tìm kiếm."}
                  </p>
                </div>

                {/* Speech Transcript Section (If Audio) */}
                {item.type === "audio" && (
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-bold text-slate-300">Nội dung lời thoại:</span>
                      {hasTranscript && (
                        <button
                          onClick={() => handleCopy(item.transcript)}
                          className="text-[11px] text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
                        >
                          {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                          <span>{copied ? "Đã chép" : "Sao chép"}</span>
                        </button>
                      )}
                    </div>
                    {hasTranscript ? (
                      <div className="p-3 rounded-xl bg-slate-950 border border-white/10 text-slate-200 text-xs leading-relaxed max-h-48 overflow-y-auto whitespace-pre-wrap">
                        {item.transcript}
                      </div>
                    ) : (
                      <div className="p-3 rounded-xl bg-slate-950/60 border border-white/5 text-slate-400 text-xs leading-relaxed">
                        Đoạn ghi âm dài {item.size}. Bấm phát âm thanh bên trái để nghe trực tiếp.
                      </div>
                    )}
                  </div>
                )}

                {/* OCR Text Section (If Image with text) */}
                {item.type === "image" && hasOcr && (
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-bold text-slate-300">Văn bản đọc được (OCR):</span>
                      <button
                        onClick={() => handleCopy(item.ocrText)}
                        className="text-[11px] text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
                      >
                        {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                        <span>{copied ? "Đã chép" : "Sao chép"}</span>
                      </button>
                    </div>
                    <div className="p-3 rounded-xl bg-slate-950 border border-white/10 text-slate-200 text-xs leading-relaxed max-h-40 overflow-y-auto whitespace-pre-wrap font-mono">
                      {item.ocrText}
                    </div>
                  </div>
                )}

                {/* Tags */}
                {item.tags && item.tags.length > 0 && (
                  <div>
                    <span className="text-xs font-bold text-slate-400 block mb-1.5">Đặc trưng nhận diện:</span>
                    <div className="flex flex-wrap gap-1.5">
                      {item.tags.map((tag) => (
                        <span
                          key={tag}
                          className="text-[11px] px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-slate-300 font-medium"
                        >
                          #{tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === "tech" && (
              <div className="space-y-3 animate-fade-in text-xs font-mono">
                <div className="p-3 rounded-xl bg-slate-950 border border-white/10 space-y-2.5">
                  <div>
                    <span className="text-slate-500 block text-[10px]">ĐỊNH DANH (ID DYNAMODB)</span>
                    <span className="text-emerald-400 text-xs break-all">{item.id}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">ĐƯỜNG DẪN CLOUD (S3 KEY)</span>
                    <span className="text-slate-300 text-xs break-all">{item.url ? item.url.split("?")[0] : "uploads/" + item.filename}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">KHU VỰC ĐÁM MÂY</span>
                    <span className="text-slate-300 text-xs">AWS US-EAST-1 (N. Virginia)</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">TRẠNG THÁI LẬP CHỈ MỤC</span>
                    <span className="text-emerald-400 text-xs font-bold">HOÀN TẤT (READY)</span>
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
