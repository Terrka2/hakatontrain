// Геометрия маркеров. Сами кластеры и баллы приходят из API или из mock-«города» (lib/mock-city).

/** Диаметр маркера: 28 px за одно обращение, +6 px за каждое следующее, не больше 52 px. */
export function markerSize(reportCount: number): number {
  return Math.min(52, 28 + 6 * Math.max(0, reportCount - 1))
}
