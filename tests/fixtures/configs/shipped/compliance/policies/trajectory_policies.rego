package agent.authz

import rego.v1

# Local trajectory limits for development.
# Git trajectory policy defines max_trajectory_length := 20; this file sets a
# different local cap via local_max_trajectory_length to avoid OPA complete-rule
# conflict when both policy sources are loaded.
#
# 20 was too low to be a development default. It terminates any
# conversation past the twentieth turn with "This thread has been
# terminated due to policy violation", which is a sentence about
# the user having done something wrong when all that happened is
# that the conversation got long. It also makes the agent unable
# to run AppWorld, whose standard prompt is 23 turns before the
# task even starts.
#
# This is a resource bound, not a safety one — the safety rules
# live in message_policies.rego and agent_authz.rego and are
# unchanged. Set where a long task can finish and a runaway loop
# still stops.
local_max_trajectory_length := 200

deny_reasons contains msg if {
	input.current_intent.action == "trajectory_validation"
	count(input.trajectory) > local_max_trajectory_length
	msg := sprintf(
		"Local trajectory length (%d) exceeds limit (%d)",
		[count(input.trajectory), local_max_trajectory_length],
	)
}
