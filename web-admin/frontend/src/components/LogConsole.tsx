import { useEffect, useRef } from 'react'
import type { LogEntry } from '../hooks/useWebSocket'

interface Props {
  logs: LogEntry[]
  isConnected: boolean
  isDone: boolean
  exitCode: number | null
}

export default function LogConsole({ logs, isConnected, isDone, exitCode }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const getLineClass = (entry: LogEntry) => {
    if (entry.type === 'error') return 'text-red-400'
    if (entry.type === 'done') return exitCode === 0 ? 'text-green-400' : 'text-red-400'
    const msg = entry.message ?? ''
    if (msg.includes('오류') || msg.includes('Error') || msg.includes('error')) return 'text-red-300'
    if (msg.includes('완료') || msg.includes('✓')) return 'text-green-300'
    if (msg.startsWith('[')) return 'text-yellow-300'
    return 'text-gray-300'
  }

  return (
    <div className="bg-gray-950 rounded-lg border border-gray-700 overflow-hidden">
      {/* 헤더 */}
      <div className="flex items-center gap-2 px-4 py-2 bg-gray-900 border-b border-gray-700">
        <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400 animate-pulse' : isDone ? (exitCode === 0 ? 'bg-green-500' : 'bg-red-500') : 'bg-gray-500'}`} />
        <span className="text-xs font-mono text-gray-400">
          {isConnected ? '실행 중...' : isDone ? (exitCode === 0 ? `완료 (exit 0)` : `실패 (exit ${exitCode})`) : '대기 중'}
        </span>
      </div>

      {/* 로그 영역 */}
      <div className="h-80 overflow-y-auto p-4 font-mono text-xs leading-5">
        {logs.length === 0 ? (
          <div className="text-gray-600 italic">파이프라인을 실행하면 로그가 여기에 표시됩니다.</div>
        ) : (
          logs.map((entry, i) => (
            <div key={i} className={getLineClass(entry)}>
              {entry.type === 'done'
                ? `─── 프로세스 종료 (exit ${entry.exit_code}) ───`
                : entry.message ?? ''}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
