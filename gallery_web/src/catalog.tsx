import {
  Activity,
  Atom,
  BookOpen,
  BookOpenCheck,
  Bot,
  Briefcase,
  Building2,
  Calculator,
  Clapperboard,
  Cloud,
  Code2,
  Cog,
  Cpu,
  Database,
  Dna,
  Dumbbell,
  FlaskConical,
  GraduationCap,
  HeartPulse,
  Landmark,
  Languages,
  Layers,
  LayoutGrid,
  LucideIcon,
  Megaphone,
  Mountain,
  Network,
  Newspaper,
  PawPrint,
  Pill,
  Presentation,
  Receipt,
  Scale,
  Shapes,
  ShieldCheck,
  Sigma,
  Stethoscope,
  TrendingUp,
  Truck,
  Users,
  UtensilsCrossed,
  Wrench,
  Zap,
} from "lucide-react"
import { DisciplineId, SmartCategory } from "./types"

export interface CategoryMeta {
  key: SmartCategory
  label: string
  Icon: LucideIcon
}

export interface SubjectMeta {
  key: string
  label: string
  Icon: LucideIcon
  discipline?: DisciplineId
}

export interface DisciplineGroup {
  id: DisciplineId
  label: string
  Icon: LucideIcon
  subjects: SubjectMeta[]
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

export const IT_SUBJECTS: SubjectMeta[] = [
  { key: "programming", label: "Lập trình", Icon: Code2, discipline: "it" },
  { key: "ai_ml", label: "Trí tuệ nhân tạo (AI/ML)", Icon: Bot, discipline: "it" },
  { key: "networks", label: "Mạng máy tính", Icon: Network, discipline: "it" },
  { key: "os", label: "Hệ điều hành", Icon: Cpu, discipline: "it" },
  { key: "database", label: "Cơ sở dữ liệu", Icon: Database, discipline: "it" },
  { key: "cloud", label: "Đám mây / AWS", Icon: Cloud, discipline: "it" },
  { key: "security", label: "An toàn thông tin", Icon: ShieldCheck, discipline: "it" },
  { key: "software_eng", label: "Công nghệ phần mềm", Icon: Layers, discipline: "it" },
]

export const BUSINESS_SUBJECTS: SubjectMeta[] = [
  { key: "economics", label: "Kinh tế học", Icon: TrendingUp, discipline: "business" },
  { key: "finance", label: "Tài chính - Ngân hàng", Icon: Landmark, discipline: "business" },
  { key: "accounting", label: "Kế toán - Kiểm toán", Icon: Calculator, discipline: "business" },
  { key: "marketing", label: "Marketing số", Icon: Megaphone, discipline: "business" },
  { key: "logistics", label: "Logistics & Chuỗi cung ứng", Icon: Truck, discipline: "business" },
  { key: "management", label: "Quản trị kinh doanh", Icon: Briefcase, discipline: "business" },
]

export const HEALTHCARE_SUBJECTS: SubjectMeta[] = [
  { key: "medicine", label: "Y đa khoa & Bệnh học", Icon: Stethoscope, discipline: "healthcare" },
  { key: "pharmacy", label: "Dược học & Dược lý", Icon: Pill, discipline: "healthcare" },
  { key: "nursing", label: "Điều dưỡng & Chăm sóc", Icon: HeartPulse, discipline: "healthcare" },
  { key: "public_health", label: "Y tế công cộng & Dinh dưỡng", Icon: Activity, discipline: "healthcare" },
]

export const SOCIAL_LAW_SUBJECTS: SubjectMeta[] = [
  { key: "law", label: "Pháp luật", Icon: Scale, discipline: "social_law" },
  { key: "media", label: "Báo chí & Truyền thông", Icon: Newspaper, discipline: "social_law" },
  { key: "english", label: "Tiếng Anh & Ngoại ngữ", Icon: Languages, discipline: "social_law" },
  { key: "philosophy", label: "Triết học & Lý luận chính trị", Icon: BookOpenCheck, discipline: "social_law" },
  { key: "psychology", label: "Tâm lý học & Xã hội", Icon: HeartPulse, discipline: "social_law" },
]

export const ENGINEERING_SUBJECTS: SubjectMeta[] = [
  { key: "automation", label: "Tự động hóa & Kỹ thuật", Icon: Cog, discipline: "engineering" },
  { key: "mechanical", label: "Kỹ thuật Cơ khí", Icon: Wrench, discipline: "engineering" },
  { key: "electrical", label: "Kỹ thuật Điện - Điện tử", Icon: Zap, discipline: "engineering" },
  { key: "construction", label: "Kỹ thuật Xây dựng & Kiến trúc", Icon: Building2, discipline: "engineering" },
]

export const SCIENCE_SUBJECTS: SubjectMeta[] = [
  { key: "math", label: "Toán học", Icon: Sigma, discipline: "natural_sciences" },
  { key: "physics", label: "Vật lý", Icon: Atom, discipline: "natural_sciences" },
  { key: "chemistry", label: "Hóa học", Icon: FlaskConical, discipline: "natural_sciences" },
  { key: "biology", label: "Sinh học & CNSH", Icon: Dna, discipline: "natural_sciences" },
  { key: "pedagogy", label: "Sư phạm & Giáo dục học", Icon: GraduationCap, discipline: "natural_sciences" },
]

export const GENERAL_SUBJECTS: SubjectMeta[] = [
  { key: "lecture", label: "Bài giảng chung & Đồ án", Icon: Presentation, discipline: "general" },
  { key: "pe", label: "GDTC / Quốc phòng", Icon: Dumbbell, discipline: "general" },
  { key: "off_major", label: "Kỹ năng mềm & Ngoài ngành", Icon: BookOpen, discipline: "general" },
]

export const DISCIPLINES: DisciplineGroup[] = [
  { id: "it", label: "CNTT & Trí Tuệ Nhân Tạo", Icon: Code2, subjects: IT_SUBJECTS },
  { id: "business", label: "Kinh Tế & Quản Trị", Icon: TrendingUp, subjects: BUSINESS_SUBJECTS },
  { id: "healthcare", label: "Y Dược & Sức Khỏe", Icon: Stethoscope, subjects: HEALTHCARE_SUBJECTS },
  { id: "social_law", label: "Khoa Học Xã Hội & Luật", Icon: Scale, subjects: SOCIAL_LAW_SUBJECTS },
  { id: "engineering", label: "Kỹ Thuật & Công Nghệ", Icon: Cog, subjects: ENGINEERING_SUBJECTS },
  { id: "natural_sciences", label: "Khoa Học Tự Nhiên & Sư Phạm", Icon: Sigma, subjects: SCIENCE_SUBJECTS },
  { id: "general", label: "Đại Cương & Kỹ Năng", Icon: Presentation, subjects: GENERAL_SUBJECTS },
]

// Backwards-compatible exports
export const MAJOR_SUBJECTS = IT_SUBJECTS
export const OFF_MAJOR_SUBJECT_LIST = [
  ...BUSINESS_SUBJECTS,
  ...HEALTHCARE_SUBJECTS,
  ...SOCIAL_LAW_SUBJECTS,
  ...ENGINEERING_SUBJECTS,
  ...SCIENCE_SUBJECTS,
]
export const OFF_MAJOR_UMBRELLA: SubjectMeta = {
  key: "off_major",
  label: "Ngoài ngành",
  Icon: BookOpen,
  discipline: "general",
}

export const ALL_SUBJECTS: SubjectMeta[] = [
  ...IT_SUBJECTS,
  ...BUSINESS_SUBJECTS,
  ...HEALTHCARE_SUBJECTS,
  ...SOCIAL_LAW_SUBJECTS,
  ...ENGINEERING_SUBJECTS,
  ...SCIENCE_SUBJECTS,
  ...GENERAL_SUBJECTS,
]

const SUBJECT_LOOKUP = new Map<string, SubjectMeta>(ALL_SUBJECTS.map((meta) => [meta.key, meta]))

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
