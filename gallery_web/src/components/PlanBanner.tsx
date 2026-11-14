import React from "react"
import { AlertCircle, AlertTriangle, Clock, Sparkles, Type, X } from "lucide-react"
import { SearchPlan } from "../types"

interface PlanBannerProps {
  plan: SearchPlan | null
  rationale: string
  onClear: () => void
}

export const PlanBanner: React.FC<PlanBannerProps> = ({ plan, rationale, onClear }) => {
  const source = plan?.planner_source || "heuristic"
  const isBedrock = source === "bedrock"
  const isThrottled = source === "bedrock_throttled"
  const isRateLimited = source === "bedrock_rate_limited"
  const isError = source === "bedrock_error"
  const isWarning = isThrottled || isRateLimited || isError

  const badgeConfig = isBedrock
    ? {
        label: "Bedrock planner",
        Icon: Sparkles,
        className: "bg-violet-500/20 text-violet-200 border-violet-400/30",
      }
    : isThrottled
      ? {
          label: "AWS Bedrock Quota",
          Icon: AlertTriangle,
          className: "bg-amber-500/20 text-amber-200 border-amber-400/30",
        }
      : isRateLimited
        ? {
            label: "AWS Bedrock Bận",
            Icon: Clock,
            className: "bg-amber-500/20 text-amber-200 border-amber-400/30",
          }
        : isError
          ? {
              label: "Lỗi AWS Bedrock",
              Icon: AlertCircle,
              className: "bg-rose-500/20 text-rose-200 border-rose-400/30",
            }
          : {
              label: "Tìm kiếm từ khóa",
              Icon: Type,
              className: "bg-white/[0.06] text-slate-300 border-white/[0.08]",
            }

  const BannerIcon = badgeConfig.Icon

  return (
    <div
      className={`mb-5 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-2xl border px-4 py-3 text-sm animate-fade-in ${
        isWarning
          ? "border-amber-400/20 bg-amber-500/[0.06]"
          : "border-violet-400/15 bg-violet-500/[0.06]"
      }`}
    >
      <span
        className={`flex shrink-0 items-center gap-1.5 rounded-lg border px-2 py-1 text-[11px] font-bold uppercase tracking-wide ${badgeConfig.className}`}
      >
        <BannerIcon className="h-3 w-3" />
        {badgeConfig.label}
      </span>

      <span className="min-w-0 flex-1 text-slate-300">{rationale}</span>

      {plan?.keywords && plan.keywords.length > 0 && (
        <span className="flex flex-wrap items-center gap-1">
          {plan.keywords.slice(0, 4).map((keyword) => (
            <span
              key={keyword}
              className="rounded-md border border-white/[0.08] bg-white/[0.05] px-1.5 py-0.5 font-mono text-[11px] text-slate-400"
            >
              {keyword}
            </span>
          ))}
        </span>
      )}

      <button
        type="button"
        onClick={onClear}
        className="rounded-lg p-1 text-slate-500 transition hover:bg-white/10 hover:text-white"
        aria-label="Đóng kết quả AI"
        title="Quay về lọc thường"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  )
}
