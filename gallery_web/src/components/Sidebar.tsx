import React from "react"
import { ChevronRight, GraduationCap, LogOut, X } from "lucide-react"
import {
  CATEGORIES,
  MAJOR_SUBJECTS,
  OFF_MAJOR_SUBJECT_LIST,
  OFF_MAJOR_UMBRELLA,
  SubjectMeta,
} from "../catalog"
import { HealthResponse, isOffMajorSubject, MediaItem, SmartCategory } from "../types"

interface SidebarProps {
  open: boolean
  onClose: () => void
  items: MediaItem[]
  activeCategory: SmartCategory
  activeSubject: string
  onSelectCategory: (category: SmartCategory) => void
  onSelectSubject: (subject: string) => void
  health: HealthResponse | null
  onOpenStatus: () => void
  onLogout?: () => void
}

function NavItem({
  Icon,
  label,
  count,
  active,
  accent = "violet",
  onClick,
}: {
  Icon: React.ComponentType<{ className?: string }>
  label: string
  count?: number
  active: boolean
  accent?: "violet" | "sky" | "amber"
  onClick: () => void
}) {
  const activeClass =
    accent === "sky"
      ? "bg-sky-500/[0.12] text-sky-200 border-sky-400/20"
      : accent === "amber"
        ? "bg-amber-500/[0.12] text-amber-200 border-amber-400/20"
        : "bg-violet-500/[0.14] text-violet-100 border-violet-400/25"

  return (
    <button
      type="button"
      onClick={onClick}
      className={`group flex w-full items-center gap-2.5 rounded-xl border px-3 py-2 text-left text-sm transition ${
        active
          ? `${activeClass} font-semibold`
          : "border-transparent text-slate-400 hover:bg-white/[0.05] hover:text-slate-100"
      }`}
    >
      <Icon className={`h-4 w-4 shrink-0 ${active ? "" : "opacity-70 group-hover:opacity-100"}`} />
      <span className="min-w-0 flex-1 truncate">{label}</span>
      {typeof count === "number" && count > 0 && (
        <span
          className={`rounded-md px-1.5 py-0.5 font-mono text-[11px] leading-none ${
            active ? "bg-white/10 text-inherit" : "bg-white/[0.06] text-slate-500"
          }`}
        >
          {count}
        </span>
      )}
    </button>
  )
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="px-3 pb-1.5 pt-5 text-[11px] font-bold uppercase tracking-[0.14em] text-slate-600">
      {children}
    </p>
  )
}

export const Sidebar: React.FC<SidebarProps> = ({
  open,
  onClose,
  items,
  activeCategory,
  activeSubject,
  onSelectCategory,
  onSelectSubject,
  health,
  onOpenStatus,
  onLogout,
}) => {
  const categoryCount = (key: SmartCategory) =>
    key === "all" ? items.length : items.filter((item) => item.category === key).length
  const subjectCount = (key: string) => items.filter((item) => item.subject === key).length
  const offMajorCount = items.filter((item) => isOffMajorSubject(item.subject)).length
  const visibleOffMajor = OFF_MAJOR_SUBJECT_LIST.filter((meta) => subjectCount(meta.key) > 0)

  const degraded = health?.status === "DEGRADED"
  const offline = !health || health.status === "OFFLINE"
  const statusTone = offline ? "bg-rose-400" : degraded ? "bg-amber-400" : "bg-emerald-400"
  const statusText = offline ? "Mất kết nối API" : degraded ? "AWS thiếu dịch vụ" : "AWS hoạt động tốt"

  const subjectItem = (meta: SubjectMeta, accent: "sky" | "amber") => (
    <NavItem
      key={meta.key}
      Icon={meta.Icon}
      label={meta.label}
      count={subjectCount(meta.key)}
      active={activeSubject === meta.key}
      accent={accent}
      onClick={() => onSelectSubject(activeSubject === meta.key ? "all" : meta.key)}
    />
  )

  const content = (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-3 px-4 pb-2 pt-5">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-sky-400 shadow-glow">
          <GraduationCap className="h-5 w-5 text-white" />
        </div>
        <div className="min-w-0 leading-tight">
          <div className="text-[15px] font-extrabold tracking-tight text-white">AgentSys</div>
          <div className="truncate text-xs text-slate-500">Thư viện học liệu AI</div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="ml-auto rounded-lg p-1.5 text-slate-500 hover:bg-white/[0.06] hover:text-white lg:hidden"
          aria-label="Đóng menu"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <nav className="min-h-0 flex-1 overflow-y-auto px-3 pb-4">
        <SectionLabel>Thư viện</SectionLabel>
        <div className="space-y-0.5">
          {CATEGORIES.filter((meta) => meta.key === "all" || categoryCount(meta.key) > 0).map((meta) => (
            <NavItem
              key={meta.key}
              Icon={meta.Icon}
              label={meta.label}
              count={categoryCount(meta.key)}
              active={activeSubject === "all" && activeCategory === meta.key}
              onClick={() => onSelectCategory(meta.key)}
            />
          ))}
        </div>

        <SectionLabel>Môn ngành CNTT</SectionLabel>
        <div className="space-y-0.5">{MAJOR_SUBJECTS.map((meta) => subjectItem(meta, "sky"))}</div>

        <SectionLabel>Ngoài ngành</SectionLabel>
        <div className="space-y-0.5">
          <NavItem
            Icon={OFF_MAJOR_UMBRELLA.Icon}
            label="Tất cả ngoài ngành"
            count={offMajorCount}
            active={activeSubject === "off_major"}
            accent="amber"
            onClick={() => onSelectSubject(activeSubject === "off_major" ? "all" : "off_major")}
          />
          {visibleOffMajor.map((meta) => subjectItem(meta, "amber"))}
        </div>
      </nav>

      <div className="border-t border-white/[0.06] p-3">
        <button
          type="button"
          onClick={onOpenStatus}
          className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left text-sm transition hover:bg-white/[0.05]"
        >
          <span className="relative flex h-2 w-2 shrink-0">
            {!offline && !degraded && (
              <span className={`absolute inline-flex h-full w-full animate-ping rounded-full ${statusTone} opacity-60`} />
            )}
            <span className={`relative inline-flex h-2 w-2 rounded-full ${statusTone}`} />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate font-medium text-slate-200">{statusText}</span>
            <span className="block truncate text-xs text-slate-500">
              {items.length} tệp trong thư viện
            </span>
          </span>
          <ChevronRight className="h-4 w-4 shrink-0 text-slate-600" />
        </button>
        {onLogout && (
          <button type="button" onClick={onLogout} className="btn-ghost mt-1 w-full justify-start text-slate-500">
            <LogOut className="h-4 w-4" />
            Đăng xuất
          </button>
        )}
      </div>
    </div>
  )

  return (
    <>
      {/* Desktop */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[280px] border-r border-white/[0.06] bg-ink-900/80 backdrop-blur-xl lg:block">
        {content}
      </aside>

      {/* Mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true">
          <div className="absolute inset-0 bg-black/70 backdrop-blur-sm animate-fade-in" onClick={onClose} />
          <aside className="absolute inset-y-0 left-0 w-[290px] max-w-[85vw] border-r border-white/[0.08] bg-ink-900 shadow-pop animate-slide-in-left">
            {content}
          </aside>
        </div>
      )}
    </>
  )
}
