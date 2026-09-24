import { Camera, Check, MapPin, X } from "lucide-react"
import { useId, useState } from "react"

import { Button } from "@/components/ui/button"
import type { FailReason, JobUpdate, RouteStop } from "@/lib/contracts"
import { FailDialog } from "./FailDialog"
import { buildUpdate, canFinish } from "./logic"

type Props = {
  stop: RouteStop
  crewId: string
  onUpdate: (u: JobUpdate) => void
  busy?: boolean
}

/** Три действия одной рукой: «Приехал», «Сделано» (только с фото), «Не могу» (с причиной). */
export function StopActions({ stop, crewId, onUpdate, busy }: Props) {
  const [photo, setPhoto] = useState<string | null>(null)
  const [failOpen, setFailOpen] = useState(false)
  const inputId = useId()
  const at = () => new Date().toISOString()

  const send = (partial: Parameters<typeof buildUpdate>[0]) => {
    setPhoto(null)
    onUpdate(buildUpdate(partial))
  }

  const onFail = (reason: FailReason, needsSkill?: string, note?: string) => {
    setFailOpen(false)
    send({
      jobId: stop.job_id,
      crewId,
      status: "failed",
      at: at(),
      reason,
      needsSkill,
      note,
    })
  }

  return (
    <section className="flex flex-col gap-3" aria-label="Действия по остановке">
      {stop.status === "pending" ? (
        <Button
          size="lg"
          className="h-14 w-full text-lg"
          disabled={busy}
          onClick={() =>
            send({ jobId: stop.job_id, crewId, status: "arrived", at: at() })
          }
        >
          <MapPin className="size-6" aria-hidden />
          Приехал
        </Button>
      ) : (
        <>
          <label
            htmlFor={inputId}
            className="flex h-14 w-full cursor-pointer items-center justify-center gap-2 rounded-md border bg-background text-lg font-medium hover:bg-accent"
          >
            <Camera className="size-6" aria-hidden />
            {photo ? "Переснять" : "Сфотографировать"}
            <input
              id={inputId}
              type="file"
              accept="image/*"
              capture="environment"
              className="sr-only"
              onChange={(e) => {
                const f = e.target.files?.[0]
                setPhoto(f ? URL.createObjectURL(f) : null)
              }}
            />
          </label>
          {photo && (
            <img
              src={photo}
              alt="Фото результата"
              className="max-h-40 w-full rounded-xl border object-cover"
            />
          )}
          <Button
            size="lg"
            className="h-14 w-full text-lg"
            disabled={busy || !canFinish(photo !== null)}
            onClick={() =>
              send({
                jobId: stop.job_id,
                crewId,
                status: "done",
                at: at(),
                photoUrl: photo,
              })
            }
          >
            <Check className="size-6" aria-hidden />
            Сделано
          </Button>
          {!photo && (
            <p className="text-center text-sm text-muted-foreground">
              «Сделано» откроется после фото результата
            </p>
          )}
        </>
      )}
      <Button
        variant="outline"
        size="lg"
        className="h-12 w-full text-base"
        disabled={busy}
        onClick={() => setFailOpen(true)}
      >
        <X className="size-5" aria-hidden />
        Не могу
      </Button>
      <FailDialog
        open={failOpen}
        onOpenChange={setFailOpen}
        onSubmit={onFail}
      />
    </section>
  )
}
