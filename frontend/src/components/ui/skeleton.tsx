import { cn } from "@/lib/utils"

type Props = React.ComponentProps<"div"> & {
  /** Список из N строк-заглушек (для очередей и карточек). Без rows — один прямоугольник. */
  rows?: number
}

function Skeleton({ className, rows, ...props }: Props) {
  if (rows && rows > 0) {
    return (
      <div aria-busy="true" className={cn("flex flex-col gap-3", className)} {...props}>
        {Array.from({ length: rows }, (_, i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="size-6 shrink-0 animate-pulse rounded-full bg-accent" />
            <div className="h-4 flex-1 animate-pulse rounded-md bg-accent" />
            <div className="h-4 w-12 animate-pulse rounded-md bg-accent" />
          </div>
        ))}
      </div>
    )
  }
  return (
    <div
      data-slot="skeleton"
      className={cn("bg-accent animate-pulse rounded-md", className)}
      {...props}
    />
  )
}

export { Skeleton }
