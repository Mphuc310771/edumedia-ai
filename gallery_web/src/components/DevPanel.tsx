import React from "react"
import { Layers, X, ShieldCheck, Zap, Database, Brain, HardDrive, Bell, Terminal, CheckCircle2 } from "lucide-react"

interface DevPanelProps {
  onClose: () => void
  provider: string
}

interface ServiceCard {
  name: string
  service: string
  role: string
  badge: string
  icon: React.ElementType
  color: string
}

const AWS_SERVICES: ServiceCard[] = [
  {
    name: "Amazon S3",
    service: "Media Bucket",
    role: "Lưu trữ media bảo mật, mã hóa SSE-S3, kích hoạt S3:ObjectCreated notification tới SQS",
    badge: "Storage & Events",
    icon: HardDrive,
    color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10",
  },
  {
    name: "Amazon SQS + DLQ",
    service: "Message Buffer",
    role: "Đệm chịu tải burst ingest, Dead-Letter Queue tự động cô lập lỗi sau 3 lần retry",
    badge: "Decoupling",
    icon: Zap,
    color: "text-amber-400 border-amber-500/30 bg-amber-500/10",
  },
  {
    name: "AWS Lambda",
    service: "Ingest & HTTP API",
    role: "FastAPI + Mangum xử lý REST API, Ingest Worker điều phối AI serverless không tốn chi phí rỗi",
    badge: "Compute",
    icon: Zap,
    color: "text-orange-400 border-orange-500/30 bg-orange-500/10",
  },
  {
    name: "Amazon Rekognition",
    service: "Computer Vision AI",
    role: "Tự động phân tích DetectLabels (vật thể/khung cảnh) và DetectText (bóc chữ OCR trên bảng/hóa đơn)",
    badge: "Vision AI",
    icon: Brain,
    color: "text-cyan-400 border-cyan-500/30 bg-cyan-500/10",
  },
  {
    name: "Amazon Transcribe",
    service: "Speech-to-Text vi-VN",
    role: "Nhận diện giọng nói bài giảng tiếng Việt và chuyển đổi thành văn bản có dấu",
    badge: "Speech AI",
    icon: Brain,
    color: "text-indigo-400 border-indigo-500/30 bg-indigo-500/10",
  },
  {
    name: "Amazon DynamoDB",
    service: "Metadata Catalog",
    role: "NoSQL Database Pay-per-Request lưu trữ chỉ mục, Global Secondary Index category-index",
    badge: "Database",
    icon: Database,
    color: "text-blue-400 border-blue-500/30 bg-blue-500/10",
  },
  {
    name: "Amazon Bedrock",
    service: "GenAI Query Planner",
    role: "Mô hình Claude 3.5 / Nova Lite phân tích câu hỏi tự nhiên tiếng Việt thành Search Plan",
    badge: "Generative AI",
    icon: Brain,
    color: "text-purple-400 border-purple-500/30 bg-purple-500/10",
  },
  {
    name: "Amazon CloudWatch",
    service: "Observability & Alarms",
    role: "Custom Metrics AgentSys, Alarms Lambda Errors, MediaIngestFailed và SQS DLQ Messages",
    badge: "Monitoring",
    icon: Bell,
    color: "text-rose-400 border-rose-500/30 bg-rose-500/10",
  },
]

export const DevPanel: React.FC<DevPanelProps> = ({ onClose, provider }) => {
  const isAws = provider === "aws"

  return (
    <div
      className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex justify-end animate-fade-in"
      role="dialog"
      aria-modal="true"
    >
      <div className="w-full max-w-xl bg-[#0B101D] border-l border-white/10 p-6 overflow-y-auto flex flex-col justify-between shadow-2xl">
        <div>
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-white/10 mb-5">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center">
                <Layers className="w-4 h-4 text-cyan-400" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white tracking-tight">Kiến trúc Cloud FCAJ</h3>
                <span className="text-[11px] text-slate-400 font-mono">AgentSys SAM Stack • AWS Vietnam</span>
              </div>
            </div>
            <button
              onClick={onClose}
              aria-label="Đóng"
              className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/15 text-slate-400 hover:text-white flex items-center justify-center transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Runtime Status Pill */}
          <div className="mb-5 p-3.5 rounded-2xl bg-slate-900/90 border border-white/10 flex items-center justify-between">
            <div>
              <div className="text-[11px] text-slate-400 font-mono">Môi trường thực thi:</div>
              <div className="text-xs font-bold text-white flex items-center gap-2 mt-0.5">
                <span
                  className={`w-2 h-2 rounded-full ${isAws ? "bg-emerald-400 animate-pulse" : "bg-cyan-400"}`}
                ></span>
                {isAws ? "AWS Cloud Production" : "Local In-Memory Mode"}
              </div>
            </div>
            <span className="text-[10px] font-mono px-2 py-1 rounded-md bg-white/5 border border-white/10 text-emerald-400">
              Provider: {provider}
            </span>
          </div>

          {/* Cloud Security Checklist */}
          <div className="mb-5 p-3.5 rounded-2xl bg-emerald-500/5 border border-emerald-500/20 text-xs text-emerald-300 flex items-start gap-2.5">
            <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <strong className="text-emerald-200">Chuẩn bảo mật AWS Least Privilege:</strong>
              <p className="text-[11px] text-slate-300 mt-0.5">
                Không chứa Access Key tĩnh. Toàn bộ quyền truy cập S3/DynamoDB/AI được cấp qua IAM Role riêng biệt cho từng hàm Lambda.
              </p>
            </div>
          </div>

          {/* Services List */}
          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider font-mono mb-3">
            Dịch vụ AWS đã tích hợp ({AWS_SERVICES.length})
          </h4>
          <div className="space-y-2.5">
            {AWS_SERVICES.map((svc) => {
              const Icon = svc.icon
              return (
                <div
                  key={svc.name}
                  className="p-3 rounded-xl bg-slate-900/60 border border-white/5 hover:border-white/15 transition-all"
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <div className={`p-1.5 rounded-lg border ${svc.color}`}>
                        <Icon className="w-3.5 h-3.5" />
                      </div>
                      <span className="font-bold text-xs text-white">{svc.name}</span>
                      <span className="text-[11px] text-slate-400 font-mono">• {svc.service}</span>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-white/5 text-slate-300">
                      {svc.badge}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 pl-8 leading-relaxed">{svc.role}</p>
                </div>
              )
            })}
          </div>
        </div>

        {/* Footer Commands */}
        <div className="pt-4 border-t border-white/10 mt-6 text-xs text-slate-500 font-mono">
          <div className="flex items-center gap-1.5 text-slate-400 mb-1">
            <Terminal className="w-3.5 h-3.5 text-cyan-400" />
            <span>Triển khai tự động bằng AWS SAM:</span>
          </div>
          <code className="block p-2 rounded-lg bg-black/60 border border-white/10 text-emerald-400 text-[11px]">
            sam build -t infra/template.yaml && sam deploy
          </code>
        </div>
      </div>
    </div>
  )
}
