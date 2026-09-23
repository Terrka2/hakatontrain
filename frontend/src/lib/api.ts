// Общий доступ к API для фич (F1). Единственное место, где решается «mock или сервер».
import { client } from "@/client/client.gen"

/** L0: mock включён по умолчанию. VITE_USE_MOCK=false → реальный API. */
export const USE_MOCK = import.meta.env.VITE_USE_MOCK !== "false"

type Query = Record<string, string | number | boolean>

/** GET через сгенерированный клиент: та же авторизация и baseURL, что у остального приложения. */
export async function apiGet<T>(url: string, query?: Query): Promise<T> {
  const res = (await client.get({
    url,
    query,
    throwOnError: true,
  })) as unknown as { data: T }
  return res.data
}
