// One feature, alone, at the same user count as the mixed run.
//
//     make load FEATURE=threads
//
// Running a feature on its own is how you tell "the system is
// slow under load" from "this endpoint is slow": the mixed run
// gives the first answer and this gives the second.

import { threads } from "../lib/journeys.js";
import { VUS, DURATION, RAMP, thresholds } from "../lib/config.js";

export const options = {
  scenarios: {
    threads_only: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: RAMP, target: VUS },
        { duration: DURATION, target: VUS },
        { duration: "30s", target: 0 },
      ],
      gracefulRampDown: "30s",
    },
  },
  thresholds,
};

export default function () {
  threads();
}
