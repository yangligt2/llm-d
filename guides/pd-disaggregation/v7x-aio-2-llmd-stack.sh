# Source the env vars
source v7x-aio-0-env.sh

# Install the Inference Extension CRDs.
# Although GKE already installed it: https://docs.cloud.google.com/kubernetes-engine/docs/how-to/deploy-gke-inference-gateway#compatibility, EPP will crash if not explicitly install it.
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api-inference-extension/raw/v1.0.0/config/crd/bases/inference.networking.x-k8s.io_inferenceobjectives.yaml

# create namespace
kubectl create namespace ${NAMESPACE}

# create HF token secret
kubectl create secret generic llm-d-hf-token \
  --namespace "${NAMESPACE}" \
  --from-literal="HF_TOKEN=${HF_TOKEN}"

# install the p/d stack, make sure you are unde dir guides/pd-disaggregation
helmfile apply -e gke_tpu -n ${NAMESPACE}

# install HTTP route
kubectl apply -f httproute.gke.yaml -n ${NAMESPACE}
