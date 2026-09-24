import { WifiOff } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

type Props = {
  title?: string
  error?: unknown
  onRetry?: () => void
  className?: string
}

function describe(error: unknown): string {
  if (error instanceof Error) return error.message
  if (typeof error === "string") return error
  return "Сервер не ответил."
}

/** Ошибка загрузки: что случилось и кнопка «Повторить». Без стека и без «упс». */
export function ErrorState({ title = "Не удалось загрузить данные", error, onRetry, className }: Props) {
  return (
    <div
      role="alert"
      className={cn("flex min-h-40 flex-col items-center justify-center gap-2 px-4 py-8 text-center", className)}
    >
      <WifiOff className="size-8 text-destructive" aria-hidden />
      <p className="text-base font-medium">{title}</p>
      <p className="max-w-prose break-words text-sm text-muted-foreground">{describe(error)}</p>
      {onRetry && (
        <Button variant="outline" size="lg" className="mt-2 min-h-12" onClick={onRetry}>
          Повторить
        </Button>
      )}
    </div>
  )
}
