import React, { useState } from "react"
import { ChevronDown, ChevronRight, LogOut, X } from "lucide-react"
import { CATEGORIES, DISCIPLINES, SubjectMeta } from "../catalog"
import { DisciplineId, HealthResponse, MediaItem, SmartCategory } from "../types"
import { BrandLogo } from "./BrandLogo"

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

type AccentTone = "violet" | "sky" | "amber" | "emerald" | "rose" | "teal"

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
  accent?: AccentTone
  onClick: () => void
}) {
  const activeClass =
    accent === "sky"
      ? "bg-sky-500/[0.12] text-sky-200 border-sky-400/20"
      : accent === "amber"
        ? "bg-amber-500/[0.12] text-amber-200 border-amber-400/20"
        : accent === "emerald"
          ? "bg-emerald-500/[0.12] text-emerald-200 border-emerald-400/20"
          : accent === "rose"
            ? "bg-rose-500/[0.12] text-rose-200 border-rose-400/20"
            : accent === "teal"
              ? "bg-teal-500/[0.12] text-teal-200 border-teal-400/20"
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

function disciplineAccent(id: DisciplineId): AccentTone {
  switch (id) {
    case "it":
      return "sky"
    case "business":
      return "emerald"
    case "healthcare":
      return "rose"
    case "social_law":
      return "violet"
    case "engineering":
      return "amber"
    case "natural_sciences":
      return "teal"
    case "general":
    default:
      return "amber"
  }
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
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    it: true,
    business: true,
  })

  const toggleSection = (id: string) => {
    setOpenSections((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  const categoryCount = (key: SmartCategory) =>
    key === "all" ? items.length : items.filter((item) => item.category === key).length
  const subjectCount = (key: string) => items.filter((item) => item.subject === key).length

  const degraded = health?.status === "DEGRADED"
  const offline = !health || health.status === "OFFLINE"
  const statusTone = offline ? "bg-rose-400" : degraded ? "bg-amber-400" : "bg-emerald-400"
  const statusText = offline ? "Mất kết nối API" : degraded ? "AWS thiếu dịch vụ" : "AWS hoạt động tốt"

  const subjectItem = (meta: SubjectMeta, accent: AccentTone) => (
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
        <BrandLogo size="md" subtitle="Smart Media Hub" />
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

        <SectionLabel>Khối ngành Đào tạo</SectionLabel>
        {DISCIPLINES.map((discipline) => {
          const totalInDiscipline = discipline.subjects.reduce(
            (sum, s) => sum + subjectCount(s.key),
            0,
          )
          const isExpanded =
            openSections[discipline.id] ??
            (totalInDiscipline > 0 ||
              discipline.id === "it" ||
              discipline.id === "business" ||
              discipline.subjects.some((s) => s.key === activeSubject))

          return (
            <div key={discipline.id} className="mt-3">
              <button
                type="button"
                onClick={() => toggleSection(discipline.id)}
                className="flex w-full items-center justify-between rounded-lg px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.12em] text-slate-400 hover:bg-white/[0.04] hover:text-slate-200 transition"
              >
                <span className="flex items-center gap-1.5 truncate">
                  <discipline.Icon className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                  <span className="truncate">{discipline.label}</span>
                </span>
                <div className="flex items-center gap-1.5 shrink-0">
                  {totalInDiscipline > 0 && (
                    <span className="rounded-md bg-white/[0.08] px-1.5 py-0.5 font-mono text-[10px] text-slate-300">
                      {totalInDiscipline}
                    </span>
                  )}
                  <ChevronDown
                    className={`h-3.5 w-3.5 text-slate-500 transition-transform duration-200 ${
                      isExpanded ? "rotate-180" : ""
                    }`}
                  />
                </div>
              </button>
              {isExpanded && (
                <div className="space-y-0.5 mt-1 pl-1">
                  {discipline.subjects.map((meta) =>
                    subjectItem(meta, disciplineAccent(discipline.id)),
                  )}
                </div>
              )}
            </div>
          )
        })}
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
