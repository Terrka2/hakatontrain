import { useRouter } from "@tanstack/react-router"
import { Bot, ChevronDown, SendHorizontal } from "lucide-react"
import { useCallback, useEffect, useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { useIsMobile } from "@/hooks/useMobile"
import type { UIAction } from "@/lib/contracts"
import { getUiState, setUiState } from "@/lib/ui-state"
import { cn } from "@/lib/utils"
import { runUiActions } from "./actions"
import { sendConfirm, sendMessage } from "./api"
import { ConfirmCard } from "./ConfirmCard"
import { buildRequest, ERROR_TEXT, type Message } from "./session"
import { dispatch, setOpen, useDrawerState } from "./store"

/** Одна сессия на вкладку: оператор помнит разговор, пока страница открыта. */
const SESSION_ID = crypto.randomUUID()

const HINTS = [
  "Что ты сделал?",
  "Почему это первое?",
  "Пошёл ливень",
  "Утверди план",
] as const

/**
 * Действия ассистента над интерфейсом. Без `navigate` — только состояние (карта подхватит выбор сама),
 * переходы между экранами пропускаются.
 */
export function applyUiActions(
  actions: UIAction[],
  navigate?: (to: string) => void,
): void {
  runUiActions(actions, {
    navigate: navigate ?? (() => undefined),
    setUiState,
    getFilters: () => getUiState().filters,
  })
}

function Trace({ trace }: { trace: string[] }) {
  const [open, setOpen] = useState(false)
  if (!trace.length) return null
  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="inline-flex min-h-8 items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
      >
        <ChevronDown
          className={cn("size-3 transition-transform", open && "rotate-180")}
          aria-hidden
        />
        Как я думал
      </button>
      {open && (
        <ol className="mt-1 flex flex-wrap gap-1">
          {trace.map((step, i) => (
            <li
              key={`${step}-${i}`}
              className="rounded-md bg-muted px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground"
            >
              {step}
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}

function Bubble({ message }: { message: Message }) {
  if (message.role === "user") {
    return (
      <li className="ml-8 self-end rounded-2xl rounded-br-sm bg-primary px-3 py-2 text-sm text-primary-foreground">
        {message.text}
      </li>
    )
  }
  if (message.role === "error") {
    return (
      <li
        role="alert"
        className="mr-8 rounded-2xl rounded-bl-sm border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm"
      >
        {message.text}
      </li>
    )
  }
  return (
    <li className="mr-8 rounded-2xl rounded-bl-sm bg-muted px-3 py-2 text-sm leading-relaxed">
      {message.text}
      <Trace trace={message.trace} />
    </li>
  )
}

/** Панель разговора с ИИ-оператором. Самодостаточна: своя плавающая кнопка, своя сессия. */
export function AssistantDrawer() {
  const router = useRouter()
  const isMobile = useIsMobile()
  const { open, session: state } = useDrawerState()
  const [draft, setDraft] = useState("")
  const listRef = useRef<HTMLOListElement>(null)

  const navigate = useCallback(
    (to: string) => {
      router.navigate({ to })
    },
    [router],
  )

  // biome-ignore lint/correctness/useExhaustiveDependencies: прокрутка к последнему сообщению при каждом новом
  useEffect(() => {
    listRef.current?.lastElementChild?.scrollIntoView({ block: "end" })
  }, [state.messages.length])

  const send = useCallback(
    async (text: string) => {
      const clean = text.trim()
      if (!clean || state.busy) return
      setDraft("")
      dispatch({ type: "send", text: clean })
      try {
        const res = await sendMessage(
          buildRequest(SESSION_ID, clean, getUiState()),
        )
        dispatch({ type: "reply", response: res })
        applyUiActions(res.actions, navigate)
      } catch {
        dispatch({ type: "fail", text: ERROR_TEXT })
      }
    },
    [navigate, state.busy],
  )

  const decide = useCallback(
    async (approve: boolean) => {
      const pending = state.pending
      if (!pending) return
      dispatch({ type: "decide", approve })
      if (!approve) return
      try {
        const res = await sendConfirm(pending.id, true)
        dispatch({ type: "reply", response: res })
        applyUiActions(res.actions, navigate)
      } catch {
        dispatch({ type: "fail", text: ERROR_TEXT })
      }
    },
    [navigate, state.pending],
  )

  return (
    <>
      <Button
        type="button"
        size="lg"
        onClick={() => setOpen(true)}
        aria-label="Открыть панель ассистента"
        data-testid="assistant-fab"
        className="fixed bottom-4 left-4 z-40 h-12 rounded-full px-4 shadow-lg md:bottom-6 md:left-auto md:right-6"
      >
        <Bot className="size-5" aria-hidden />
        Ассистент
      </Button>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent
          side={isMobile ? "bottom" : "right"}
          data-testid="assistant-panel"
          className={cn(
            "gap-0 p-0",
            isMobile ? "h-[85dvh] rounded-t-2xl" : "sm:max-w-md",
          )}
        >
          <SheetHeader className="border-b pr-12">
            <SheetTitle className="flex items-center gap-2">
              <Bot className="size-5 text-primary" aria-hidden />
              ИИ-оператор
            </SheetTitle>
            <SheetDescription>
              Видит то же, что и вы: карту, выбранную проблему, план. Утвердить
              что-либо может только человек.
            </SheetDescription>
          </SheetHeader>

          <ol
            ref={listRef}
            aria-live="polite"
            className="flex flex-1 flex-col gap-2 overflow-y-auto px-4 py-3"
          >
            {state.messages.length === 0 && (
              <li className="py-6 text-center text-sm text-muted-foreground">
                Спросите, что сделал оператор, или дайте команду.
              </li>
            )}
            {state.messages.map((m, i) => (
              <Bubble key={`${m.role}-${i}`} message={m} />
            ))}
            {state.busy && (
              <li className="mr-8 w-16 animate-pulse rounded-2xl rounded-bl-sm bg-muted px-3 py-2 text-sm text-muted-foreground">
                …
              </li>
            )}
            {state.pending && (
              <li className="mt-1">
                <ConfirmCard pending={state.pending} onDecide={decide} />
              </li>
            )}
          </ol>

          <div className="flex flex-col gap-2 border-t p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
            <div className="flex flex-wrap gap-1.5">
              {HINTS.map((h) => (
                <Button
                  key={h}
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-9 rounded-full"
                  disabled={state.busy}
                  onClick={() => send(h)}
                >
                  {h}
                </Button>
              ))}
            </div>
            <form
              className="flex gap-2"
              onSubmit={(e) => {
                e.preventDefault()
                void send(draft)
              }}
            >
              <Input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Напишите оператору"
                aria-label="Сообщение оператору"
                className="h-12 text-base"
                disabled={state.busy}
              />
              <Button
                type="submit"
                size="icon"
                className="size-12 shrink-0"
                aria-label="Отправить"
                disabled={state.busy || !draft.trim()}
              >
                <SendHorizontal className="size-5" aria-hidden />
              </Button>
            </form>
          </div>
        </SheetContent>
      </Sheet>
    </>
  )
}
