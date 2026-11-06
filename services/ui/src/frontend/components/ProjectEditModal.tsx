import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Button,
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
  ModalVariant,
  TextInput,
  TextArea,
  FormGroup,
} from '@patternfly/react-core';

interface ProjectEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (name: string, description: string) => boolean | void | 'error' | Promise<boolean | void | 'error'>;
  initialName?: string;
  initialDescription?: string;
  title?: string;
}

export function ProjectEditModal({
  isOpen,
  onClose,
  onSave,
  initialName = '',
  initialDescription = '',
  title = 'New Project',
}: ProjectEditModalProps) {
  const { t } = useTranslation();
  const [name, setName] = useState(initialName);
  const [description, setDescription] = useState(initialDescription);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setName(initialName);
      setDescription(initialDescription);
      setError(null);
      setSaving(false);
    }
  }, [isOpen, initialName, initialDescription]);

  const handleSave = async () => {
    const trimmed = name.trim();
    if (!trimmed || saving) return;
    setSaving(true);
    setError(null);
    try {
      const ok = await onSave(trimmed, description.trim());
      if (ok === false) {
        setError(t('projects.nameTaken'));
        return;
      }
      if (ok === 'error') {
        setError(t('projects.saveFailed'));
        return;
      }
      onClose();
    } catch {
      setError(t('projects.saveFailed'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      variant={ModalVariant.small}
      isOpen={isOpen}
      onClose={onClose}
      aria-label={title}
    >
      <ModalHeader title={title} />
      <ModalBody>
        <FormGroup label={t('projects.name')} isRequired fieldId="project-name">
          <TextInput
            id="project-name"
            value={name}
            validated={error ? 'error' : 'default'}
            onChange={(_e, val) => {
              setName(val);
              setError(null);
            }}
            onKeyDown={(e) => e.key === 'Enter' && void handleSave()}
            autoFocus
          />
          {error && (
            <p className="text-sm text-destructive mt-1" role="alert">
              {error}
            </p>
          )}
        </FormGroup>
        <FormGroup label={t('projects.description')} fieldId="project-desc" className="mt-3">
          <TextArea
            id="project-desc"
            value={description}
            onChange={(_e, val) => setDescription(val)}
            rows={3}
          />
        </FormGroup>
      </ModalBody>
      <ModalFooter>
        <Button
          variant="primary"
          onClick={() => void handleSave()}
          isDisabled={!name.trim() || saving}
        >
          {t('common.save')}
        </Button>
        <Button variant="link" onClick={onClose}>
          {t('common.cancel')}
        </Button>
      </ModalFooter>
    </Modal>
  );
}
