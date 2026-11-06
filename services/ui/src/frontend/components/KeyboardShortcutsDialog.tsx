import type { ReactNode } from 'react';
import {
  Button,
  Content,
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
  ModalVariant,
} from '@patternfly/react-core';

// Built once at module load, outside any component, so the
// catalogue is read from the instance rather than a hook.
import i18n from '../i18n';

export interface KeyboardShortcutsDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="inline-flex items-center rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-xs text-foreground shadow-sm">
      {children}
    </kbd>
  );
}

const rows: { combo: ReactNode; action: string }[] = [
  {
    combo: <Kbd>/</Kbd>,
    action: i18n.t('shortcuts.focusInput'),
  },
  {
    combo: <Kbd>Esc</Kbd>,
    action: i18n.t('shortcuts.cancelStream'),
  },
  {
    combo: (
      <span className="inline-flex flex-wrap items-center gap-1">
        <Kbd>Ctrl</Kbd>
        <span className="text-muted-foreground">+</span>
        <Kbd>N</Kbd>
        <span className="text-xs text-muted-foreground">{i18n.t('shortcuts.macNewChat')}</span>
      </span>
    ),
    action: i18n.t('shortcuts.newChat'),
  },
  {
    combo: (
      <span className="inline-flex flex-wrap items-center gap-1">
        <Kbd>Ctrl</Kbd>
        <span className="text-muted-foreground">+</span>
        <Kbd>Shift</Kbd>
        <span className="text-muted-foreground">+</span>
        <Kbd>S</Kbd>
        <span className="text-xs text-muted-foreground">{i18n.t('shortcuts.macSearch')}</span>
      </span>
    ),
    action: i18n.t('shortcuts.openSettings'),
  },
  {
    combo: <Kbd>?</Kbd>,
    action: i18n.t('shortcuts.showDialog'),
  },
  {
    combo: (
      <span className="inline-flex flex-wrap items-center gap-1">
        <Kbd>Ctrl</Kbd>
        <span className="text-muted-foreground">+</span>
        <Kbd>Shift</Kbd>
        <span className="text-muted-foreground">+</span>
        <Kbd>E</Kbd>
        <span className="text-xs text-muted-foreground">{i18n.t('shortcuts.macEdit')}</span>
      </span>
    ),
    action: i18n.t('shortcuts.exportChat'),
  },
];

export function KeyboardShortcutsDialog({ isOpen, onClose }: KeyboardShortcutsDialogProps) {
  return (
    <Modal
      variant={ModalVariant.small}
      isOpen={isOpen}
      onClose={onClose}
      aria-label={i18n.t('shortcuts.title')}
    >
      <ModalHeader title={i18n.t('shortcuts.heading')} />
      <ModalBody>
        <Content>
          <div className="rounded-lg border border-border overflow-hidden">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-border bg-muted/60">
                  <th className="text-left font-semibold px-3 py-2 w-[45%]">{i18n.t('shortcuts.shortcut')}</th>
                  <th className="text-left font-semibold px-3 py-2">{i18n.t('shortcuts.action')}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.action} className="border-b border-border last:border-b-0">
                    <td className="px-3 py-2 align-top">{row.combo}</td>
                    <td className="px-3 py-2 text-foreground/90">{row.action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Content>
      </ModalBody>
      <ModalFooter>
        <Button variant="primary" onClick={onClose}>
          Close
        </Button>
      </ModalFooter>
    </Modal>
  );
}
