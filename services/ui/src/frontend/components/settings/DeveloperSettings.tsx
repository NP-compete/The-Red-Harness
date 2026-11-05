import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, Bot, FolderTree, LoaderCircle, Paperclip, Puzzle, Radio, Receipt, Search, Server, Sparkles, Wrench } from 'lucide-react';
import { cn } from '@/lib/utils';
import { EvalDashboard } from './eval';
import { SkillSource } from './SkillSource';
import { useAppSelector } from '../../redux/hooks';
import type { RootState } from '../../redux/store';
import { fetchAgentStructure, type AgentNode, type AgentStructure } from '../../services/agent-structure';
import { useTranslation } from 'react-i18next';
import { ChannelsSection } from './ChannelsSection';
import { ExtractionStatus } from './ExtractionStatus';
import { Extensions } from './Extensions';
import { ModelPrices } from './ModelPrices';
import { SystemHealth } from './SystemHealth';
import { ReindexControl } from './ReindexControl';
import { SchemaVersion } from './SchemaVersion';
import { InboundDoor } from './InboundDoor';
import { MyAllowance } from './MyAllowance';

/**
 * The symbol for each kind of thing in the diagram, and the word for it.
 *
 * Declared together so the group heading and the chips under it can never
 * disagree — the heading is the legend, sitting against the things it
 * explains rather than in a key somewhere else. `Server` and `Wrench` are
 * what the MCP and tool lists elsewhere in Settings already use.
 */
// Keys, not words: this table is built once at module load,
// where there is no translator to call. `MCP` is a key too, so
// the table has one rule rather than an exception.
const KIND = {
  skill: { icon: Sparkles, labelKey: 'devtools.skills' },
  mcp: { icon: Server, labelKey: 'devtools.mcp' },
  tool: { icon: Wrench, labelKey: 'devtools.tools' },
} as const;

type CapabilityKind = keyof typeof KIND;

/**
 * A skill or an MCP server hanging under the agent that holds it.
 *
 * A skill opens its source — the same modal the Skills panel uses, so the
 * operating instructions behind a capability are one click from the picture
 * of who holds it. An MCP server has no equivalent endpoint, so it stays a
 * label rather than pretending to be pressable.
 */
function CapabilityChip({
  label,
  kind,
  shared,
  onOpen,
}: {
  label: string;
  kind: CapabilityKind;
  shared: boolean;
  onOpen?: () => void;
}) {
  const Icon = KIND[kind].icon;
  const className = cn(
    'flex w-full items-center gap-1.5 rounded border px-2 py-1 text-left text-xs',
    shared
      ? 'border-primary/40 bg-primary/5 text-foreground'
      : 'border-border bg-background text-muted-foreground',
    onOpen &&
      'transition-colors hover:border-primary/60 hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary',
  );
  const title = shared ? `${label} — also held by another subagent` : label;

  return (
    <li className="relative">
      {onOpen ? (
        <button type="button" onClick={onOpen} className={className} title={`${title} — open source`}>
          <Icon className="h-3 w-3 shrink-0 opacity-70" aria-hidden="true" />
          <span className="truncate">{label}</span>
        </button>
      ) : (
        <span className={className} title={title}>
          <Icon className="h-3 w-3 shrink-0 opacity-70" aria-hidden="true" />
          <span className="truncate">{label}</span>
        </span>
      )}
    </li>
  );
}

