/**
 * Agent payload types, from the agent (E10-T14).
 *
 * The one place this UI names a shape the agent owns. Everything
 * here is an alias into `generated/agent-api.d.ts`, which `npm run
 * contract` writes from the agent's OpenAPI baseline — so a payload
 * that changes shape becomes a TypeScript error here rather than a
 * runtime surprise in a component, and `npm run contract:check`
 * fails naming the endpoint that moved.
 *
 * Add an alias when the agent declares a response model for a route.
 * Do *not* hand-write a shape in this file: a hand-written type that
 * claims to be the contract is worse than one admitting it is a
 * guess, because nothing will ever contradict it.
 *
 * Types describing how the UI holds data — view models, props,
 * anything with a `Date` or a callback — belong elsewhere in this
 * directory. They are not the contract.
 */
import type { components } from './generated/agent-api';

type Schema = components['schemas'];

export type Project = Schema['Project'];
export type ProjectCreate = Schema['ProjectCreate'];
export type ProjectListResponse = Schema['ProjectListResponse'];

export type EditingState = Schema['EditingStateOut'];
export type ConfigTree = Schema['ConfigTreeOut'];
export type ConfigTreeFile = Schema['ConfigTreeFileOut'];
export type ConfigFileText = Schema['ConfigFileOut'];
export type SettingsView = Schema['SettingsViewOut'];
export type SettingsField = Schema['SettingsFieldOut'];
export type DeclaredChecks = Schema['DeclaredChecksOut'];
