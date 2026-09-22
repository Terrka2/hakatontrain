// Действия ассистента над интерфейсом. Чистая часть: зависимости передаются явно, чтобы тестировать без роутера.
import type { UIAction } from "@/lib/contracts"

export type ActionDeps = {
  navigate: (to: string) => void
  setUiState: (patch: {
    selected_cluster_id?: string | null
    filters?: Record<string, unknown>
  }) => void
  getFilters: () => Record<string, unknown>
}

/** Возвращает список того, что сделано, — для лога и тестов. */
export function runUiActions(actions: UIAction[], deps: ActionDeps): string[] {
  const done: string[] = []
  for (const a of actions) {
    switch (a.kind) {
      case "focus_cluster": {
        const id =
          typeof a.payload.cluster_id === "string" ? a.payload.cluster_id : null
        if (!id) break
        deps.setUiState({ selected_cluster_id: id })
        deps.navigate("/")
        done.push(`focus:${id}`)
        break
      }
      case "show_plan":
        deps.navigate("/plan")
        done.push("plan")
        break
      case "show_run": {
        const runId =
          typeof a.payload.run_id === "string" ? a.payload.run_id : null
        if (runId)
          deps.setUiState({ filters: { ...deps.getFilters(), run_id: runId } })
        deps.navigate("/plan")
        done.push(`run:${runId ?? "?"}`)
        break
      }
      case "show_crew":
        deps.navigate("/crew")
        done.push("crew")
        break
      case "set_filter":
        deps.setUiState({ filters: { ...deps.getFilters(), ...a.payload } })
        done.push(`filter:${Object.keys(a.payload).join(",")}`)
        break
      default:
        // show_trip / open_report_form — дополнительные блоки, в ядре не обрабатываются.
        break
    }
  }
  return done
}
