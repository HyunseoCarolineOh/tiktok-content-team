import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// ── 파이프라인 ──────────────────────────────────────────
export interface RunParams {
  date?: string
  index?: number
  mock?: boolean
  dry_run?: boolean
  skip_whisper?: boolean
}

export const runPipelineStep = (step: string, params: RunParams = {}) =>
  api.post<{ run_id: string; step: string; status: string }>(
    `/pipeline/run/${step}`,
    null,
    { params }
  )

export const getPipelineStatus = () =>
  api.get<{ active_runs: string[] }>('/pipeline/status')

// ── Outputs ─────────────────────────────────────────────
export const getDates = () =>
  api.get<{ dates: string[] }>('/outputs/dates')

export const getDateSummary = (date: string) =>
  api.get<Record<string, unknown>>(`/outputs/${date}/summary`)

export const getScripts = (date: string) =>
  api.get<{ scripts: { name: string; size: number; modified: number }[] }>(
    `/outputs/${date}/scripts`
  )

export const getScript = (date: string, filename: string) =>
  api.get<{ filename: string; content: string }>(
    `/outputs/${date}/scripts/${filename}`
  )

export const saveScript = (date: string, filename: string, content: string) =>
  api.put(`/outputs/${date}/scripts/${filename}`, { content })

export const getMetadataList = (date: string) =>
  api.get<{ metadata: { name: string; size: number; modified: number }[] }>(
    `/outputs/${date}/metadata`
  )

export const getMetadata = (date: string, filename: string) =>
  api.get<{ filename: string; data: Record<string, unknown> }>(
    `/outputs/${date}/metadata/${filename}`
  )

export const saveMetadata = (date: string, filename: string, data: Record<string, unknown>) =>
  api.put(`/outputs/${date}/metadata/${filename}`, { data })

export const getFinalVideos = (date: string) =>
  api.get<{ videos: { name: string; size: number }[] }>(
    `/outputs/${date}/final`
  )

// ── 스케줄 ───────────────────────────────────────────────
export const getSchedule = (date: string) =>
  api.get<{ schedule: Record<string, unknown> }>(`/schedule/${date}`)

export const saveSchedule = (date: string, schedule: Record<string, unknown>) =>
  api.put(`/schedule/${date}`, { schedule })

export const updateVideoSchedule = (
  date: string,
  videoIndex: number,
  payload: { publish_at?: string; topic?: string; category?: string }
) => api.patch(`/schedule/${date}/${videoIndex}`, payload)

// ── TikTok 인증 / 업로드 ───────────────────────────────
export const getAuthUrl = () =>
  api.get<{ auth_url: string }>('/upload/auth/url')

export const getAuthStatus = () =>
  api.get<{ authenticated: boolean }>('/upload/auth/status')

export const triggerUpload = (date: string, videoIndex?: number, dryRun = false) =>
  api.post<{ run_id: string }>('/upload/video', {
    date,
    video_index: videoIndex,
    dry_run: dryRun,
  })

export default api
