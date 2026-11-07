import {
  Atom,
  BookOpen,
  Clapperboard,
  Cloud,
  Code2,
  Cpu,
  Database,
  Dna,
  Dumbbell,
  FlaskConical,
  GraduationCap,
  Landmark,
  Languages,
  LayoutGrid,
  LucideIcon,
  Mountain,
  Network,
  PawPrint,
  Presentation,
  Receipt,
  Scale,
  Shapes,
  Sigma,
  TrendingUp,
  Users,
  UtensilsCrossed,
} from "lucide-react"
import { SmartCategory } from "./types"

export interface CategoryMeta {
  key: SmartCategory
  label: string
  Icon: LucideIcon
}

export interface SubjectMeta {
  key: string
  label: string
  Icon: LucideIcon
}

export const CATEGORIES: CategoryMeta[] = [
  { key: "all", label: "Tất cả", Icon: LayoutGrid },
  { key: "study", label: "Học tập", Icon: GraduationCap },
  { key: "people", label: "Con người", Icon: Users },
  { key: "pets", label: "Thú cưng", Icon: PawPrint },
  { key: "food", label: "Ẩm thực", Icon: UtensilsCrossed },
  { key: "receipts", label: "Hóa đơn", Icon: Receipt },
  { key: "scenes", label: "Cảnh quan", Icon: Mountain },
  { key: "videos", label: "Video", Icon: Clapperboard },
  { key: "other", label: "Khác", Icon: Shapes },
]

export const MAJOR_SUBJECTS: SubjectMeta[] = [
  { key: "math", label: "Toán", Icon: Sigma },
  { key: "os", label: "Hệ điều hành", Icon: Cpu },
  { key: "networks", label: "Mạng máy tính", Icon: Network },
  { key: "programming", label: "Lập trình", Icon: Code2 },
  { key: "database", label: "Cơ sở dữ liệu", Icon: Database },
  { key: "cloud", label: "Đám mây / AWS", Icon: Cloud },
  { key: "lecture", label: "Bài giảng chung", Icon: Presentation },
]

export const OFF_MAJOR_SUBJECT_LIST: SubjectMeta[] = [
  { key: "english", label: "Tiếng Anh", Icon: Languages },
  { key: "physics", label: "Vật lý", Icon: Atom },
  { key: "chemistry", label: "Hóa học", Icon: FlaskConical },
  { key: "biology", label: "Sinh học", Icon: Dna },
  { key: "economics", label: "Kinh tế", Icon: TrendingUp },
  { key: "law", label: "Pháp luật", Icon: Scale },
  { key: "philosophy", label: "Lý luận chính trị", Icon: Landmark },
  { key: "pe", label: "GDTC / Quốc phòng", Icon: Dumbbell },
]

export const OFF_MAJOR_UMBRELLA: SubjectMeta = {
  key: "off_major",
  label: "Ngoài ngành",
  Icon: BookOpen,
}

const SUBJECT_LOOKUP = new Map<string, SubjectMeta>(
  [...MAJOR_SUBJECTS, ...OFF_MAJOR_SUBJECT_LIST, OFF_MAJOR_UMBRELLA].map((meta) => [meta.key, meta]),
)

export function subjectMeta(key?: string): SubjectMeta | undefined {
  return key ? SUBJECT_LOOKUP.get(key) : undefined
}

export function categoryMeta(key?: string): CategoryMeta | undefined {
  return CATEGORIES.find((meta) => meta.key === key)
}

export type ViewMode = "grid" | "list"

export type SortMode = "relevance" | "newest" | "oldest" | "name" | "size"

export const SORT_OPTIONS: { key: SortMode; label: string }[] = [
  { key: "newest", label: "Mới nhất" },
  { key: "oldest", label: "Cũ nhất" },
  { key: "name", label: "Tên A→Z" },
  { key: "size", label: "Dung lượng" },
]

export const RELEVANCE_OPTION: { key: SortMode; label: string } = {
  key: "relevance",
  label: "Liên quan nhất",
}

const SIZE_UNITS: Record<string, number> = { B: 1, KB: 1024, MB: 1024 ** 2, GB: 1024 ** 3 }

export function parseSize(size: string): number {
  const match = /([\d.]+)\s*(B|KB|MB|GB)/i.exec(size || "")
  if (!match) return 0
  return parseFloat(match[1]) * (SIZE_UNITS[match[2].toUpperCase()] || 1)
}
