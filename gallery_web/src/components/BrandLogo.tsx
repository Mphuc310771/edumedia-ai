import React from "react"

interface BrandLogoProps {
  size?: "sm" | "md" | "lg"
  showText?: boolean
  subtitle?: string
}

export const BrandIcon: React.FC<{ className?: string }> = ({ className = "h-6 w-6" }) => (
  <svg
    viewBox="0 0 40 40"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    aria-hidden="true"
  >
    <defs>
      <linearGradient id="aiPrismA" x1="6" y1="6" x2="34" y2="34" gradientUnits="userSpaceOnUse">
        <stop stopColor="#6366F1" />
        <stop offset="0.5" stopColor="#8B5CF6" />
        <stop offset="1" stopColor="#06B6D4" />
      </linearGradient>
      <linearGradient id="aiPrismB" x1="12" y1="8" x2="28" y2="32" gradientUnits="userSpaceOnUse">
        <stop stopColor="#38BDF8" stopOpacity="0.9" />
        <stop offset="1" stopColor="#818CF8" stopOpacity="0.4" />
      </linearGradient>
      <radialGradient id="aiCore" cx="20" cy="20" r="6" gradientUnits="userSpaceOnUse">
        <stop stopColor="#FFFFFF" />
        <stop offset="0.6" stopColor="#A5B4FC" />
        <stop offset="1" stopColor="#6366F1" stopOpacity="0" />
      </radialGradient>
      <filter id="aiGlow" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="2" result="blur" />
        <feComposite in="SourceGraphic" in2="blur" operator="over" />
      </filter>
    </defs>

    {/* Outer Isometric Facets */}
    <path
      d="M20 3L35 11.5V28.5L20 37L5 28.5V11.5L20 3Z"
      stroke="url(#aiPrismA)"
      strokeWidth="1.8"
      strokeLinejoin="round"
      className="opacity-90"
    />

    {/* Multimodal Neural Triad */}
    <path
      d="M20 3V20L35 28.5"
      stroke="url(#aiPrismB)"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M20 20L5 28.5"
      stroke="url(#aiPrismB)"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M20 20L5 11.5"
      stroke="url(#aiPrismA)"
      strokeWidth="1.2"
      strokeDasharray="2 3"
      className="opacity-60"
    />
    <path
      d="M20 20L35 11.5"
      stroke="url(#aiPrismA)"
      strokeWidth="1.2"
      strokeDasharray="2 3"
      className="opacity-60"
    />

    {/* Multimodal Peripheral Nodes */}
    <circle cx="20" cy="3" r="2" fill="#38BDF8" />
    <circle cx="35" cy="11.5" r="2" fill="#818CF8" />
    <circle cx="35" cy="28.5" r="2" fill="#A855F7" />
    <circle cx="20" cy="37" r="2" fill="#06B6D4" />
    <circle cx="5" cy="28.5" r="2" fill="#818CF8" />
    <circle cx="5" cy="11.5" r="2" fill="#38BDF8" />

    {/* Radiant AI Agent Core */}
    <circle cx="20" cy="20" r="5" fill="url(#aiCore)" filter="url(#aiGlow)" />
    <circle cx="20" cy="20" r="2" fill="#FFFFFF" />
  </svg>
)

export const BrandLogo: React.FC<BrandLogoProps> = ({
  size = "md",
  showText = true,
  subtitle = "Học liệu AI Đa phương thức",
}) => {
  const iconSizes = {
    sm: "h-8 w-8",
    md: "h-10 w-10",
    lg: "h-12 w-12",
  }

  const boxSizes = {
    sm: "h-8 w-8 rounded-lg",
    md: "h-10 w-10 rounded-xl",
    lg: "h-12 w-12 rounded-2xl",
  }

  return (
    <div className="flex items-center gap-3">
      <div
        className={`relative flex shrink-0 items-center justify-center ${boxSizes[size]} border border-indigo-500/25 bg-gradient-to-b from-indigo-950/80 via-slate-900/90 to-slate-950/90 shadow-[0_0_20px_rgba(99,102,241,0.22)] backdrop-blur-md`}
      >
        <div className="absolute inset-0 rounded-[inherit] bg-gradient-to-tr from-cyan-500/10 via-transparent to-indigo-500/15" />
        <BrandIcon className={iconSizes[size]} />
      </div>

      {showText && (
        <div className="min-w-0 leading-tight">
          <div className="flex items-center gap-1.5">
            <span className="text-[16px] font-black tracking-tight text-white">
              Agent<span className="bg-gradient-to-r from-indigo-400 via-sky-300 to-cyan-300 bg-clip-text text-transparent">Sys</span>
            </span>
            <span className="inline-flex items-center rounded-md border border-indigo-500/30 bg-indigo-500/15 px-1.5 py-0.5 text-[9px] font-bold tracking-wide text-indigo-300">
              AWS AI
            </span>
          </div>
          <div className="truncate text-xs font-medium text-slate-400">{subtitle}</div>
        </div>
      )}
    </div>
  )
}