/** One subagent and everything attached to it, as a single column. */
function AgentColumn({
  agent,
  sharedNames,
  onOpenSkill,
  onOpenAgent,
}: {
  agent: AgentNode;
  sharedNames: Set<string>;
  onOpenSkill: (name: string) => void;
  onOpenAgent: (name: string) => void;
}) {
  const { t } = useTranslation();
  const skills = agent.skills ?? [];
  const mcps = agent.mcps ?? [];
  const tools = agent.tools ?? [];
  const empty = skills.length + mcps.length + tools.length === 0;

  const group = (kind: CapabilityKind, items: string[]) => {
    const Icon = KIND[kind].icon;
    return items.length > 0 ? (
      <div className="mt-2">
        <p className="mb-1 flex items-center gap-1 text-[0.625rem] font-medium uppercase tracking-wide text-muted-foreground">
          <Icon className="h-2.5 w-2.5 shrink-0" aria-hidden="true" />
          {t(KIND[kind].labelKey)}
        </p>
        <ul className="space-y-1">
          {items.map((item) => (
            <CapabilityChip
              key={item}
              label={item}
              kind={kind}
              shared={sharedNames.has(`${kind}:${item}`)}
              onOpen={kind === 'skill' ? () => onOpenSkill(item) : undefined}
            />
          ))}
        </ul>
      </div>
    ) : null;
  };

  return (
    <div className="flex w-52 shrink-0 flex-col px-2">
      <button
        type="button"
        onClick={() => onOpenAgent(agent.name)}
        title={`${agent.name} — open prompt`}
        className={cn(
          'w-full rounded-lg border border-border bg-secondary/30 px-3 py-2 text-center transition-colors',
          'hover:border-primary/60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary',
        )}
      >
        <span className="flex items-center justify-center gap-1.5">
          <Bot className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
          <span className="truncate text-sm font-medium text-foreground">{agent.name}</span>
        </span>
      </button>
      {/* The stem the capabilities hang from. Nothing crosses it, which is
          the whole reason they are grouped by owner rather than pooled in a
          column of their own. */}
      {!empty ? <div className="mx-auto h-3 w-px bg-border" aria-hidden="true" /> : null}
      {empty ? (
        <p className="mt-2 text-center text-xs text-amber-500">nothing attached</p>
      ) : (
        <div className="rounded-lg border border-dashed border-border/70 p-2">
          {group('skill', skills)}
          {group('mcp', mcps)}
          {group('tool', tools)}
        </div>
      )}
    </div>
  );
}

/**
 * The structure as a tree: delegation across the top, and what each agent
 * holds hanging directly beneath it.
 *
 * Two earlier attempts are worth not repeating. A tree of counts with the
 * names in an accordion below meant reading the shape in one place and the
 * contents in another. Pooling every capability into a second column and
 * joining them with edges put the names on screen, but 28 edges between two
 * tall columns is a hairball — no node's connections can be followed by eye,
 * which is the one thing a graph is for.
 *
 * Grouping by owner means no edge crosses another: each capability sits
 * under the one agent that holds it. What that loses is sharing, so the
 * handful of capabilities held by more than one subagent are tinted, rather
 * than every relationship being drawn to make a few of them visible.
 */
