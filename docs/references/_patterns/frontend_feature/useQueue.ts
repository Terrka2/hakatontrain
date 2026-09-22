import { useQuery } from "@tanstack/react-query"

import { fetchClusters } from "./api"

export function useQueue() {
  return useQuery({ queryKey: ["clusters"], queryFn: fetchClusters })
}
