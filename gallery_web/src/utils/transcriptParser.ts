export interface TranscriptSegment {
  id: string
  startTime: number // in seconds
  endTime: number // in seconds
  timestampStr: string // "00:15"
  text: string
}

export function formatSecondsToTime(seconds: number): string {
  if (isNaN(seconds) || seconds < 0) return "00:00"
  const totalSecs = Math.floor(seconds)
  const hrs = Math.floor(totalSecs / 3600)
  const mins = Math.floor((totalSecs % 3600) / 60)
  const secs = totalSecs % 60

  if (hrs > 0) {
    return `${hrs.toString().padStart(2, "0")}:${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`
  }
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`
}

function parseTimeToSeconds(timeStr: string): number {
  const parts = timeStr.trim().split(":").map(Number)
  if (parts.length === 3) {
    return parts[0] * 3600 + parts[1] * 60 + parts[2]
  }
  if (parts.length === 2) {
    return parts[0] * 60 + parts[1]
  }
  return 0
}

/**
 * Parses raw text or Transcribe JSON into structured timestamped segments.
 */
export function parseTranscript(rawContent: string, mediaDuration?: number): TranscriptSegment[] {
  if (!rawContent || !rawContent.trim()) return []

  const trimmed = rawContent.trim()

  // 1. Check if rawContent is Amazon Transcribe JSON
  if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
    try {
      const data = JSON.parse(trimmed)
      // Check audio_segments
      if (Array.isArray(data?.results?.audio_segments) && data.results.audio_segments.length > 0) {
        return data.results.audio_segments.map((seg: any, idx: number) => {
          const start = parseFloat(seg.start_time || "0")
          const end = parseFloat(seg.end_time || String(start + 5))
          return {
            id: `seg-${idx}`,
            startTime: start,
            endTime: end,
            timestampStr: formatSecondsToTime(start),
            text: seg.transcript || "",
          }
        })
      }
      // Check items list
      if (Array.isArray(data?.results?.items) && data.results.items.length > 0) {
        // Group items into segments of ~15-20 words
        const segments: TranscriptSegment[] = []
        let currentWords: string[] = []
        let segStart = 0
        let segEnd = 0

        for (let i = 0; i < data.results.items.length; i++) {
          const item = data.results.items[i]
          const alt = item?.alternatives?.[0]?.content || ""
          if (item.type === "pronunciation") {
            if (currentWords.length === 0) {
              segStart = parseFloat(item.start_time || "0")
            }
            segEnd = parseFloat(item.end_time || String(segStart + 1))
            currentWords.push(alt)
          } else if (item.type === "punctuation") {
            if (currentWords.length > 0) {
              currentWords[currentWords.length - 1] += alt
            }
          }

          if (currentWords.length >= 18 || (alt === "." && currentWords.length >= 8) || i === data.results.items.length - 1) {
            if (currentWords.length > 0) {
              segments.push({
                id: `seg-${segments.length}`,
                startTime: segStart,
                endTime: segEnd,
                timestampStr: formatSecondsToTime(segStart),
                text: currentWords.join(" "),
              })
              currentWords = []
            }
          }
        }
        if (segments.length > 0) return segments
      }

      // Plain transcript inside JSON
      if (typeof data?.transcript === "string") {
        return parseTranscript(data.transcript, mediaDuration)
      }
    } catch {
      // Fall through to plain text parsing
    }
  }

  // 2. Parse text with explicit timestamps: [mm:ss] or mm:ss
  const timestampRegex = /\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*[:-]?\s*(.+?)(?=\n*\[?\d{1,2}:\d{2}(?::\d{2})?\]?|$)/gs
  const explicitMatches: TranscriptSegment[] = []
  let match: RegExpExecArray | null

  while ((match = timestampRegex.exec(trimmed)) !== null) {
    const timeStr = match[1]
    const content = match[2].trim()
    if (content) {
      const startTime = parseTimeToSeconds(timeStr)
      explicitMatches.push({
        id: `seg-${explicitMatches.length}`,
        startTime,
        endTime: startTime + 10, // estimated next
        timestampStr: formatSecondsToTime(startTime),
        text: content,
      })
    }
  }

  // Fix end times for explicit matches
  if (explicitMatches.length >= 2) {
    for (let i = 0; i < explicitMatches.length - 1; i++) {
      explicitMatches[i].endTime = explicitMatches[i + 1].startTime
    }
    if (mediaDuration && mediaDuration > explicitMatches[explicitMatches.length - 1].startTime) {
      explicitMatches[explicitMatches.length - 1].endTime = mediaDuration
    } else {
      explicitMatches[explicitMatches.length - 1].endTime = explicitMatches[explicitMatches.length - 1].startTime + 15
    }
    return explicitMatches
  }

  // 3. Fallback: Parse plain text by breaking into sentences and distributing timestamps
  const rawSentences = trimmed
    .split(/(?<=[.?!;])\s+|\n{2,}/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0)

  if (rawSentences.length === 0) return []

  const totalDuration = mediaDuration && mediaDuration > 5 ? mediaDuration : rawSentences.length * 10
  const durationPerSentence = totalDuration / rawSentences.length

  return rawSentences.map((sentence, idx) => {
    const start = idx * durationPerSentence
    const end = (idx + 1) * durationPerSentence
    return {
      id: `seg-${idx}`,
      startTime: Math.round(start * 10) / 10,
      endTime: Math.round(end * 10) / 10,
      timestampStr: formatSecondsToTime(start),
      text: sentence,
    }
  })
}
