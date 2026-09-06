import React, { FormEvent, useState } from "react"
import { GraduationCap, Loader2 } from "lucide-react"
import { login } from "../api/client"

export const LoginScreen: React.FC<{ onSuccess: () => void }> = ({ onSuccess }) => {
  const [username, setUsername] = useState("admin")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(username.trim(), password)
      onSuccess()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đăng nhập thất bại")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <form
        onSubmit={(event) => void onSubmit(event)}
        className="w-full max-w-sm rounded-3xl border border-white/[0.08] bg-ink-900/80 p-8 shadow-pop backdrop-blur-xl"
      >
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-sky-400">
            <GraduationCap className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-extrabold text-white">AgentSys</h1>
            <p className="text-xs text-slate-500">Đăng nhập thư viện học liệu</p>
          </div>
        </div>
        <label className="mb-3 block text-xs font-semibold uppercase tracking-wide text-slate-500">
          Tài khoản
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            className="mt-1.5 w-full rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2.5 text-sm text-white outline-none focus:border-violet-400/50"
            autoComplete="username"
          />
        </label>
        <label className="mb-4 block text-xs font-semibold uppercase tracking-wide text-slate-500">
          Mật khẩu
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="mt-1.5 w-full rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2.5 text-sm text-white outline-none focus:border-violet-400/50"
            autoComplete="current-password"
          />
        </label>
        {error && <p className="mb-3 text-sm text-rose-300">{error}</p>}
        <button type="submit" disabled={busy} className="btn-primary w-full justify-center">
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Vào thư viện
        </button>
        <p className="mt-4 text-center text-[11px] leading-relaxed text-slate-600">
          Lab: user <span className="font-mono text-slate-400">admin</span>, mật khẩu ={" "}
          <span className="font-mono text-slate-400">ADMIN_API_KEY</span> trong file .env (không nhét key vào frontend).
        </p>
      </form>
    </div>
  )
}
