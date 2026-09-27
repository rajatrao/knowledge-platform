#!/usr/bin/env bash
# Local kind cluster for the knowledge Kubernetes sandbox.
#
# Docker is the prerequisite. kind and kubectl must be on PATH:
#   brew install kind kubectl
#
# Create the cluster, install agent-sandbox, and export its kubeconfig:
#   ./scripts/kind-up.sh
#
# Cluster name defaults to "knowledge" (override with KIND_CLUSTER).
# Kubeconfig is written to $HOME/.kube/kind-${KIND_CLUSTER}.yaml.
# With KUBECONFIG unset, the API uses that file when it exists and still
# returns 503 when it does not. There is no local subprocess fallback.
#
# Agent-sandbox v1.0.4 matches the k8s-agent-sandbox client installed with
# langchain-k8s==0.6.0 (CRDs extensions.agents.x-k8s.io/v1beta1). Override with
# AGENT_SANDBOX_VERSION.
#
# Tear the cluster down and drop the kubeconfig the API looks for:
#   kind delete cluster --name knowledge
#   rm -f "$HOME/.kube/kind-knowledge.yaml"

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KIND_CLUSTER="${KIND_CLUSTER:-knowledge}"
AGENT_SANDBOX_VERSION="${AGENT_SANDBOX_VERSION:-v1.0.4}"
BOOTSTRAP_NS="${BOOTSTRAP_NS:-knowledge}"
KUBECONFIG_PATH="${KUBECONFIG_PATH:-${HOME}/.kube/kind-${KIND_CLUSTER}.yaml}"
RELEASE_URL="https://github.com/kubernetes-sigs/agent-sandbox/releases/download/${AGENT_SANDBOX_VERSION}"
ROUTER_URL="https://raw.githubusercontent.com/kubernetes-sigs/agent-sandbox/${AGENT_SANDBOX_VERSION}/sandbox-router/deploy"

info() { printf '[kind] %s\n' "$*"; }

for cmd in docker kind kubectl; do
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    printf '[kind] %s is required\n' "${cmd}" >&2
    exit 1
  fi
done

if ! docker info >/dev/null 2>&1; then
  printf '[kind] Docker is not running\n' >&2
  exit 1
fi

export KUBECONFIG="${KUBECONFIG_PATH}"
mkdir -p "$(dirname "${KUBECONFIG_PATH}")"

if kind get clusters 2>/dev/null | grep -qx "${KIND_CLUSTER}"; then
  info "Reusing kind cluster ${KIND_CLUSTER}"
else
  info "Creating kind cluster ${KIND_CLUSTER}"
  kind create cluster \
    --name "${KIND_CLUSTER}" \
    --config "${ROOT}/deploy/kind/cluster.yaml" \
    --wait 180s
fi

kind export kubeconfig --name "${KIND_CLUSTER}" --kubeconfig "${KUBECONFIG_PATH}"
kubectl cluster-info >/dev/null

install_gvisor() {
  local node="${KIND_CLUSTER}-control-plane"
  info "Installing gVisor runsc on ${node}"
  docker exec -i "${node}" bash -s <<'EOS'
set -euo pipefail
if ! command -v runsc >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y --no-install-recommends curl ca-certificates zstd
  arch="$(uname -m)"
  work="$(mktemp -d)"
  trap 'rm -rf "${work}"' EXIT
  cd "${work}"
  base="https://storage.googleapis.com/gvisor/releases/release/latest/${arch}"
  curl -fsSL -O "${base}/gvisor.tar.zstd"
  curl -fsSL -O "${base}/gvisor.tar.zstd.sha512"
  sha512sum -c gvisor.tar.zstd.sha512
  tar --zstd -xf gvisor.tar.zstd -C /usr/local/bin
  chmod 755 /usr/local/bin/runsc /usr/local/bin/containerd-shim-runsc-v1
fi
cat > /etc/containerd/runsc.toml <<'EOF'
[runsc_config]
  platform = "systrap"
  systemd-cgroup = "true"
EOF
if ! grep -q 'ConfigPath = "/etc/containerd/runsc.toml"' /etc/containerd/config.toml; then
  cat >> /etc/containerd/config.toml <<'EOF'

[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runsc.options]
  ConfigPath = "/etc/containerd/runsc.toml"
  SystemdCgroup = true
EOF
fi
systemctl restart containerd
EOS
  local attempt
  for attempt in $(seq 1 30); do
    if kubectl get nodes >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
  kubectl wait --for=condition=Ready nodes --all --timeout=180s
}

install_gvisor
kubectl apply -f "${ROOT}/deploy/kind/runtimeclass.yaml"

info "Installing agent-sandbox ${AGENT_SANDBOX_VERSION}"
kubectl apply -f "${RELEASE_URL}/sandbox-with-extensions.yaml"
kubectl rollout status deployment/agent-sandbox-controller \
  -n agent-sandbox-system --timeout=180s

info "Installing sandbox-router"
for manifest in serviceaccount.yaml rbac.yaml deployment.yaml service.yaml pdb.yaml; do
  kubectl apply -f "${ROUTER_URL}/${manifest}"
done
# The v1.0.4 deployment manifest points at :latest, which is not published.
kubectl set image deployment/sandbox-router \
  "sandbox-router=registry.k8s.io/agent-sandbox/sandbox-router-go:${AGENT_SANDBOX_VERSION}" \
  -n agent-sandbox-system
kubectl rollout status deployment/sandbox-router \
  -n agent-sandbox-system --timeout=180s

SANDBOX_IMAGE="$(awk '/^[[:space:]]*image:/{print $2; exit}' "${ROOT}/deploy/sandbox/sandbox-template.yaml")"
if [[ -z "${SANDBOX_IMAGE}" ]]; then
  printf '[kind] sandbox template has no image\n' >&2
  exit 1
fi
info "Loading ${SANDBOX_IMAGE} into ${KIND_CLUSTER}"
# kind load uses ctr --all-platforms, which fails on the Python image index.
node_arch="$(kubectl get nodes -o jsonpath='{.items[0].status.nodeInfo.architecture}')"
docker pull --platform "linux/${node_arch}" "${SANDBOX_IMAGE}"
docker save "${SANDBOX_IMAGE}" | docker exec -i "${KIND_CLUSTER}-control-plane" \
  ctr --namespace=k8s.io images import -

info "Applying SandboxTemplate, warm pool, and RBAC"
kubectl apply -f "${ROOT}/deploy/kind/rbac.yaml"
kubectl create namespace "${BOOTSTRAP_NS}" --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n "${BOOTSTRAP_NS}" -f "${ROOT}/deploy/sandbox/sandbox-template.yaml"
sed "s/namespace: NAMESPACE/namespace: ${BOOTSTRAP_NS}/" \
  "${ROOT}/deploy/sandbox/sandbox-warm-pool.yaml" | kubectl apply -f -

kubectl get crd sandboxtemplates.extensions.agents.x-k8s.io >/dev/null
kubectl get crd sandboxwarmpools.extensions.agents.x-k8s.io >/dev/null
kubectl get crd sandboxclaims.extensions.agents.x-k8s.io >/dev/null
kubectl get sandboxwarmpool warm -n "${BOOTSTRAP_NS}" >/dev/null
kubectl get runtimeclass gvisor >/dev/null

info "Cluster ${KIND_CLUSTER} is ready"
info "export KUBECONFIG=${KUBECONFIG_PATH}"
