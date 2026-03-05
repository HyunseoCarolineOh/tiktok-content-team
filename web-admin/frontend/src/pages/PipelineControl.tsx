import { useState } from 'react'
import { Play, RefreshCw, AlertTriangle } from 'lucide-react'
import LogConsole from '../components/LogConsole'
import VideoUploader from '../components/VideoUploader'
import { runPipelineStep } from '../api/client'
import { useWebSocket } from '../hooks/useWebSocket'

const isLocalEnv = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'

const STEPS = [
  { id: '1', label: '01 리서치', desc: '트렌드 수집 + 주제 풀 생성', color: 'bg-blue-600 hover:bg-blue-700' },
  { id: '2', label: '02 기획', desc: '주간 5개 주제 선정 + 스케줄', color: 'bg-purple-600 hover:bg-purple-700' },
  { id: '3', label: '03 스크립트', desc: '후크A/B + 본문 + CTA 생성', color: 'bg-indigo-600 hover:bg-indigo-700' },
  { id: '4', label: '04 편집', desc: 'Whisper + FFmpeg + 썸네일', color: 'bg-orange-600 hover:bg-orange-700' },
  { id: '5', label: '05 업로드', desc: 'TikTok API 업로드', color: 'bg-pink-600 hover:bg-pink-700' },
  { id: '6', label: '06 분석', desc: '성과 리포트 생성', color: 'bg-green-600 hover:bg-green-700' },
]

export default function PipelineControl() {
  const today = new Date().toISOString().slice(0, 10)
  const [date, setDate] = useState(today)
  const [runningStep, setRunningStep] = useState<string | null>(null)
  const { logs, isConnected, isDone, exitCode, connect, clear } = useWebSocket()

  const handleRun = async (step: string) => {
    clear()
    setRunningStep(step)
    try {
      const res = await runPipelineStep(step, { date })
      connect(res.data.run_id)
    } catch (err) {
      console.error('파이프라인 실행 실패', err)
      setRunningStep(null)
    }
  }

  // 완료 시 runningStep 해제
  if (isDone && runningStep) {
    setRunningStep(null)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">파이프라인 실행</h1>
        <p className="text-gray-400 mt-1 text-sm">6단계 콘텐츠 파이프라인을 순서대로 실행하세요.</p>
      </div>

      {!isLocalEnv && (
        <div className="flex items-start gap-3 bg-yellow-900/30 border border-yellow-700 rounded-lg p-4">
          <AlertTriangle size={18} className="text-yellow-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-yellow-300 font-semibold text-sm">파이프라인은 로컬 환경에서만 실행 가능합니다</p>
            <p className="text-yellow-400/80 text-xs mt-1">
              Vercel 서버리스는 장기 실행 프로세스와 WebSocket을 지원하지 않습니다.
              로컬에서 <code className="bg-black/30 px-1 rounded">python -X utf8 pipeline/01_research.py</code> 로 직접 실행하세요.
            </p>
          </div>
        </div>
      )}

      {/* 날짜 선택 */}
      <div className="flex items-center gap-3">
        <label className="text-sm text-gray-400">실행 날짜</label>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="bg-gray-800 border border-gray-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-brand-red"
        />
      </div>

      {/* 스텝 버튼 그리드 */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {STEPS.map((step) => {
          const isRunning = runningStep === step.id
          const disabled = !isLocalEnv || (runningStep !== null && !isRunning)
          return (
            <button
              key={step.id}
              onClick={() => handleRun(step.id)}
              disabled={disabled || isRunning}
              className={`${step.color} disabled:opacity-40 disabled:cursor-not-allowed rounded-lg p-4 text-left transition-colors`}
            >
              <div className="flex items-center gap-2 mb-1">
                {isRunning ? (
                  <RefreshCw size={16} className="text-white animate-spin" />
                ) : (
                  <Play size={16} className="text-white" />
                )}
                <span className="font-semibold text-white text-sm">{step.label}</span>
              </div>
              <p className="text-xs text-white/70">{step.desc}</p>
            </button>
          )
        })}
      </div>

      {/* 로그 콘솔 */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold text-gray-300">실행 로그</h2>
          <button
            onClick={clear}
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            지우기
          </button>
        </div>
        <LogConsole logs={logs} isConnected={isConnected} isDone={isDone} exitCode={exitCode} />
      </div>

      {/* raw 영상 업로드 (04_editing용) */}
      <div>
        <h2 className="text-sm font-semibold text-gray-300 mb-2">raw 영상 업로드 (04 편집용)</h2>
        <VideoUploader date={date} />
      </div>
    </div>
  )
}