function AgentStructureGraph({ structure }: { structure: AgentStructure }) {
  const { t } = useTranslation();
  const { main, children, shared, unattached } = useMemo(() => {
    const orchestrator = structure.orchestrator;
    const rootNames = (orchestrator.subagents ?? []).filter((name) => structure.subagents[name]);
    const subagents = (rootNames.length > 0 ? rootNames : Object.keys(structure.subagents))
      .map((name) => structure.subagents[name])
      .filter(Boolean);

    // Sharing between subagents only. The orchestrator holds the superset,
    // so counting it would tint every chip on screen and mean nothing.
    const holders = new Map<string, number>();
    for (const agent of subagents) {
      for (const skill of agent.skills ?? []) holders.set(`skill:${skill}`, (holders.get(`skill:${skill}`) ?? 0) + 1);
      for (const mcp of agent.mcps ?? []) holders.set(`mcp:${mcp}`, (holders.get(`mcp:${mcp}`) ?? 0) + 1);
    }
    const sharedKeys = new Set([...holders.entries()].filter(([, n]) => n > 1).map(([k]) => k));

    const everywhere = new Set<string>();
    for (const agent of [orchestrator, ...subagents]) {
      for (const skill of agent.skills ?? []) everywhere.add(`skill:${skill}`);
      for (const mcp of agent.mcps ?? []) everywhere.add(`mcp:${mcp}`);
    }
    const orphans = [
      ...structure.available_skills.filter((n) => !everywhere.has(`skill:${n}`)),
      ...Object.keys(structure.mcp_servers).filter((n) => !everywhere.has(`mcp:${n}`)),
    ];

    return { main: orchestrator, children: subagents, shared: sharedKeys, unattached: orphans };
  }, [structure]);

  const [openSkill, setOpenSkill] = useState<string | null>(null);
  // An agent's prompt is its own endpoint — `/prompt` for the main agent,
  // `/subagents/<name>` for the rest — so the box carries both.
  const [openPrompt, setOpenPrompt] = useState<{ name: string; endpoint: string } | null>(null);

  const mainSkills = main.skills?.length ?? 0;
  const mainMcps = main.mcps?.length ?? 0;

  return (
    <div className="mt-6 space-y-3 border-t border-border pt-6">
      <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
        <FolderTree className="h-4 w-4 text-primary" aria-hidden="true" />
        {t('devtools.structure')}
      </div>

      <figure className="m-0 overflow-x-auto pb-1">
        <div className="flex min-w-max flex-col items-center px-2">
          <button
            type="button"
            onClick={() => setOpenPrompt({ name: 'PROMPT.md', endpoint: '/prompt' })}
            title={`${main.name} — open prompt`}
            className={cn(
              'rounded-lg border border-primary/40 bg-primary/5 px-4 py-2 text-center transition-colors',
              'hover:border-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary',
            )}
          >
            <span className="flex items-center justify-center gap-1.5">
              <Bot className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
              <span className="text-sm font-medium text-foreground">{main.name}</span>
            </span>
            <span className="mt-1 inline-block rounded bg-primary/10 px-1.5 py-0.5 text-[0.625rem] font-medium uppercase tracking-wide text-primary">
              {t('devtools.mainAgent')}
            </span>
            <span className="mt-1 block text-xs text-muted-foreground">
              {mainSkills === structure.available_skills.length
                ? `every skill · ${mainMcps} MCP`
                : `${mainSkills} skills · ${mainMcps} MCP`}
            </span>
          </button>

          {children.length > 0 ? (
            <>
              <div className="h-4 w-px bg-border" aria-hidden="true" />
              <div className="flex items-start">
                {children.map((child) => (
                  <div
                    key={child.name}
                    className={cn(
                      'relative pt-4',
                      // Half-width rules meeting in the middle draw the bus
                      // across the row; the outer halves are dropped so the
                      // line stops at the first and last child.
                      "before:absolute before:left-1/2 before:top-0 before:w-1/2 before:border-t before:border-border before:content-['']",
                      "after:absolute after:right-1/2 after:top-0 after:w-1/2 after:border-t after:border-border after:content-['']",
                      'first:after:hidden last:before:hidden',
                    )}
                  >
                    <div className="absolute left-1/2 top-0 h-4 w-px bg-border" aria-hidden="true" />
                    <AgentColumn
                      agent={child}
                      sharedNames={shared}
                      onOpenSkill={setOpenSkill}
                      onOpenAgent={(name) => setOpenPrompt({
                        name,
                        endpoint: `/subagents/${encodeURIComponent(name)}`,
                      })}
                    />
                  </div>
                ))}
              </div>
            </>
          ) : null}
        </div>

        <figcaption className="sr-only">
          {`${main.name} is the main agent`}
          {children.length
            ? `, delegating to ${children.map((c) => c.name).join(', ')}. Each column lists the skills and MCP servers that agent holds.`
            : ' and has no subagents.'}
        </figcaption>
      </figure>

      {unattached.length > 0 ? (
        <p className="text-xs">
          <span className="text-muted-foreground">{t('developers.heldByNoAgent')}</span>
          <span className="text-amber-500">{unattached.join(' · ')}</span>
        </p>
      ) : null}




      {openSkill ? <SkillSource name={openSkill} onClose={() => setOpenSkill(null)} /> : null}
      {openPrompt ? (
        <SkillSource
          name={openPrompt.name}
          endpoint={openPrompt.endpoint}
          onClose={() => setOpenPrompt(null)}
        />
      ) : null}
    </div>
  );
}

