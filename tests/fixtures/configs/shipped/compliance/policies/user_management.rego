package agent.authz

# User-management mutation policy (D-3).
#
# Keyed on (actor role, target role, field class) — not on individual
# attributes. Per-attribute rules multiply with every field the admin
# surface learns to edit and stop being reviewable; three field classes
# stay reviewable.
#
#   profile     — display name, title, locale, timezone, contact
#   membership  — which groups/role the target is treated as holding
#   entitlement — what the target is allowed to spend and use
#
# Extends the same `agent.authz` package and the same `deny_reasons`
# contract as the message policies: the service derives "allowed" from
# `deny_reasons` being empty, so anything not permitted here must
# produce a reason. There is no second permission model — roles are the
# LDAP roles the rest of the agent already resolves.

import rego.v1

# Mirrors agent.src.ldap.prompt_config.ROLE_HIERARCHY. The policy
# keeps its own copy deliberately: a policy that has to call back into
# the harness to rank a role is a policy that cannot be reviewed on its
# own.
user_mutation_role_rank := {
	"owners": 4,
	"admins": 3,
	"builders": 2,
	"users": 1,
}

user_mutation_field_classes := {"profile", "membership", "entitlement"}

# ── Who may change what ───────────────────────────────────────────────

# Owners: every field class, every target.
user_mutation_permitted if {
	input.current_intent.actor_role == "owners"
	input.current_intent.field_class in user_mutation_field_classes
}

# Admins: every field class, but only downward. An admin cannot grant
# themselves or a peer a membership or entitlement they do not have.
user_mutation_permitted if {
	input.current_intent.actor_role == "admins"
	input.current_intent.field_class in user_mutation_field_classes
	user_mutation_role_rank[input.current_intent.target_role] < user_mutation_role_rank.admins
}

# Admins may still correct a peer's profile — a display name is not a
# privilege.
user_mutation_permitted if {
	input.current_intent.actor_role == "admins"
	input.current_intent.field_class == "profile"
	input.current_intent.target_role == "admins"
}

# Builders: profile only, and only for targets below them.
user_mutation_permitted if {
	input.current_intent.actor_role == "builders"
	input.current_intent.field_class == "profile"
	user_mutation_role_rank[input.current_intent.target_role] < user_mutation_role_rank.builders
}

# ── Denials ───────────────────────────────────────────────────────────

deny_reasons contains msg if {
	input.current_intent.action == "user_mutation"
	not user_mutation_permitted
	msg := sprintf(
		"role '%s' may not change '%s' fields on role '%s'",
		[
			input.current_intent.actor_role,
			input.current_intent.field_class,
			input.current_intent.target_role,
		],
	)
}

# Self-escalation, checked independently of rank: an owner editing their
# own entitlement is the one case the rank rules would wave through, and
# it is the case that removes the second pair of eyes. Profile is exempt
# — people are allowed to fix their own display name.
deny_reasons contains msg if {
	input.current_intent.action == "user_mutation"
	input.current_intent.actor == input.current_intent.target
	input.current_intent.field_class != "profile"
	msg := sprintf(
		"'%s' fields cannot be changed on your own account",
		[input.current_intent.field_class],
	)
}

# An unrecognised field class is a harness that has grown a fourth
# category without the policy hearing about it. Deny rather than fall
# through to whichever rule happens not to mention it.
deny_reasons contains msg if {
	input.current_intent.action == "user_mutation"
	not input.current_intent.field_class in user_mutation_field_classes
	msg := sprintf(
		"unknown field class '%s'",
		[input.current_intent.field_class],
	)
}
