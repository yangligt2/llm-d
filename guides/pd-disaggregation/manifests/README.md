# Model Server and InferencePool Manifests

This directory contains Kustomize manifests for deploying the Model Server (`ms-pd`) and Helm values files for deploying the `InferencePool` via the Gateway API Inference Extension (GAIE).

These manifests serve as an alternative to the Helmfile-based deployment described in the main `guides/pd-disaggregation/README.md`, aligning with the pattern used in `guides/wide-ep-lws`.

## Prerequisites

Ensure you have created the namespace and set it as an environment variable:

```bash
export NAMESPACE=llm-d-pd # or your chosen namespace
kubectl create namespace ${NAMESPACE}
```

Ensure you have created the `llm-d-hf-token` secret as described in the main README.

## 1. Deploy Model Server (Kustomize)

Navigate to the `guides/pd-disaggregation` directory:

```bash
cd guides/pd-disaggregation
```

Select the appropriate overlay for your hardware and apply it using `kubectl apply -k`:

### GKE (Nvidia GPU)
```bash
kubectl apply -k ./manifests/modelserver/gke -n ${NAMESPACE}
```

### AMD GPU
```bash
kubectl apply -k ./manifests/modelserver/amd -n ${NAMESPACE}
```

### Cloud TPU
```bash
kubectl apply -k ./manifests/modelserver/tpu -n ${NAMESPACE}
```

### Intel HPU (Gaudi)
```bash
kubectl apply -k ./manifests/modelserver/hpu -n ${NAMESPACE}
```

### Intel XPU
```bash
kubectl apply -k ./manifests/modelserver/xpu -n ${NAMESPACE}
```

### SGLang (Nvidia GPU)
```bash
kubectl apply -k ./manifests/modelserver/sglang -n ${NAMESPACE}
```

### OpenShift (OCP)
```bash
kubectl apply -k ./manifests/modelserver/ocp -n ${NAMESPACE}
```

## 2. Deploy InferencePool (Helm)

After deploying the model server, deploy the `InferencePool` using the Helm chart. This requires specifying the values file and the appropriate provider.

### For vLLM (Default)

```bash
helm install llm-d-infpool \
  -n ${NAMESPACE} \
  -f ./manifests/inferencepool.values.yaml \
  --set "provider.name=gke" \
  oci://registry.k8s.io/gateway-api-inference-extension/charts/inferencepool \
  --version v1.4.0
```

### For SGLang

```bash
helm install llm-d-infpool \
  -n ${NAMESPACE} \
  -f ./manifests/inferencepool_sglang.values.yaml \
  --set "provider.name=gke" \
  oci://registry.k8s.io/gateway-api-inference-extension/charts/inferencepool \
  --version v1.4.0
```

> [!NOTE]
> Change `--set "provider.name=gke"` to match your gateway provider (e.g., `istio`, `none`, etc.) as described in the main README under "Gateway options".
