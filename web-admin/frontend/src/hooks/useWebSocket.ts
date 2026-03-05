import { useCallback, useEffect, useRef, useState } from 'react'

export interface LogEntry {
  type: 'log' | 'done' | 'error'
  message?: string
  exit_code?: number
}

export interface UseWebSocketReturn {
  logs: LogEntry[]
  isConnected: boolean
  isDone: boolean
  exitCode: number | null
  connect: (runId: string) => void
  clear: () => void
}

export function useWebSocket(): UseWebSocketReturn {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isDone, setIsDone] = useState(false)
  const [exitCode, setExitCode] = useState<number | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  const clear = useCallback(() => {
    setLogs([])
    setIsConnected(false)
    setIsDone(false)
    setExitCode(null)
  }, [])

  const connect = useCallback((runId: string) => {
    // 기존 연결 정리
    if (wsRef.current) {
      wsRef.current.close()
    }
    clear()

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host = window.location.hostname
    const port = import.meta.env.DEV ? '8000' : window.location.port
    const url = `${protocol}://${host}:${port}/api/pipeline/ws/logs/${runId}`

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => setIsConnected(true)

    ws.onmessage = (event) => {
      try {
        const msg: LogEntry = JSON.parse(event.data)
        setLogs((prev) => [...prev, msg])
        if (msg.type === 'done') {
          setIsDone(true)
          setExitCode(msg.exit_code ?? null)
          setIsConnected(false)
        }
      } catch {
        // JSON 파싱 실패 시 raw 텍스트로 처리
        setLogs((prev) => [...prev, { type: 'log', message: event.data }])
      }
    }

    ws.onerror = () => {
      setLogs((prev) => [
        ...prev,
        { type: 'error', message: 'WebSocket 연결 오류' },
      ])
      setIsConnected(false)
    }

    ws.onclose = () => {
      setIsConnected(false)
    }
  }, [clear])

  // 컴포넌트 언마운트 시 연결 정리
  useEffect(() => {
    return () => {
      wsRef.current?.close()
    }
  }, [])

  return { logs, isConnected, isDone, exitCode, connect, clear }
}
