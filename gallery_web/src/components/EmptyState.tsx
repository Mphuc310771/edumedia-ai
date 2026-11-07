import React, { useRef } from "react"
import { FileText, Mic, Search, UploadCloud } from "lucide-react"

interface EmptyStateProps {
  onFiles: (files: File[]) => void
}

const FEATURES = [
  { Icon: FileText, label: "Đọc chữ trong ảnh", detail: "Amazon Rekognition OCR" },
  { Icon: Mic, label: "Gỡ băng ghi âm", detail: "Amazon Transcribe vi-VN" },
  { Icon: Search, label: "Tìm kiếm ngôn ngữ tự nhiên", detail: "Amazon Bedrock + Titan" },
]

export const EmptyState: React.FC<EmptyStateProps> = ({ onFiles }) => {
  const inputRef = useRef<HTMLInputElement | null>(null)

  return (
    <div className="flex flex-1 flex-col items-center justify-center py-12 animate-fade-in">
      <input
        ref={inputRef}
        type="file"
        multiple
        accept="image/*,audio/*,video/*"
        className="hidden"
        onChange={(e) => {
          if (e.target.files?.length) onFiles(Array.from(e.target.files))
          e.target.value = ""
        }}
      />

      <div
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click()
        }}
        className="group flex w-full max-w-2xl cursor-pointer flex-col items-center rounded-[2rem] border-2 border-dashed border-white/10 bg-white/[0.02] px-8 py-14 text-center transition hover:border-violet-400/50 hover:bg-violet-500/[0.04] focus:outline-none focus:ring-2 focus:ring-violet-400/50"
      >
        <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-sky-400 shadow-glow transition group-hover:scale-110">
          <UploadCloud className="h-8 w-8 text-white" />
        </div>
        <h2 className="mb-2 text-2xl font-extrabold tracking-tight text-white">
          Thư viện học liệu của bạn đang trống
        </h2>
        <p className="mb-7 max-w-md text-sm leading-relaxed text-slate-400">
          Kéo thả ảnh bài giảng, ghi âm hoặc video vào bất kỳ đâu trên màn hình. AI sẽ tự đọc nội dung,
          nhận diện môn học và xếp vào đúng ngăn.
        </p>
        <span className="btn-primary pointer-events-none">
          <UploadCloud className="h-4 w-4" />
          Chọn tệp từ máy
        </span>
      </div>

      <div className="mt-8 grid w-full max-w-2xl gap-3 sm:grid-cols-3">
        {FEATURES.map(({ Icon, label, detail }) => (
          <div key={label} className="flex items-start gap-3 rounded-2xl surface p-4">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-violet-500/10 text-violet-300">
              <Icon className="h-4 w-4" />
            </span>
            <span>
              <span className="block text-[13px] font-bold leading-tight text-slate-100">{label}</span>
              <span className="mt-1 block text-xs text-slate-500">{detail}</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
