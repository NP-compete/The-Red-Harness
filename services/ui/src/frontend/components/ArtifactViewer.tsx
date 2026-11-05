import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, Label } from '@patternfly/react-core';
import { Copy, Check, FileText, Code, FileJson } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
import { markdownSanitizeSchema } from '../lib/markdown-sanitize';
import { detectArtifactKind, type ArtifactKind } from '../types/deep-agent';
import { normalizeListIndent } from "@/lib/normalize-list-indent";

interface ArtifactViewerProps {
  readonly content: string;
  readonly title?: string;
}

// Keys rather than words. The format names are keys too, so a
// locale that writes them differently can, and so this table does
// not quietly become the one place English survives.
const KIND_META: Record<ArtifactKind, { labelKey: string; color: 'blue' | 'purple' | 'orange' | 'grey'; icon: typeof FileText }> = {
  code: { labelKey: 'artifacts.code', color: 'purple', icon: Code },
  json: { labelKey: 'artifacts.json', color: 'orange', icon: FileJson },
  markdown: { labelKey: 'artifacts.markdown', color: 'blue', icon: FileText },
  text: { labelKey: 'artifacts.text', color: 'grey', icon: FileText },
};

export function ArtifactViewer({ content, title }: ArtifactViewerProps) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  const kind = detectArtifactKind(content);
  const meta = KIND_META[kind];
  const KindIcon = meta.icon;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard unavailable (e.g. non-secure context) */
    }
  };

  return (
    <div className="border border-border rounded-lg overflow-hidden bg-card">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-muted/30">
        <div className="flex items-center gap-2">
          <KindIcon className="w-3.5 h-3.5 text-muted-foreground" />
          {title && <span className="text-xs font-medium text-foreground">{title}</span>}
          <Label isCompact color={meta.color}>{t(meta.labelKey)}</Label>
        </div>
        <Button
          variant="plain"
          size="sm"
          className="p-1!"
          onClick={handleCopy}
          aria-label={t('artifacts.copy')}
        >
          {copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
        </Button>
      </div>

      <div className="max-h-80 overflow-auto p-3">
        {kind === 'markdown' ? (
          <div className="md-prose max-w-none text-sm">
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[[rehypeSanitize, markdownSanitizeSchema]]}>{normalizeListIndent(content)}</ReactMarkdown>
          </div>
        ) : kind === 'json' ? (
          <pre className="text-xs font-mono text-foreground whitespace-pre-wrap">
            {(() => { try { return JSON.stringify(JSON.parse(content), null, 2); } catch { return content; } })()}
          </pre>
        ) : (
          <pre className="text-xs font-mono text-foreground whitespace-pre-wrap">{content}</pre>
        )}
      </div>
    </div>
  );
}
