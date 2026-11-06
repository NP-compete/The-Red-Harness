{{/*
The labels every object carries.

`app` and `component` are the selector and cannot change on a live
Deployment — selectors are immutable — so the recommended Kubernetes
labels go on the pod template beside them, which is where collectors
look. An agent left at the default arrives in the metrics backend as
"agent", indistinguishable from every other one; the version label is
what lets a backend split a metric by release.
*/}}
{{- define "agent.selectorLabels" -}}
app: {{ .Values.app.name }}
component: {{ .Values.app.component }}
{{- end }}

{{- define "agent.labels" -}}
{{ include "agent.selectorLabels" . }}
app.kubernetes.io/name: {{ .Values.app.serviceName }}
app.kubernetes.io/component: {{ .Values.app.component }}
app.kubernetes.io/version: {{ .Values.image.tag | quote }}
app.kubernetes.io/part-of: {{ .Values.app.partOf }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "agent.image" -}}
{{ .Values.image.registry }}/{{ .Values.app.namespace }}/{{ .Values.image.name }}:{{ .Values.image.tag }}
{{- end }}

{{/*
What restricted SCC will accept.

No `runAsUser`: OpenShift assigns a uid per namespace, and naming one
here is what makes a chart that works locally and is refused by the
cluster it was written for.
*/}}
{{- define "agent.containerSecurityContext" -}}
runAsNonRoot: true
allowPrivilegeEscalation: false
capabilities:
  drop:
    - ALL
seccompProfile:
  type: RuntimeDefault
{{- end }}
