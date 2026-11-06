import { useEffect, useState } from 'react';
import { Radio } from 'lucide-react';

import { listChannels, type Channel } from '../../services/channels-api';
import { useTranslation } from 'react-i18next';

/** Where this agent can be reached, besides this window. */
export function ChannelsSection() {
  const { t } = useTranslation();
  const [channels, setChannels] = useState<Channel[] | null>(null);

  useEffect(() => {
    let alive = true;
    void listChannels().then((found) => {
      if (alive) setChannels(found);
    });
    return () => {
      alive = false;
    };
  }, []);

  // Nothing is said before the answer is in: an empty list and an
  // unasked question look the same otherwise.
  if (channels === null) {
    return null;
  }

  if (channels.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        {t('settings.noChannels')}</p>
    );
  }

  return (
    <ul className="list-none space-y-2">
      {channels.map((channel) => (
        <li
          key={channel.name}
          className="flex items-center gap-2 rounded-lg border border-border bg-card p-3"
        >
          <Radio className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
          <span className="text-sm text-foreground">{channel.name}</span>
          <span className="rounded-full border border-border px-2 py-0.5 text-xs text-muted-foreground">
            {channel.type}
          </span>
        </li>
      ))}
    </ul>
  );
}
