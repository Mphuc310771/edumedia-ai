import React from "react"
import { Activity, X } from "lucide-react"
import { HealthResponse } from "../types"

const LABELS: Record<string, string> = {
  api: "FastAPI",
  catalog: "Catalog",
  sts: "AWS STS",
  s3: "Amazon S3",
  dynamodb: "DynamoDB",
  rekognition: "Rekognition",
  transcribe: "Transcribe",
  bedrock: "Bedrock",
}

function statusClass(value: string) {
  if (value === "ONLINE") return "bg-emerald-500/15 text-emerald-300"
  if (value === "OFFLINE") return "bg-rose-500/15 text-rose-300"
  if (value === "SKIPPED") return "bg-white/[0.05] text-slate-500"
  return "bg-amber-500/15 text-amber-200"
}

export const DevPanel: React.FC<{ onClose: () => void; health: HealthResponse | null }> = ({
  onClose,
  health,
}) => {
  const components = health?.components || {}

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/70 backdrop-blur-sm animate-fade-in"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className="flex h-full w-full max-w-md flex-col border-l border-white/[0.08] bg-ink-900 p-6 shadow-pop"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-5 flex items-center justify-between border-b border-white/[0.06] pb-4">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500/25 to-sky-400/25 text-violet-300">
              <Activity className="h-5 w-5" />
            </span>
            <div>
              <h3 className="text-base font-extrabold text-white">Trạng thái dịch vụ</h3>
              <p className="text-xs text-slate-500">Ping thật từng service AWS</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-500 transition hover:bg-white/[0.06] hover:text-white"
            aria-label="Đóng"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mb-4 rounded-2xl surface p-4 text-sm">
          <div className="text-xs font-bold uppercase tracking-wide text-slate-600">Provider / môi trường</div>
          <div className="mt-1.5 font-semibold text-white">
            {health?.provider || "unknown"} · {health?.environment || "—"} · ingest {health?.ingest_mode || "sync"}
          </div>
          {health?.message ? <p className="mt-2 leading-relaxed text-slate-400">{health.message}</p> : null}
        </div>

        <div className="space-y-1.5 overflow-y-auto">
          {Object.entries(components).map(([key, value]) => (
            <div
              key={key}
              className="flex items-center justify-between rounded-xl surface px-3.5 py-2.5"
            >
              <span className="text-sm font-medium text-slate-200">{LABELS[key] || key}</span>
              <span className={`rounded-lg px-2 py-0.5 font-mono text-xs font-semibold ${statusClass(value)}`}>
                {value}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
