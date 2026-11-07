import React from "react"

interface SkeletonGridProps {
  count?: number
}

export const SkeletonGrid: React.FC<SkeletonGridProps> = ({ count = 6 }) => {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 animate-fade-in">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="relative aspect-[4/3] overflow-hidden rounded-2xl border border-white/[0.06] bg-ink-850 p-3 shadow-card"
          style={{ animationDelay: `${i * 80}ms` }}
        >
          {/* Top badges shimmer */}
          <div className="flex items-center justify-between">
            <div className="skeleton h-5 w-20 rounded-lg" />
            <div className="skeleton h-6 w-6 rounded-lg" />
          </div>

          {/* Center media icon placeholder */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="skeleton h-12 w-12 rounded-2xl opacity-60" />
          </div>

          {/* Bottom text shimmer lines */}
          <div className="absolute inset-x-3 bottom-3 space-y-2">
            <div className="skeleton h-4 w-3/4 rounded" />
            <div className="skeleton h-3 w-1/2 rounded opacity-70" />
          </div>
        </div>
      ))}
    </div>
  )
}