/**
 * The agent itself: what version is deployed, and how it is wired.
 *
 * Its own tab, and the first one, because it is the thing an operator
 * opens Developers to look at. It used to be a collapsible section above
 * the evaluation dashboard, which meant the structure of the agent was
 * reached through a tab called "Evaluations".
 */
export function AgentInformation() {
  const { t } = useTranslation();
  const branding = useAppSelector((state: RootState) => state.config.branding);
  const [structure, setStructure] = useState<AgentStructure | null>(null);
  const [loadingStructure, setLoadingStructure] = useState(false);
  const [structureError, setStructureError] = useState<string | null>(null);

  const loadAgentStructure = useCallback(async () => {
    if (structure || loadingStructure) return;

    setLoadingStructure(true);
    setStructureError(null);
    try {
      setStructure(await fetchAgentStructure());
    } catch {
      setStructureError(t('devtools.structureUnavailable'));
    } finally {
      setLoadingStructure(false);
    }
  }, [structure, loadingStructure]);

  useEffect(() => { loadAgentStructure(); }, [loadAgentStructure]);

  return (
    <div>
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">{t('devtools.agentVersion')}</span>
        <code className="rounded bg-muted px-2 py-1 text-sm font-medium">
          {branding?.version ?? '—'}
        </code>
      </div>
      {/* Under the build, because the pair is the question: which
          layout this image reads, and which one it was given. */}
      <SchemaVersion />
      <InboundDoor />
      {/* What the reader may spend today, before they start
          something long rather than part-way through it. */}
      <MyAllowance />
      {loadingStructure ? (
        <div className="mt-4 flex items-center gap-2 text-sm text-muted-foreground" role="status">
          <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
          {t('devtools.loading')}
        </div>
      ) : null}
      {structureError ? (
        <p className="mt-4 text-sm text-muted-foreground">{structureError}</p>
      ) : null}
      {structure ? <AgentStructureGraph structure={structure} /> : null}
      {/* Beside the diagram, not inside it: none of these is about
          the agent's shape, and nesting them there meant one failed
          request took all three away. */}
      <div className="mt-6 space-y-3 border-t border-border pt-6">
        <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <Radio className="h-4 w-4 text-primary" aria-hidden="true" />
          {t('devtools.channels')}
        </div>
        <ChannelsSection />
      </div>

      <div className="mt-6 space-y-3 border-t border-border pt-6">
        <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <Search className="h-4 w-4 text-primary" aria-hidden="true" />
          {t('devtools.searchIndex')}
        </div>
        <ReindexControl />
      </div>

      <div className="mt-6 space-y-3 border-t border-border pt-6">
        <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <Paperclip className="h-4 w-4 text-primary" aria-hidden="true" />
          {t('devtools.attachments')}
        </div>
        <ExtractionStatus />
      </div>

      <div className="mt-6 space-y-3 border-t border-border pt-6">
        <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <Activity className="h-4 w-4 text-primary" aria-hidden="true" />
          {t('devtools.dependsOn')}
        </div>
        <SystemHealth />
      </div>

      <div className="mt-6 space-y-3 border-t border-border pt-6">
        <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <Puzzle className="h-4 w-4 text-primary" aria-hidden="true" />
          {t('devtools.interposes')}
        </div>
        <Extensions />
      </div>

      {/* Beside the dependencies because both answer "what is this
          deployment actually configured with": a cost on a run is
          only checkable against the price that produced it. */}
      <div className="mt-6 space-y-3 border-t border-border pt-6">
        <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <Receipt className="h-4 w-4 text-primary" aria-hidden="true" />
          {t('devtools.pricing')}
        </div>
        <ModelPrices />
      </div>
    </div>
  );
}

/** The evaluation dashboard, which is now all this tab holds. */
export function DeveloperSettings() {
  return <EvalDashboard />;
}
