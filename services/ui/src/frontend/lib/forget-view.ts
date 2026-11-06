export interface ForgetPlan {
  forgetting: string[];
  untouched: string[];
  cannotUnsay: string[];
  affectsOthers: string[];
  foundNothing: boolean;
  needsConfirmation: boolean;
}

export interface PresentedForget {
  headline: string;
  items: string[];
  caveat: string;
  warning: string;
  actions: string[];
}

export function presentForget(plan: ForgetPlan): PresentedForget {
  const count = plan.forgetting.length;

  let warning = '';
  if (plan.affectsOthers.length > 0) {
    warning = `${plan.affectsOthers.length} of these is shared — it goes for everyone`;
  } else if (plan.untouched.length > 0) {
    warning = `${plan.untouched.length} of these belongs to someone else and stays`;
  }

  return {
    headline: plan.foundNothing
      ? 'Nothing matching that is remembered'
      : `Forgetting ${count} thing${count === 1 ? '' : 's'}`,
    items: plan.forgetting,
    // Forgetting is forward-looking, and saying so avoids a false promise.
    caveat:
      plan.cannotUnsay.length > 0
        ? 'This stops future use — it cannot change messages already sent'
        : '',
    warning,
    actions: plan.foundNothing
      ? []
      : [plan.needsConfirmation ? 'Forget for everyone' : 'Forget', 'Cancel'],
  };
}
