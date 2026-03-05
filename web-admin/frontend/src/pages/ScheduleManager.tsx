import { useEffect, useState } from 'react'
import { Calendar, Clock, Save, ExternalLink } from 'lucide-react'
import { getDates, getSchedule, updateVideoSchedule, getAuthStatus, getAuthUrl, triggerUpload } from '../api/client'

interface VideoSchedule {
  index: number
  topic: string
  category?: string
  publish_at?: string
  angle?: string
}

interface Schedule {
  week: string
  videos: VideoSchedule[]
}

const CATEGORIES = ['트렌드 인사이트', '실전 전략', '케이스 스터디', '커뮤니티 참여']

export default function ScheduleManager() {
  const [dates, setDates] = useState<string[]>([])
  const [selectedDate, setSelectedDate] = useState('')
  const [schedule, setSchedule] = useState<Schedule | null>(null)
  const [editedVideos, setEditedVideos] = useState<Record<number, Partial<VideoSchedule>>>({})
  const [saving, setSaving] = useState<number | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [uploading, setUploading] = useState<number | null>(null)
  const [uploadRunIds, setUploadRunIds] = useState<Record<number, string>>({})

  useEffect(() => {
    getDates().then((r) => {
      setDates(r.data.dates)
      if (r.data.dates.length > 0) setSelectedDate(r.data.dates[0])
    })
    getAuthStatus().then((r) => setIsAuthenticated(r.data.authenticated))
  }, [])

  useEffect(() => {
    if (!selectedDate) return
    setSchedule(null)
    setEditedVideos({})
    getSchedule(selectedDate)
      .then((r) => setSchedule(r.data.schedule as Schedule))
      .catch(() => setSchedule(null))
  }, [selectedDate])

  const getVideoData = (video: VideoSchedule): VideoSchedule => ({
    ...video,
    ...(editedVideos[video.index] ?? {}),
  })

  const updateField = (index: number, field: keyof VideoSchedule, value: string) => {
    setEditedVideos((prev) => ({
      ...prev,
      [index]: { ...(prev[index] ?? {}), [field]: value },
    }))
  }

  const handleSave = async (video: VideoSchedule) => {
    const edited = editedVideos[video.index]
    if (!edited) return
    setSaving(video.index)
    try {
      await updateVideoSchedule(selectedDate, video.index, {
        publish_at: edited.publish_at,
        topic: edited.topic,
        category: edited.category,
      })
      // 성공 시 로컬 스케줄 업데이트
      setSchedule((prev) => prev ? {
        ...prev,
        videos: prev.videos.map((v) => v.index === video.index ? getVideoData(v) : v),
      } : prev)
      setEditedVideos((prev) => { const n = { ...prev }; delete n[video.index]; return n })
    } catch {
      alert('저장 실패')
    } finally {
      setSaving(null)
    }
  }

  const handleTikTokAuth = async () => {
    try {
      const r = await getAuthUrl()
      window.open(r.data.auth_url, '_blank', 'width=600,height=700')
    } catch {
      alert('인증 URL 생성 실패')
    }
  }

  const handleUpload = async (videoIndex: number) => {
    setUploading(videoIndex)
    try {
      const r = await triggerUpload(selectedDate, videoIndex, false)
      setUploadRunIds((prev) => ({ ...prev, [videoIndex]: r.data.run_id }))
    } catch {
      alert('업로드 실행 실패')
    } finally {
      setUploading(null)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">스케줄 관리</h1>
        <p className="text-gray-400 mt-1 text-sm">주간 발행 스케줄을 확인하고 수정하세요.</p>
      </div>

      {/* TikTok 인증 상태 */}
      <div className={`flex items-center justify-between p-3 rounded-lg border ${isAuthenticated ? 'bg-green-900/20 border-green-700' : 'bg-gray-800 border-gray-700'}`}>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isAuthenticated ? 'bg-green-400' : 'bg-gray-500'}`} />
          <span className="text-sm text-gray-300">
            TikTok {isAuthenticated ? '인증됨' : '미인증'}
          </span>
        </div>
        {!isAuthenticated && (
          <button
            onClick={handleTikTokAuth}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-red hover:bg-red-600 rounded text-xs text-white transition-colors"
          >
            <ExternalLink size={12} />
            TikTok 연결
          </button>
        )}
      </div>

      {/* 날짜 선택 */}
      <div>
        <label className="block text-xs text-gray-400 mb-1">날짜</label>
        <select
          value={selectedDate}
          onChange={(e) => setSelectedDate(e.target.value)}
          className="bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm text-white focus:outline-none"
        >
          {dates.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
      </div>

      {/* 스케줄 테이블 */}
      {schedule ? (
        <div className="space-y-3">
          {schedule.videos.map((video) => {
            const v = getVideoData(video)
            const isDirty = !!editedVideos[video.index]
            return (
              <div key={video.index} className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                <div className="grid grid-cols-1 md:grid-cols-[2fr_1.5fr_1fr_auto] gap-3 items-end">
                  {/* 주제 */}
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">
                      {video.index}번 영상 — 주제
                    </label>
                    <input
                      type="text"
                      value={v.topic ?? ''}
                      onChange={(e) => updateField(video.index, 'topic', e.target.value)}
                      className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-red"
                    />
                  </div>

                  {/* 카테고리 */}
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">카테고리</label>
                    <select
                      value={v.category ?? ''}
                      onChange={(e) => updateField(video.index, 'category', e.target.value)}
                      className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 text-sm text-white focus:outline-none"
                    >
                      <option value="">—</option>
                      {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>

                  {/* 발행 시간 */}
                  <div>
                    <label className="block text-xs text-gray-400 mb-1 flex items-center gap-1">
                      <Clock size={10} /> 발행 시간
                    </label>
                    <input
                      type="datetime-local"
                      value={v.publish_at ? v.publish_at.slice(0, 16) : ''}
                      onChange={(e) => updateField(video.index, 'publish_at', e.target.value + ':00+09:00')}
                      className="w-full bg-gray-900 border border-gray-600 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-red"
                    />
                  </div>

                  {/* 액션 버튼 */}
                  <div className="flex gap-2">
                    {isDirty && (
                      <button
                        onClick={() => handleSave(video)}
                        disabled={saving === video.index}
                        className="flex items-center gap-1 px-3 py-2 bg-brand-red hover:bg-red-600 disabled:opacity-50 rounded text-xs text-white"
                      >
                        <Save size={12} />
                        {saving === video.index ? '...' : '저장'}
                      </button>
                    )}
                    {isAuthenticated && (
                      <button
                        onClick={() => handleUpload(video.index)}
                        disabled={uploading === video.index}
                        className="flex items-center gap-1 px-3 py-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 rounded text-xs text-gray-200"
                      >
                        <ExternalLink size={12} />
                        {uploading === video.index ? '...' : '업로드'}
                      </button>
                    )}
                  </div>
                </div>

                {/* 업로드 run_id 표시 */}
                {uploadRunIds[video.index] && (
                  <p className="mt-2 text-xs text-yellow-400 font-mono">
                    run_id: {uploadRunIds[video.index]} — 파이프라인 실행 탭에서 로그 확인
                  </p>
                )}
              </div>
            )
          })}
        </div>
      ) : (
        <div className="text-gray-500 text-sm">
          {selectedDate ? `${selectedDate}의 schedule.json이 없습니다. 02_기획 단계를 먼저 실행하세요.` : '날짜를 선택하세요.'}
        </div>
      )}
    </div>
  )
}
