import { useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { type FailReason, SKILL_LABELS, SKILLS } from "@/lib/contracts"
import { cn } from "@/lib/utils"
import { FAIL_REASONS } from "./logic"

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (reason: FailReason, needsSkill?: string, note?: string) => void
}

/** «Не могу»: причина обязательна, для «нужна другая бригада» — ещё и навык. */
export function FailDialog({ open, onOpenChange, onSubmit }: Props) {
  const [reason, setReason] = useState<FailReason | null>(null)
  const [skill, setSkill] = useState<string>("")
  const [note, setNote] = useState("")
  const needsSkill = reason === "needs_other_skill"
  const ready = reason !== null && (!needsSkill || skill !== "")

  const reset = () => {
    setReason(null)
    setSkill("")
    setNote("")
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) reset()
        onOpenChange(o)
      }}
    >
      <DialogContent className="max-w-md gap-4">
        <DialogHeader>
          <DialogTitle className="text-xl">Почему не получается?</DialogTitle>
          <DialogDescription>
            Оператор перестроит план и передаст задание дальше.
          </DialogDescription>
        </DialogHeader>
        <fieldset className="flex flex-col gap-2">
          <legend className="sr-only">Причина</legend>
          {FAIL_REASONS.map((r) => (
            <button
              key={r.value}
              type="button"
              aria-pressed={reason === r.value}
              onClick={() => setReason(r.value)}
              className={cn(
                "min-h-12 rounded-xl border px-4 text-left text-base transition-colors",
                reason === r.value
                  ? "border-primary bg-primary/10 font-medium"
                  : "bg-background hover:bg-accent",
              )}
            >
              {r.label}
            </button>
          ))}
        </fieldset>
        {needsSkill && (
          <div className="flex flex-col gap-2">
            <Label htmlFor="fail-skill">Какая бригада нужна</Label>
            <Select value={skill} onValueChange={setSkill}>
              <SelectTrigger id="fail-skill" className="h-12 w-full text-base">
                <SelectValue placeholder="Выберите бригаду" />
              </SelectTrigger>
              <SelectContent>
                {SKILLS.map((s) => (
                  <SelectItem key={s} value={s} className="min-h-11 text-base">
                    {SKILL_LABELS[s]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
        <div className="flex flex-col gap-2">
          <Label htmlFor="fail-note">Заметка, если нужно</Label>
          <textarea
            id="fail-note"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            placeholder="Например: ворота закрыты, нужен ключ"
            className="min-h-12 rounded-md border bg-background px-3 py-2 text-base outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
        <DialogFooter className="gap-2 sm:flex-col">
          <Button
            size="lg"
            className="h-12 w-full text-base"
            disabled={!ready}
            onClick={() => {
              if (!reason) return
              onSubmit(reason, needsSkill ? skill : undefined, note)
              reset()
            }}
          >
            Отправить оператору
          </Button>
          <Button
            variant="ghost"
            size="lg"
            className="h-12 w-full text-base"
            onClick={() => onOpenChange(false)}
          >
            Отмена
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
