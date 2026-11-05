export interface ConnectPause {
  server: string;
  scopes: string[];
  reason: string;
}

export interface PresentedConnectPrompt {
  title: string;
  detail: string;
  permissions: string[];
  note: string;
  choices: Array<'connect' | 'skip'>;
  skipConsequence: string;
  changesData: boolean;
}

const WRITE_SCOPES = new Set(['write', 'send', 'delete', 'admin']);

export function presentConnectPrompt(pause: ConnectPause): PresentedConnectPrompt {
  return {
    title: `Connect ${pause.server}?`,
    detail: pause.reason
      ? `The agent wants to use ${pause.server} ${pause.reason}.`
      : `The agent wants to use ${pause.server}.`,
    permissions: pause.scopes,
    // The agent acts as the person, so connecting lends their access
    // rather than granting the deployment a new one.
    note: 'The agent will use your own access to this system.',
    choices: ['connect', 'skip'],
    skipConsequence: 'The agent will carry on without it and may not be able to finish.',
    changesData: pause.scopes.some((scope) => WRITE_SCOPES.has(scope)),
  };
}
