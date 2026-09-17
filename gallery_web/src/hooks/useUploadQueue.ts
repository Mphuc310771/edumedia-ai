import { useCallback, useRef, useState } from "react"
import { fetchStatus, reprocessMedia, requestUploadUrl, putPresigned } from "../api/client"

export type UploadTaskStatus = "queued" | "uploading" | "processing" | "done" | "failed"

export interface UploadTask {
  id: string
  fileName: string
  fileId?: string
  status: UploadTaskStatus
  error?: string
}

const CONCURRENCY = 3
const POLL_INTERVAL_MS = 2500
const POLL_TIMEOUT_MS = 5 * 60 * 1000

interface QueueEntry {
  taskId: string
  file: File
}

/**
 * Hàng đợi upload không chặn: đẩy nhiều file song song lên S3, kích hoạt xử lý nền
 * phía backend rồi poll trạng thái. Card xuất hiện ngay ở thư viện với trạng thái
 * "Đang phân tích" và tự chuyển sang READY/FAILED khi pipeline AWS xong.
 */
export function useUploadQueue(onCatalogChanged: () => void, onBatchDone: (ok: number, total: number) => void) {
  const [tasks, setTasks] = useState<UploadTask[]>([])
  const pending = useRef<QueueEntry[]>([])
  const activeWorkers = useRef(0)
  const batch = useRef({ total: 0, settled: 0, ok: 0 })

  const patchTask = useCallback((taskId: string, patch: Partial<UploadTask>) => {
    setTasks((prev) => prev.map((task) => (task.id === taskId ? { ...task, ...patch } : task)))
  }, [])

  const settle = useCallback(
    (taskId: string, ok: boolean, error?: string) => {
      patchTask(taskId, { status: ok ? "done" : "failed", error })
      batch.current.settled += 1
      if (ok) batch.current.ok += 1
      onCatalogChanged()
      if (batch.current.settled >= batch.current.total) {
        onBatchDone(batch.current.ok, batch.current.total)
      }
    },
    [onBatchDone, onCatalogChanged, patchTask],
  )

  const pollUntilSettled = useCallback(
    async (taskId: string, fileId: string) => {
      const started = Date.now()
      while (Date.now() - started < POLL_TIMEOUT_MS) {
        try {
          const status = await fetchStatus(fileId)
          if (status.status === "READY") {
            settle(taskId, true)
            return
          }
          if (status.status === "FAILED") {
            settle(taskId, false, status.error || "Pipeline AWS thất bại")
            return
          }
        } catch {
          // Lỗi mạng tạm thời khi poll: thử lại ở vòng sau
        }
        await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS))
      }
      settle(taskId, false, "Hết thời gian chờ xử lý. Kiểm tra AWS Console.")
    },
    [settle],
  )

  const runWorker = useCallback(async () => {
    activeWorkers.current += 1
    try {
      for (;;) {
        const entry = pending.current.shift()
        if (!entry) return
        const { taskId, file } = entry
        try {
          patchTask(taskId, { status: "uploading" })
          const { file_id, presigned_url, object_key } = await requestUploadUrl(
            file.name,
            file.type || "application/octet-stream",
          )
          await putPresigned(presigned_url, file)

          patchTask(taskId, { status: "processing", fileId: file_id })
          // S3 ObjectCreated event notification tự động đưa message vào SQS IngestQueue.
          // Không gọi triggerProcess để tránh Double Ingestion (nhận 2 messages cho cùng 1 file).
          // Card hiện ngay trong thư viện với trạng thái INDEXING/READY khi poll
          onCatalogChanged()
          void pollUntilSettled(taskId, file_id)
        } catch (err: unknown) {
          settle(taskId, false, err instanceof Error ? err.message : "Upload thất bại")
        }
      }
    } finally {
      activeWorkers.current -= 1
    }
  }, [onCatalogChanged, patchTask, pollUntilSettled, settle])

  const enqueue = useCallback(
    (files: File[]) => {
      if (files.length === 0) return
      const isIdle = batch.current.settled >= batch.current.total
      if (isIdle) {
        batch.current = { total: 0, settled: 0, ok: 0 }
        setTasks([])
      }
      batch.current.total += files.length

      const entries: QueueEntry[] = files.map((file) => ({
        taskId: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        file,
      }))
      setTasks((prev) => [
        ...prev,
        ...entries.map(({ taskId, file }) => ({ id: taskId, fileName: file.name, status: "queued" as const })),
      ])
      pending.current.push(...entries)

      const workersToStart = Math.min(CONCURRENCY - activeWorkers.current, entries.length)
      for (let i = 0; i < workersToStart; i++) void runWorker()
    },
    [runWorker],
  )

  /** Phân tích lại một tệp FAILED: gọi /reprocess rồi theo dõi như một task mới. */
  const retryIngest = useCallback(
    async (fileId: string, fileName: string) => {
      const isIdle = batch.current.settled >= batch.current.total
      if (isIdle) {
        batch.current = { total: 0, settled: 0, ok: 0 }
        setTasks([])
      }
      batch.current.total += 1

      const taskId = `retry-${fileId}-${Date.now()}`
      setTasks((prev) => [...prev, { id: taskId, fileName, fileId, status: "processing" }])
      try {
        await reprocessMedia(fileId)
        onCatalogChanged()
        void pollUntilSettled(taskId, fileId)
      } catch (err: unknown) {
        settle(taskId, false, err instanceof Error ? err.message : "Không gọi được reprocess")
      }
    },
    [onCatalogChanged, pollUntilSettled, settle],
  )

  const busy = tasks.some((task) => task.status === "queued" || task.status === "uploading" || task.status === "processing")

  return { tasks, enqueue, retryIngest, busy }
}
