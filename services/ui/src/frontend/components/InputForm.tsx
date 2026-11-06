import {
  forwardRef,
  useCallback,
  useEffect,
  useState,
  type ClipboardEvent,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { cn } from "@/lib/utils";
import { ArrowUp, Loader2, Mic, Paperclip, Square } from "lucide-react";
import { Alert } from "@patternfly/react-core";
import { useDictation } from "../hooks/useDictation";
import { AttachButton } from "./AttachButton";
import { draftStorage } from "../services/draftStorage";
import { DraftNotice } from "./DraftNotice";
import { AttachmentChip } from "./AttachmentChip";
import { StopButton } from "./StopButton";
import { CommandPalette } from "./CommandPalette";
import { ReferencePalette } from "./ReferencePalette";
import { useReferenceable } from "../hooks/useReferenceable";
import { RateLimitNotice } from "./RateLimitNotice";
import { SecretWarning } from "./SecretWarning";
import { useCommands } from "../hooks/useCommands";
import type { RunStage } from "../lib/cancel-view";
import {
  dragHasFiles,
  filesFromPaste,
  useAttachmentUpload,
} from "../hooks/useAttachmentUpload";
import { useTranslation } from "react-i18next";
import type { Attachment } from "../services/attachments-api";
import { ReasoningSelector } from './ReasoningSelector';
import { useReasoningProfiles } from '../hooks/useReasoningProfiles';

interface InputFormProps {
  onSubmit: (inputValue: string) => void;
  onCancel: () => void;
  isLoading: boolean;
  isRateLimited?: boolean;
  rateLimitRemainingSeconds?: number;
  /** Thread to attach files to. Omit to hide the attach button. */
  threadId?: string;
  /** What the run in flight is doing, so the stop control can be honest. */
  runStage?: RunStage;
  toolInFlight?: string;
  toolIsReversible?: boolean;
  onAttached?: (attachments: Attachment[], summary: string) => void;
  /** Overrides the default placeholder, which the home screen takes
      from config rather than from the translation catalogue. */
  placeholder?: string;
  /** Overrides the textarea's accessible name. */
  ariaLabel?: string;
}

export const InputForm = forwardRef<HTMLTextAreaElement, InputFormProps>(function InputForm(
  {
  onSubmit,
  onCancel,
  isLoading,
  isRateLimited = false,
  rateLimitRemainingSeconds = 0,
  threadId,
  runStage = 'thinking',
  toolInFlight = '',
  toolIsReversible = true,
  onAttached,
  placeholder,
  ariaLabel,
  },
  ref,
) {
  const { t } = useTranslation();
  const [internalInputValue, setInternalInputValue] = useState("");
  const [attached, setAttached] = useState<Attachment[]>([]);
  const commands = useCommands();
  const [attachError, setAttachError] = useState<string | null>(null);
  const [draggingFiles, setDraggingFiles] = useState(false);

  // Specialists and files, for naming one part way through a
  // sentence. Both are already open to this person elsewhere.
  const referenceable = useReferenceable();

  // A transcript is a guess, so it lands in the composer to be read
  // and corrected — never sent on the speaker's behalf.
  const dictation = useDictation(
    useCallback((heard: string) => {
      setInternalInputValue((typed) => (typed ? `${typed.trimEnd()} ${heard}` : heard));
    }, []),
  );

  // Attachments belong to the thread they were staged for. Without
  // this the composer carried them into the next conversation and
  // showed files as attached that the new thread has never seen.
  useEffect(() => {
    setAttached([]);
    setAttachError(null);
  }, [threadId]);

  // Empty unless the deployment's profiles would send different
  // requests; the selector renders nothing on an empty list.
  const reasoningProfiles = useReasoningProfiles();

  // Keep what is half-written against the thread it belongs to, so
  // leaving the conversation does not throw the words away.
  useEffect(() => {
    if (!threadId) return;
    const id = setTimeout(() => draftStorage.save(threadId, internalInputValue), 300);
    return () => clearTimeout(id);
  }, [threadId, internalInputValue]);

  const onUploaded = useCallback(
    (files: Attachment[], summary: string) => {
      setAttachError(null);
      setAttached((prev) => [...prev, ...files]);
      onAttached?.(files, summary);
    },
    [onAttached],
  );
  const { upload, busy: uploading } = useAttachmentUpload({
    threadId,
    onUploaded,
    onError: setAttachError,
  });

  // Drag state is tracked on the window, not on the composer. People
  // drop a file onto the conversation they are reading, not onto the
  // text box — a drop target that small reads as "drag and drop is
  // not supported".
  //
  // `dragenter`/`dragleave` fire for every element crossed, so a depth
  // counter is the only way to know the pointer has actually left:
  // tracking a boolean makes the overlay flicker on each child.
  useEffect(() => {
    if (!threadId) return;
    let depth = 0;
    const enter = (e: globalThis.DragEvent) => {
      if (!dragHasFiles(e)) return;
      depth += 1;
      setDraggingFiles(true);
    };
    const leave = (e: globalThis.DragEvent) => {
      if (!dragHasFiles(e)) return;
      depth = Math.max(0, depth - 1);
      if (depth === 0) setDraggingFiles(false);
    };
    // Without preventDefault on dragover the browser navigates away
    // to the dropped file, losing the conversation.
    const over = (e: globalThis.DragEvent) => {
      if (dragHasFiles(e)) e.preventDefault();
    };
    const drop = (e: globalThis.DragEvent) => {
      if (!dragHasFiles(e)) return;
      e.preventDefault();
      depth = 0;
      setDraggingFiles(false);
      void upload(Array.from(e.dataTransfer?.files ?? []));
    };
    window.addEventListener("dragenter", enter);
    window.addEventListener("dragleave", leave);
    window.addEventListener("dragover", over);
    window.addEventListener("drop", drop);
    return () => {
      window.removeEventListener("dragenter", enter);
      window.removeEventListener("dragleave", leave);
      window.removeEventListener("dragover", over);
      window.removeEventListener("drop", drop);
    };
  }, [threadId, upload]);

  const handlePaste = (e: ClipboardEvent<HTMLTextAreaElement>) => {
    if (!threadId) return;
    const files = filesFromPaste(e);
    if (!files.length) return;
    // Only once it is certain this is a file paste — otherwise an
    // ordinary text paste would be swallowed.
    e.preventDefault();
    void upload(files);
  };

  // Pill while it is a single empty line; panel once it holds an
  // attachment or the text has wrapped.
  const isExpanded =
    attached.length > 0 || internalInputValue.includes('\n') || internalInputValue.length > 80;

  const handleInternalSubmit = (e?: FormEvent) => {
    if (e) e.preventDefault();
    if (!internalInputValue.trim()) return;
    onSubmit(internalInputValue);
    setInternalInputValue("");
    // Sent is not unsent: nothing to offer back.
    if (threadId) draftStorage.discard(threadId);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleInternalSubmit();
    }
  };

  // Blocked while a file is still uploading. Sending first means the
  // run starts before the attachment lands on the thread, so the model
  // answers about a document it cannot see — and the file appears in
  // the composer a second later, which looks like it was attached.
  const isSubmitDisabled =
    !internalInputValue.trim() || isLoading || isRateLimited || uploading;

  return (
    <>
      {draggingFiles && (
        // Covers the viewport because that is the drop target.
        // `pointer-events-none` so it cannot steal the drop from the
        // window listener that is actually handling it.
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 pointer-events-none"
          aria-hidden="true"
        >
          <div className="rounded-2xl border-2 border-dashed border-primary bg-card px-8 py-6 text-center shadow-elevated">
            <Paperclip className="mx-auto mb-2 h-6 w-6 text-primary" />
            <p className="text-sm font-medium text-foreground">
              {t('input.dropToAttach')}
            </p>
          </div>
        </div>
      )}
    <form
      onSubmit={handleInternalSubmit}
      className="flex flex-col gap-2 p-3 pb-4"
    >
      <CommandPalette
        input={internalInputValue}
        commands={commands}
        onPick={(name) => setInternalInputValue(`/${name} `)}
      />
      <ReferencePalette
        input={internalInputValue}
        known={referenceable}
        onPick={setInternalInputValue}
      />
      {threadId && !internalInputValue && (
        <DraftNotice
          key={threadId}
          threadId={threadId}
          onRestore={setInternalInputValue}
        />
      )}
      <SecretWarning text={internalInputValue} />
      <RateLimitNotice
        isRateLimited={isRateLimited}
        retryAfterSeconds={rateLimitRemainingSeconds}
      />
      {attachError && (
        <Alert variant="danger" isInline title={attachError} className="mb-1" />
      )}
      {uploading && (
        <p
          className="mb-1 flex items-center gap-1.5 text-xs text-muted-foreground"
          role="status"
        >
          <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
          {t('input.attaching')}
        </p>
      )}
      <div
        className={cn(
          "composer relative border shadow-card transition-all duration-200",
          // Pill while it holds one line and nothing else; a panel
          // once there is an attachment or the text wraps. The shape
          // is the affordance: a pill says "type here", a panel says
          // "this has contents".
          isExpanded ? "rounded-3xl" : "rounded-full",
          isLoading
            ? "border-muted bg-muted/30"
            : "border-border bg-card focus-within:border-primary/40 focus-within:shadow-elevated",
        )}
      >
        {attached.length > 0 && (
          <ul
            className="flex flex-wrap gap-2 list-none p-0 px-3 pt-3"
            aria-label={t('input.attachedFiles')}
          >
            {attached.map((file) => (
              <AttachmentChip key={file.path} file={file} />
            ))}
          </ul>
        )}

        <div className="flex items-end gap-1">
          <div className="flex items-center pb-1.5 pl-1.5">
          {threadId && (
            <AttachButton
              threadId={threadId}
              disabled={isLoading}
              onUploaded={onUploaded}
              onError={setAttachError}
            />
          )}
          </div>
        <textarea
          ref={ref}
          autoFocus
          value={internalInputValue}
          onChange={(e) => setInternalInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          disabled={isLoading}
          placeholder={
            isLoading ? t('input.waiting') : (placeholder || t('input.askAnything'))
          }
          aria-label={ariaLabel || t('input.typeMessage')}
          className={cn(
            "flex-1 resize-none border-0 bg-transparent py-3 text-sm leading-relaxed max-h-[200px] placeholder:opacity-60 focus:outline-none focus:ring-0 focus:border-transparent focus:shadow-none",
            isExpanded ? "px-4 min-h-[40px]" : "px-1 min-h-[24px]",
            isLoading && "cursor-not-allowed opacity-50",
          )}
          style={{ boxShadow: 'none' }}
          rows={1}
        />
          <div className="flex items-center gap-1.5 pb-1.5 pr-1.5">
          {dictation.offered && !isLoading && (
            <button
              type="button"
              onClick={() => (dictation.recording ? dictation.stop() : void dictation.start())}
              aria-pressed={dictation.recording}
              disabled={dictation.working}
              aria-label={
                dictation.recording
                  ? 'Stop dictating'
                  : dictation.working
                    ? 'Turning what you said into text'
                    : 'Dictate a message'
              }
              className={`flex h-9 w-9 items-center justify-center rounded-full transition-colors ${
                dictation.recording
                  ? 'bg-destructive/10 text-destructive'
                  : 'text-muted-foreground hover:bg-secondary/50 hover:text-foreground'
              }`}
            >
              {dictation.working ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : dictation.recording ? (
                <Square className="h-3.5 w-3.5 fill-current" />
              ) : (
                <Mic className="h-4 w-4" />
              )}
            </button>
          )}
          {isLoading ? (
            <StopButton
              stage={runStage}
              tool={toolInFlight}
              reversible={toolIsReversible}
              onStop={onCancel}
            />
          ) : (
            <button
              type="submit"
              disabled={isSubmitDisabled}
              aria-label={
                isRateLimited
                  ? `Wait ${rateLimitRemainingSeconds} seconds`
                  : "Send message"
              }
              className={`flex items-center justify-center rounded-full transition-all duration-200 ${
                isRateLimited ? "min-w-[88px] h-9 px-2" : "w-9 h-9"
              } ${
                isSubmitDisabled
                  ? "bg-muted text-muted-foreground cursor-not-allowed"
                  : "bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm hover:shadow-md"
              }`}
            >
              {isRateLimited ? (
                <span className="text-xs font-medium tabular-nums">
                  {t('input.waitSeconds', { seconds: rateLimitRemainingSeconds })}
                </span>
              ) : (
                <ArrowUp className="h-4 w-4" />
              )}
            </button>
          )}
          </div>
        </div>
      </div>
      {dictation.problem && (
        <p role="status" className="text-xs text-destructive text-center mt-1.5">
          {dictation.problem}
        </p>
      )}
      {/* Beside the disclaimer rather than inside the composer:
          it belongs to the conversation, not to the message being
          typed, and it is absent entirely unless the agent says
          the options would send different requests. */}
      <div className="mt-1.5 flex items-center justify-center gap-3">
        <ReasoningSelector
          threadId={threadId ?? ''}
          offered={reasoningProfiles}
          onChoose={() => undefined}
        />
        <p className="text-xs text-muted-foreground text-center">
          {t('input.aiDisclaimer')}
        </p>
      </div>
    </form>
    </>
  );
});
