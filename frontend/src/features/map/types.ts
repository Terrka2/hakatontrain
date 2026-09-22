// Типы данных карты — из общих моделей контрактов (frontend/src/lib/contracts.ts).
import type { BBox } from "@/lib/ui-state"

export type {
  ClusterOut,
  CrewRoute,
  GeoPoint,
  RouteStop,
} from "@/lib/contracts"
export type { BBox }

import type { ClusterOut, CrewRoute } from "@/lib/contracts"

export type MapLayer =
  | { kind: "clusters"; items: ClusterOut[]; selectedId?: string }
  | { kind: "routes"; routes: CrewRoute[] }
  | { kind: "crew"; route: CrewRoute }
