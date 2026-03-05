import { useCallback, useState } from 'react'
import { Upload, Film } from 'lucide-react'
import api from '../api/client'

interface Props {
  date: string
  onUploaded?: () => void
}

export default function VideoUploader({ date, onUploaded }: Props) {
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState<string>('')

  const uploadFile = useCallback(async (file: File) => {
    if (!file.name.endsWith('.mp4')) {
      setProgress('MP4 파일만 업로드 가능합니다.')
      return
    }
    setUploading(true)
    setProgress(`${file.name} 업로드 중...`)
    try {
      const formData = new FormData()
      formData.append('file', file)
      await api.post(`/outputs/${date}/raw`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setProgress(`✓ ${file.name} 업로드 완료`)
      onUploaded?.()
    } catch {
      setProgress(`✗ 업로드 실패: ${file.name}`)
    } finally {
      setUploading(false)
    }
  }, [date, onUploaded])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragging(false)
      const files = Array.from(e.dataTransfer.files)
      files.forEach(uploadFile)
    },
    [uploadFile]
  )

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? [])
    files.forEach(uploadFile)
    e.target.value = ''
  }

  return (
    <div>
      <label
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={`flex flex-col items-center justify-center gap-3 p-8 rounded-lg border-2 border-dashed cursor-pointer transition-colors ${
          dragging
            ? 'border-brand-red bg-red-900/20'
            : 'border-gray-600 bg-gray-800/50 hover:border-gray-400'
        }`}
      >
        {uploading ? (
          <Film size={32} className="text-yellow-400 animate-pulse" />
        ) : (
          <Upload size={32} className="text-gray-400" />
        )}
        <div className="text-center">
          <p className="text-sm text-gray-300">
            {uploading ? '업로드 중...' : 'MP4 영상을 드래그하거나 클릭하세요'}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {date} / raw/ 폴더에 저장됩니다
          </p>
        </div>
        <input
          type="file"
          accept=".mp4,video/mp4"
          multiple
          onChange={handleFileInput}
          className="hidden"
          disabled={uploading}
        />
      </label>
      {progress && (
        <p className={`mt-2 text-xs font-mono ${progress.startsWith('✓') ? 'text-green-400' : progress.startsWith('✗') ? 'text-red-400' : 'text-yellow-400'}`}>
          {progress}
        </p>
      )}
    </div>
  )
}
