import React from "react"

interface BrandLogoProps {
  size?: "sm" | "md" | "lg"
  showText?: boolean
  subtitle?: string
}

export const BrandIcon: React.FC<{ className?: string }> = ({ className = "h-6 w-6" }) => (
  <svg
    viewBox="0 0 44 44"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    aria-hidden="true"
  >
    <defs>
      <linearGradient id="bookPageLeft" x1="4" y1="16" x2="22" y2="38" gradientUnits="userSpaceOnUse">
        <stop stopColor="#818CF8" />
        <stop offset="1" stopColor="#4F46E5" />
      </linearGradient>
      <linearGradient id="bookPageRight" x1="22" y1="16" x2="40" y2="38" gradientUnits="userSpaceOnUse">
        <stop stopColor="#38BDF8" />
        <stop offset="1" stopColor="#0284C7" />
      </linearGradient>
      <linearGradient id="aiSparkGrad" x1="16" y1="4" x2="28" y2="18" gradientUnits="userSpaceOnUse">
        <stop stopColor="#F8FAFC" />
        <stop offset="0.4" stopColor="#38BDF8" />
        <stop offset="1" stopColor="#818CF8" />
      </linearGradient>
      <filter id="aiStarGlow" x="-30%" y="-30%" width="160%" height="160%">
        <feGaussianBlur stdDeviation="2" result="blur" />
        <feComposite in="SourceGraphic" in2="blur" operator="over" />
      </filter>
    </defs>

    {/* --- Open Book of Knowledge (Học liệu / Tri thức / Sách vở) --- */}
    {/* Left Page */}
    <path
      d="M22 36.5C17 33 10 33 4.5 35.5V17.5C10 15 17 15 22 18.5V36.5Z"
      fill="url(#bookPageLeft)"
      fillOpacity="0.25"
      stroke="url(#bookPageLeft)"
      strokeWidth="2"
      strokeLinejoin="round"
    />
    {/* Left Page Text Lines (Trang sách) */}
    <path d="M8.5 21C11.5 20 15 20.2 18 21.5" stroke="#A5B4FC" strokeWidth="1.3" strokeLinecap="round" strokeOpacity="0.7" />
    <path d="M8.5 25C11.5 24 15 24.2 18 25.5" stroke="#A5B4FC" strokeWidth="1.3" strokeLinecap="round" strokeOpacity="0.7" />
    <path d="M8.5 29C11.5 28 15 28.2 18 29.5" stroke="#A5B4FC" strokeWidth="1.3" strokeLinecap="round" strokeOpacity="0.5" />

    {/* Right Page */}
    <path
      d="M22 36.5C27 33 34 33 39.5 35.5V17.5C34 15 27 15 22 18.5V36.5Z"
      fill="url(#bookPageRight)"
      fillOpacity="0.25"
      stroke="url(#bookPageRight)"
      strokeWidth="2"
      strokeLinejoin="round"
    />
    {/* Right Page Text Lines (Trang sách) */}
    <path d="M26 21.5C29 20.2 32.5 20 35.5 21" stroke="#7DD3FC" strokeWidth="1.3" strokeLinecap="round" strokeOpacity="0.7" />
    <path d="M26 25.5C29 24.2 32.5 24 35.5 25" stroke="#7DD3FC" strokeWidth="1.3" strokeLinecap="round" strokeOpacity="0.7" />
    <path d="M26 29.5C29 28.2 32.5 28 35.5 29" stroke="#7DD3FC" strokeWidth="1.3" strokeLinecap="round" strokeOpacity="0.5" />

    {/* Spine / Gáy sách */}
    <path d="M22 18.5V37" stroke="#E0E7FF" strokeWidth="2.2" strokeLinecap="round" />

    {/* --- Rising AI Spark of Intelligence (Trí tuệ nhân tạo AI) --- */}
    {/* Neural connection rays from book into AI core */}
    <path d="M15 15L22 10L29 15" stroke="#38BDF8" strokeWidth="1.2" strokeDasharray="2 2" strokeOpacity="0.8" />
    <circle cx="15" cy="15" r="1.5" fill="#818CF8" />
    <circle cx="29" cy="15" r="1.5" fill="#38BDF8" />

    {/* 4-point Radiant AI Intelligence Star */}
    <path
      d="M22 2C22.4 5.5 24.5 7.6 28 8C24.5 8.4 22.4 10.5 22 14C21.6 10.5 19.5 8.4 16 8C19.5 7.6 21.6 5.5 22 2Z"
      fill="url(#aiSparkGrad)"
      filter="url(#aiStarGlow)"
    />

    {/* Glowing Center Core */}
    <circle cx="22" cy="8" r="1.5" fill="#FFFFFF" />
  </svg>
)

export const BrandLogo: React.FC<BrandLogoProps> = ({
  size = "md",
  showText = true,
  subtitle = "Thư viện Học liệu AI",
}) => {
  const iconSizes = {
    sm: "h-7 w-7",
    md: "h-9 w-9",
    lg: "h-11 w-11",
  }

  const boxSizes = {
    sm: "h-9 w-9 rounded-lg p-1",
    md: "h-11 w-11 rounded-xl p-1.5",
    lg: "h-14 w-14 rounded-2xl p-2",
  }

  return (
    <div className="flex items-center gap-3">
      <div
        className={`relative flex shrink-0 items-center justify-center ${boxSizes[size]} border border-indigo-500/30 bg-gradient-to-b from-indigo-950/90 via-slate-900/95 to-slate-950 shadow-[0_0_24px_rgba(79,70,229,0.28)] backdrop-blur-md`}
      >
        <div className="absolute inset-0 rounded-[inherit] bg-gradient-to-tr from-sky-500/10 via-transparent to-indigo-500/20" />
        <BrandIcon className={iconSizes[size]} />
      </div>

      {showText && (
        <div className="min-w-0 leading-tight">
          <div className="flex items-center gap-1.5">
            <span className="text-[16px] font-black tracking-tight text-white">
              Edu<span className="bg-gradient-to-r from-indigo-400 via-sky-300 to-cyan-300 bg-clip-text text-transparent">Media AI</span>
            </span>
            <span className="inline-flex items-center rounded-md border border-indigo-500/30 bg-indigo-500/15 px-1.5 py-0.5 text-[9px] font-bold tracking-wide text-indigo-300">
              Học liệu AI
            </span>
          </div>
          <div className="truncate text-xs font-medium text-slate-400">{subtitle}</div>
        </div>
      )}
    </div>
  )
}
