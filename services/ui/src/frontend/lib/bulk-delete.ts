export interface DeletionPlan {
  /** Whether the selection reaches past the rows on screen. */
  beyondThisPage: boolean;
  pickedOnPage: () => string[];
  targets: (allIds: string[]) => string[];
  listAll: () => Promise<string[] | null>;
}

/**
 * Which conversations a delete should actually take.
 *
 * A select-all is a rule, so it has to be applied against the real
 * list rather than the handful the sidebar happens to have loaded.
 */
export async function idsToDelete(plan: DeletionPlan): Promise<string[]> {
  if (!plan.beyondThisPage) {
    return plan.pickedOnPage();
  }

  const all = await plan.listAll();
  // Deleting nothing would read as the button being broken. What is on
  // screen is at least what the reader can see they asked for.
  if (all === null) {
    return plan.pickedOnPage();
  }

  return plan.targets(all);
}
