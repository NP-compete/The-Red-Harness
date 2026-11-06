export interface ConfigFile {
  path: string;
  baseline?: string;
  overlay?: string;
  author?: string;
  at?: string;
}

export type DriftAction = 'adopt-baseline' | 'export';

export interface DriftRow {
  path: string;
  baseline?: string;
  current: string;
  author?: string;
  at?: string;
  actions: DriftAction[];
}

export interface DriftSummary {
  rows: DriftRow[];
  pinned: string[];
  count: number;
  warning?: string;
}

const WARNING =
  'These files were edited here, so changes from your pipeline no longer reach them.';

export function summariseDrift(
  files: ConfigFile[],
  options: { readOnly?: boolean } = {},
): DriftSummary {
  const edited = files.filter((file) => file.overlay !== undefined);

  // An edit that matches the pipeline is a pin, not a divergence: worth
  // showing, but not worth asking anybody to reconcile.
  const pinned = edited
    .filter((file) => file.overlay === file.baseline)
    .map((file) => file.path)
    .sort();

  const rows = edited
    .filter((file) => file.overlay !== file.baseline)
    .sort((a, b) => a.path.localeCompare(b.path))
    .map<DriftRow>((file) => ({
      path: file.path,
      baseline: file.baseline,
      current: file.overlay as string,
      author: file.author,
      at: file.at,
      // Export survives read-only. It is how a drifted
      // deployment gets back: commit the effective tree,
      // reconcile, and the overrides can go. Dropping every
      // action here shut the way out at the moment it was
      // needed — read-only means the deployment cannot be
      // edited, not that it is no longer drifted.
      actions: options.readOnly
        ? (['export'] as DriftAction[])
        : (['adopt-baseline', 'export'] as DriftAction[]),
    }));

  return {
    rows,
    pinned,
    count: rows.length,
    warning: rows.length > 0 ? WARNING : undefined,
  };
}
