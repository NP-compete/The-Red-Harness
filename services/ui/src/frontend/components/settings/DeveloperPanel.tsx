import { useState } from 'react';
import { ConfigProblems } from './ConfigProblems';
import { useTranslation } from 'react-i18next';
import { Tab, Tabs, TabTitleText } from '@patternfly/react-core';
import { AnalyticsPage } from '../../pages/AnalyticsPage';
import { ConfigDrift } from './ConfigDrift';
import { ConfigEditor } from './ConfigEditor';
import { InterfaceConfigView } from './InterfaceConfig';
import { SettingsFields } from './SettingsFields';
import { UserProfileAdmin } from './UserProfileAdmin';
import { AdminPage } from '../../pages/AdminPage';
import { AgentInformation, DeveloperSettings } from './DeveloperSettings';

/**
 * Operator surfaces, grouped.
 *
 * Usage, Evaluations and Feature flags were three entries in the
 * outer bar that share one audience and one gate: a privileged role
 * plus developer mode. Three tabs that appear and disappear together
 * are one tab.
 *
 * Unlike Components, there is no per-section flag. These are not
 * things a deployment chooses to show or hide — they are things only
 * operators may see at all, and the agent enforces that
 * independently (`/analytics/*` and `/documents/*` return 403 without
 * the role). A switch here would imply a choice that does not exist.
 */
const SECTIONS = [
  // First: what the agent is, before what it costs or how it scores.
  { key: 'agent', render: () => <AgentInformation /> },
  { key: 'usage', render: () => <AnalyticsPage embedded /> },
  { key: 'flags', render: () => <AdminPage embedded /> },
  // Beside the flags: both answer "what has this deployment
  // been changed to", and somebody chasing a surprise checks
  // them together.
  {
    key: 'configuration',
    render: () => (
      <>
        <ConfigEditor />
        <ConfigDrift />
        {/* The same question as drift, for the half of the
            configuration that is not in a file. */}
        <SettingsFields />
        {/* Last: the interface's own file. Each service shows the
            configuration it actually reads, which is the only
            division that does not lie. */}
        <InterfaceConfigView />
      </>
    ),
  },
  // Beside the configuration surfaces: all of these answer "what
  // has this deployment been set to", and a person's profile is
  // the one piece of that which is about somebody rather than
  // something.
  { key: 'people', render: () => <UserProfileAdmin /> },
  { key: 'evaluations', render: () => <DeveloperSettings /> },
] as const;

export function DeveloperPanel() {
  const { t } = useTranslation();
  const [active, setActive] = useState(0);

  return (
    <>
    {/* Above the tabs, not inside one: the agent is running
        something other than what was written, and that is true
        whichever tab somebody came here for. */}
    <ConfigProblems />
    <Tabs
      activeKey={active}
      onSelect={(_e, key) => setActive(Number(key))}
      aria-label={t('developers.title')}
    >
      {SECTIONS.map((section, i) => (
        <Tab
          key={section.key}
          eventKey={i}
          title={<TabTitleText>{t(`developers.tabs.${section.key}`)}</TabTitleText>}
        >
          {/* Mounted only while selected. Usage fires four requests
              on mount; rendering all three up front would run them
              for someone who came to flip a flag.
              Padding lives here, once, rather than in each section —
              repeating it is how one of them ended up without any. */}
          {active === i && <div className="pt-5">{section.render()}</div>}
        </Tab>
      ))}
    </Tabs>
    </>
  );
}
