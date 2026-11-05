# Deploying the agent

Two ways to install the same thing. Both read
`config/agent/deployment/values.yaml`, which is the source of truth —
a replica count or a memory limit is a config edit, not a code edit,
and `make render-deployment` turns it into both the kustomize patches
and the chart's values. `make render-deployment-check` fails if either
has drifted.

Pick kustomize if you already deploy this estate that way. Pick the
chart if your tooling expects one. They produce the same Deployment,
and a test fails when they stop agreeing.

## The chart

See what you would get, before you get it:

```sh
helm template agent deployment/chart
```

Install it:

```sh
helm install agent deployment/chart --namespace ai-agents --create-namespace
```

Upgrade in place:

```sh
helm upgrade agent deployment/chart --namespace ai-agents
```

### Secrets

The chart ships the secret's **keys** and no values — the pod reads
them by name, so they have to exist, but a chart carrying a working
password would put the same one in every cluster that installs it.
The defaults are references resolved at deploy time by whatever
injects secrets in your cluster.

To fill them yourself instead:

```sh
helm install agent deployment/chart \
  --set-string secrets.POSTGRES_PASSWORD="$POSTGRES_PASSWORD"
```

Keep real values in a file outside this repository and pass it with
`-f`, rather than editing `deployment/chart/values.yaml` — that file
is generated and will be overwritten.

### Storage

Two claims. `agent-documents-pvc` is mounted by every replica, so it
needs `ReadWriteMany`; on OpenShift that usually means a file-based
storage class rather than the default block one. If the cluster
default cannot do RWX the claim stays Pending, and the fix is
`storage.documents.storageClassName`.

`config-pvc` is shared with the UI by subPath and is `ReadWriteOnce`,
which pins both pods to one node. That is free on a single-node
cluster and a deliberate choice anywhere else.

### Scaling to zero

Off by default. Turning it on swaps the autoscaler for a scaler that
can reach zero:

```sh
helm upgrade agent deployment/chart \
  --set components.scaleToZero=true \
  --set scaleToZero.host=agent.apps.example.com
```

This needs two cluster-level prerequisites — the custom metrics
autoscaler and its HTTP add-on. Without the add-on it deadlocks: at
zero replicas nothing receives the request, so nothing enqueues a
run, so nothing ever wakes the workload.

Three consequences come with it. The first request after idle pays a
cold start of roughly a minute. Scheduled work is deferred rather
than lost — it catches up on wake. And a run in flight dies on
scale-in; it is re-executed, but the reader's stream is already cut,
so `scaleToZero.cooldownSeconds` should exceed your longest run.

With this on, the Deployment stops naming a replica count and no
`HorizontalPodAutoscaler` is installed. Both are deliberate: two
controllers owning one Deployment oscillate.

## Kustomize

```sh
kubectl apply -k deployment/overlays/openshift
```

Overlays live in `deployment/overlays/`, optional pieces in
`deployment/components/`. Which components are on is decided by the
`components:` block in `values.yaml`, not by editing the overlay.

## Changing a value

Edit `config/agent/deployment/values.yaml`, then:

```sh
make render-deployment
```

Never edit `deployment/overlays/*/generated.yaml` or
`deployment/chart/values.yaml` by hand. Both are rendered, and a
value changed only in one of them is a value the other install method
never learns about.
