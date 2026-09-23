import { useQuery } from "@tanstack/react-query"

import { fetchClusters } from "./api"

export function useClusters() {
  return useQuery({
    queryKey: ["clusters"],
    queryFn: fetchClusters,
    staleTime: 30_000,
  })
}
