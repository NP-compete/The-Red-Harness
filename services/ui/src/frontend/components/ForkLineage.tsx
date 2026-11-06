import { useTranslation } from 'react-i18next';
import { GitBranch } from 'lucide-react';
import { Link } from 'react-router-dom';

import { presentForkTree, type BranchSummary } from '../lib/fork-tree';

export interface LineageChat {
  id: string;
  title: string;
  forkedFrom: string | null;
  /** Absent for a conversation whose messages are not loaded. */
  messageCount?: number;
  /** How far into the parent this fork was taken. */
  forkedAt?: number | null;
}

/** Where this conversation sits among the ones it was forked from. */
export function ForkLineage({
  chats,
  currentId,
}: {
  chats: LineageChat[];
  currentId: string;
}) {
  const { t } = useTranslation();
  const byId = new Map(chats.map((chat) => [chat.id, chat]));

  // Only the line this conversation belongs to: other people's forks of
  // other conversations are not this reader's business here.
  const family = new Set<string>();
  const walkUp = (id: string | null) => {
    while (id && byId.has(id) && !family.has(id)) {
      family.add(id);
      id = byId.get(id)!.forkedFrom;
    }
  };
  walkUp(currentId);
  let grew = true;
  while (grew) {
    grew = false;
    for (const chat of chats) {
      if (chat.forkedFrom && family.has(chat.forkedFrom) && !family.has(chat.id)) {
        family.add(chat.id);
        grew = true;
      }
    }
  }

  if (family.size < 2) {
    return null;
  }

  const branches: BranchSummary[] = chats
    .filter((chat) => family.has(chat.id))
    .map((chat) => ({
      name: chat.id,
      messages: chat.messageCount ?? 0,
      from: chat.forkedFrom ?? undefined,
      // Two forks of one conversation share a parent, a title and a
      // depth. Where each was taken is what tells them apart.
      at:
        chat.forkedAt == null
          ? undefined
          : t('counts.forkedAt', { count: chat.forkedAt }),
    }));

  const tree = presentForkTree(branches, { current: currentId });

  return (
    <section className="rounded-lg border border-border bg-card p-3">
      <div className="mb-2 flex items-center gap-2">
        <GitBranch className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          {t('counts.forks', { count: tree.forkCount })}
        </span>
      </div>
      <ul className="list-none space-y-1">
        {tree.rows.map((row) => (
          <li
            key={row.name}
            data-depth={row.depth}
            aria-current={row.current ? 'true' : undefined}
            style={{ paddingLeft: `${row.depth * 12}px` }}
            className="flex items-baseline gap-2 text-xs"
          >
            {/* The point of seeing the line is being able to move
                along it; the one being read is not a link to here. */}
            {row.current ? (
              <span className="text-foreground">
                {byId.get(row.name)?.title ?? row.name}
              </span>
            ) : (
              <Link
                to={`/chat/${row.name}`}
                className="text-muted-foreground hover:text-foreground hover:underline"
              >
                {byId.get(row.name)?.title ?? row.name}
              </Link>
            )}
            {/* Only the open conversation has its messages loaded,
                so "0 messages" would be a claim about threads whose
                length is simply not known here. */}
            {row.messages > 0 && (
              <span className="text-[11px] text-muted-foreground">
                {t('counts.messages', { count: row.messages })}
              </span>
            )}
            {row.takenAt && (
              <span className="text-[11px] text-muted-foreground">
                {row.takenAt}
              </span>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
