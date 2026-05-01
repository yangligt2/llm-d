# Prefill/Decode Disaggregation on Google TPU v7

This guide demonstrates how to deploy `Qwen/Qwen3.5-397B-A17B-FP8` using prefill-decode (P/D) disaggregation on Google TPU v7 clusters. 

For a comprehensive overview of P/D disaggregation architecture, best practices, and benchmarking, please refer to the **[Unified P/D Disaggregation Guide](./README.md)**.

## Prerequisites

Before starting, ensure your cluster and environment are properly configured:

1. **TPU Topology:** Your GKE cluster must have TPU v7 nodes provisioned with a `2x2x1` topology (4 chips per node) to accommodate the model requirements.
   > [!NOTE]
   > **TPUv7 Cores and Parallelism:** TPUv7 has 2 cores per chip. You need to consider this when setting parallelism. For example, in `guides/pd-disaggregation/modelserver/tpu/vllm/patch-decode.yaml`, with 4 chips per pod, the tensor parallel size (`--tensor-parallel-size`) is set to `8`. 
2. Complete the **[Prerequisites](./README.md#prerequisites)** section in the main guide to clone the repository and install the Gateway API Inference Extension CRDs.
3. Set your environment variables, overriding the model name for Qwen 3.5:

```bash
export GAIE_VERSION=v1.4.0
export GUIDE_NAME="pd-disaggregation"
export NAMESPACE="llm-d-pd-disaggregation"
export MODEL_NAME="Qwen/Qwen3.5-397B-A17B-FP8"
```

## Installation Instructions

### 1. Deploy the llm-d Router

Deploy the router in either Standalone or Gateway mode by following the exact instructions in the **[Deploy the llm-d Router](./README.md#1-deploy-the-llm-d-router)** section of the main guide.

### 2. Deploy the TPU Model Server

Once the router is deployed, apply the Kustomize overlays specifically configured for TPU v7 and vLLM. This configuration sets up heterogeneous KV caches (HMA) and configures the TPU workers.

```bash
kubectl apply -n ${NAMESPACE} -k guides/${GUIDE_NAME}/modelserver/tpu/vllm/
```

*(Note: If you have monitoring enabled, you can optionally apply the monitoring components as described in the [main guide](./README.md#3-enable-monitoring-optional)).*

## Verification

Follow the **[Verification steps in the main guide](./README.md#verification)** to retrieve the proxy IP address. 

When sending your test request, ensure you use the correct TPU model name:

```bash
# Send a completion request to the TPU deployment
curl -X POST http://${IP}/v1/completions \
    -H 'Content-Type: application/json' \
    -d '{
    "model": "Qwen/Qwen3.5-397B-A17B-FP8",
    "prompt": "How are you today?"
    }' | jq
```

## Benchmarking & Cleanup

To run synthetic load tests or clean up your cluster, return to the **[Benchmarking](./README.md#benchmarking)** and **[Cleanup](./README.md#cleanup)** sections of the unified guide.
