import React, { useMemo } from "react"

const VI_CHAR_MAP: Record<string, string> = {
  à: "a", á: "a", ả: "a", ã: "a", ạ: "a",
  ă: "a", ằ: "a", ắ: "a", ẳ: "a", ẵ: "a", ặ: "a",
  â: "a", ầ: "a", ấ: "a", ẩ: "a", ẫ: "a", ậ: "a",
  đ: "d",
  è: "e", é: "e", ẻ: "e", ẽ: "e", ẹ: "e",
  ê: "e", ề: "e", ế: "e", ể: "e", ễ: "e", ệ: "e",
  ì: "i", í: "i", ỉ: "i", ĩ: "i", ị: "i",
  ò: "o", ó: "o", ỏ: "o", õ: "o", ọ: "o",
  ô: "o", ồ: "o", ố: "o", ổ: "o", ỗ: "o", ộ: "o",
  ơ: "o", ờ: "o", ớ: "o", ở: "o", ỡ: "o", ợ: "o",
  ù: "u", ú: "u", ủ: "u", ũ: "u", ụ: "u",
  ư: "u", ứ: "u", ừ: "u", ử: "u", ữ: "u", ự: "u",
  ỳ: "y", ý: "y", ỷ: "y", ỹ: "y", ỵ: "y",
  À: "a", Á: "a", Ả: "a", Ã: "a", Ạ: "a",
  Ă: "a", Ằ: "a", Ắ: "a", Ẳ: "a", Ẵ: "a", Ặ: "a",
  Â: "a", Ầ: "a", Ấ: "a", Ẩ: "a", Ẫ: "a", Ậ: "a",
  Đ: "d",
  È: "e", É: "e", Ẻ: "e", Ẽ: "e", Ẹ: "e",
  Ê: "e", Ề: "e", Ế: "e", Ể: "e", Ễ: "e", Ệ: "e",
  Ì: "i", Í: "i", Ỉ: "i", Ĩ: "i", Ị: "i",
  Ò: "o", Ó: "o", Ỏ: "o", Õ: "o", Ọ: "o",
  Ô: "o", Ồ: "o", Ố: "o", Ổ: "o", Ỗ: "o", Ộ: "o",
  Ơ: "o",Ờ: "o", Ớ: "o", Ở: "o", Ỡ: "o", Ợ: "o",
  Ù: "u", Ú: "u", Ủ: "u", Ũ: "u", Ụ: "u",
  Ư: "u", Ừ: "u", Ứ: "u", Ử: "u", Ữ: "u", Ự: "u",
  Ỳ: "y", Ý: "y", Ỷ: "y", Ỹ: "y", Ỵ: "y",
}

/**
 * Normalizes text to unaccented lowercase while strictly preserving 1-to-1 character index.
 */
export function fold1to1(text: string): string {
  let res = ""
  for (let i = 0; i < text.length; i++) {
    const ch = text[i]
    res += VI_CHAR_MAP[ch] || ch.toLowerCase()
  }
  return res
}

interface HighlightTextProps {
  text: string
  keywords?: string | string[]
  className?: string
  markClassName?: string
}

export const HighlightText: React.FC<HighlightTextProps> = ({
  text,
  keywords,
  className,
  markClassName = "bg-amber-200 dark:bg-amber-900/60 text-amber-900 dark:text-amber-200 px-1 rounded font-medium",
}) => {
  const parts = useMemo(() => {
    if (!text) return []

    // Collect and sanitize keywords
    const kwList: string[] = []
    const rawList = Array.isArray(keywords) ? keywords : typeof keywords === "string" ? [keywords] : []

    for (const raw of rawList) {
      if (!raw) continue
      // Split query by commas or spaces if full sentence
      const tokens = raw
        .split(/[\s,;.+/\-_]+/)
        .map((t) => t.trim())
        .filter((t) => t.length >= 2)
      kwList.push(...tokens)
      if (raw.trim().length >= 3 && !kwList.includes(raw.trim())) {
        kwList.push(raw.trim())
      }
    }

    if (kwList.length === 0) {
      return [{ text, match: false }]
    }

    const foldedText = fold1to1(text)
    const ranges: [number, number][] = []

    for (const kw of kwList) {
      const foldedKw = fold1to1(kw)
      if (!foldedKw) continue

      let startIdx = 0
      while (startIdx < foldedText.length) {
        const found = foldedText.indexOf(foldedKw, startIdx)
        if (found === -1) break
        ranges.push([found, found + foldedKw.length])
        startIdx = found + Math.max(1, foldedKw.length)
      }
    }

    if (ranges.length === 0) {
      return [{ text, match: false }]
    }

    // Sort ranges and merge overlaps
    ranges.sort((a, b) => a[0] - b[0] || b[1] - a[1])
    const merged: [number, number][] = []
    let current = ranges[0]

    for (let i = 1; i < ranges.length; i++) {
      const next = ranges[i]
      if (next[0] <= current[1]) {
        current = [current[0], Math.max(current[1], next[1])]
      } else {
        merged.push(current)
        current = next
      }
    }
    merged.push(current)

    // Slice text into match and non-match segments
    const result: { text: string; match: boolean }[] = []
    let cursor = 0

    for (const [start, end] of merged) {
      if (start > cursor) {
        result.push({ text: text.slice(cursor, start), match: false })
      }
      result.push({ text: text.slice(start, end), match: true })
      cursor = end
    }
    if (cursor < text.length) {
      result.push({ text: text.slice(cursor), match: false })
    }

    return result
  }, [text, keywords])

  return (
    <span className={className}>
      {parts.map((p, i) =>
        p.match ? (
          <mark key={i} className={markClassName}>
            {p.text}
          </mark>
        ) : (
          <React.Fragment key={i}>{p.text}</React.Fragment>
        ),
      )}
    </span>
  )
}
