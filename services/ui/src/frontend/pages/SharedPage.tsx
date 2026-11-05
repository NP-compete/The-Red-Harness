import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';
import { Spinner } from '@patternfly/react-core';
import { Paperclip } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import rehypeSanitize from 'rehype-sanitize';
import remarkGfm from 'remark-gfm';

import { markdownSanitizeSchema } from '../lib/markdown-sanitize';

import { readShared, type SharedConversation } from '../services/shared-read';
import { normalizeListIndent } from "@/lib/normalize-list-indent";

function textOf(content: unknown): string {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    return content
      .map((part) =>
        part && typeof part === 'object' && 'text' in part
          ? String((part as { text?: unknown }).text ?? '')
          : '',
      )
      .join('');
  }
  return '';
}

/**
 * A conversation someone shared.
 *
 * Read-only by construction: this is a snapshot taken when the link
 * was made, not a window onto a conversation that has since moved on.
 */
export function SharedPage() {
  const { t } = useTranslation();
  const { shareId } = useParams<{ shareId: string }>();
  const [found, setFound] = useState<SharedConversation | null>(null);

  useEffect(() => {
    if (!shareId) return;
    let alive = true;
    void readShared(shareId).then((result) => {
      if (alive) setFound(result);
    });
    return () => {
      alive = false;
    };
  }, [shareId]);

  if (!found) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner size="lg" aria-label={t('shared.opening')} />
      </div>
    );
  }

  if (found.state !== 'ok') {
    return (
      <div className="mx-auto max-w-xl px-8 py-16 text-center">
        <p className="text-sm text-foreground">{message(found, t)}</p>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-3xl px-8 py-10">
      <header className="mb-6">
        <h1 className="text-xl font-semibold text-foreground">{found.title}</h1>
        <p className="mt-1 text-xs text-muted-foreground">
          {t('share.snapshotLine', {
            taken: found.capturedAt
              ? t('share.snapshotTaken', { date: found.capturedAt.slice(0, 10) })
              : '',
          })}
        </p>
      </header>

      <ol className="list-none space-y-4">
        {found.messages.map((message, index) => (
          <li key={index} className={message.type === 'human' ? 'text-right' : ''}>
            <span className="inline-block max-w-[80%] rounded-2xl border border-border bg-card px-4 py-2 text-left text-sm text-foreground">
              {message.type === 'human' ? (
                // A question is shown as it was typed: markdown in it was
                // never meant as formatting.
                <span className="whitespace-pre-wrap">{textOf(message.content)}</span>
              ) : (
                <div className="space-y-2 [&_h1]:text-base [&_h2]:text-sm [&_h3]:text-sm [&_h1]:font-semibold [&_h2]:font-semibold [&_h3]:font-semibold [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_code]:font-mono [&_code]:text-xs">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[[rehypeSanitize, markdownSanitizeSchema]]}
                  >
                    {normalizeListIndent(textOf(message.content))}
                  </ReactMarkdown>
                </div>
              )}
            </span>
          </li>
        ))}
      </ol>

      {found.attachmentNames.length > 0 && (
        <section className="mt-8 border-t border-border pt-4">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {t('shared.attachments')}
          </p>
          {/* Named only: the files themselves are not part of a share. */}
          <ul className="mt-2 list-none space-y-1">
            {found.attachmentNames.map((name) => (
              <li key={name} className="flex items-center gap-2 text-xs text-muted-foreground">
                <Paperclip className="h-3 w-3" />
                {name}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function message(found: SharedConversation, t: (key: string) => string): string {
  switch (found.state) {
    case 'gone':
      // The agent's own words for why it is gone, already in the
      // reader's language — a key here would overwrite them.
      return found.reason;
    case 'missing':
      return t('shared.badLink');
    case 'sign-in':
      return t('shared.signIn');
    default:
      return t('shared.unavailable');
  }
}
