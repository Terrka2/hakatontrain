type Props = { block: string; title: string; contract: string }

/** Заглушка каркаса C0: экран ждёт своего блока. Удаляется владельцем блока вместе с первым PR. */
export function BlockPlaceholder({ block, title, contract }: Props) {
  return (
    <div className="flex h-full min-h-[60vh] flex-col items-center justify-center gap-2 text-center">
      <span className="rounded-md border px-2 py-1 font-mono text-sm">
        {block}
      </span>
      <h1 className="text-2xl">{title}</h1>
      <p className="text-muted-foreground">
        Экран ещё не реализован. Контракт: docs/contracts/{contract}
      </p>
    </div>
  )
}
