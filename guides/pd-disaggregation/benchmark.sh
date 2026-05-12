#!/bin/bash

set -euo pipefail

# ==============================================================================
# Configuration & Setup
# ==============================================================================
source env.sh

# Config kubectl so kubectl context points to correct cluster and location.
gcloud container clusters get-credentials "${CLUSTER}" --location="${LOCATION}"

NAMESPACE="${NAMESPACE:-llm-d-pd}"
GATEWAY_NAME="${GATEWAY_NAME:-infra-pd-inference-gateway}"
BENCHMARK_DIR="benchmark"
OUTPUT_DIR="./benchmark-report"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color


ISL_OSL="${1:-1k1k}"  # Input Sequence Length / Output Sequence Length. Defines the number of input and output tokens for the benchmark (e.g., 1K/8K means 1,024 input tokens and 8,192 output tokens).

if [[ "${ISL_OSL}" != "1k1k" && "${ISL_OSL}" != "8k1k" ]]; then
  echo -e "${RED}${ISL_OSL} is invalid. Benchmark config should be either 1k1k or 8k1k.${NC}"
  exit
fi

echo -e "Starting benchmark in namespace: ${GREEN}${NAMESPACE}${NC}"

# Check for required files
if [ ! -d "${BENCHMARK_DIR}" ]; then
  echo -e "${RED}Error: Directory '${BENCHMARK_DIR}' not found. Are you in the correct directory?${NC}"
  exit 1
fi

mkdir -p "${OUTPUT_DIR}"

# ==============================================================================
# Step 1: Verify Gateway
# ==============================================================================
echo -e "\n--- Checking Gateway ---"
RAW_IP=$(kubectl get gateway "${GATEWAY_NAME}" -n "${NAMESPACE}" -o jsonpath='{.status.addresses[0].value}' 2>/dev/null)

if [ -z "${RAW_IP}" ]; then
  echo -e "${RED}Gateway IP not assigned yet. Cannot run benchmark.${NC}"
  exit 1
else
  echo -e "Gateway IP found: ${GREEN}${RAW_IP}${NC}"
  BASE_URL="http://${RAW_IP}:80"
  echo "Target URL: ${BASE_URL}"

  readonly local config_template="${BENCHMARK_DIR}/config_${ISL_OSL}.yaml"
  readonly local config_file="${OUTPUT_DIR}/config.yaml"
  # Update the config.yaml with the dynamic Gateway IP
  sed "s|base_url: .*|base_url: ${BASE_URL}|" "${config_template}" > "${config_file}"
  echo "Copied ${config_template} to ${config_file} and updated base_url to ${BASE_URL}"
fi

# ==============================================================================
# Step 2: Prepare Benchmark Configuration
# ==============================================================================
echo -e "\n--- Preparing Benchmark Configuration ---"

# Update ConfigMap
echo "Updating ConfigMap 'inference-perf-config'..."
kubectl delete configmap inference-perf-config -n "${NAMESPACE}" --ignore-not-found=true
kubectl create configmap inference-perf-config -n "${NAMESPACE}" --from-file="${OUTPUT_DIR}/config.yaml"

# ==============================================================================
# Step 3: Run Benchmark Job
# ==============================================================================
echo -e "\n--- Starting Benchmark Job ---"

# Clean up previous job
if kubectl get job inference-perf -n "${NAMESPACE}" > /dev/null 2>&1; then
  echo "Deleting previous benchmark job..."
  kubectl delete job inference-perf -n "${NAMESPACE}" --wait=true
fi

# Capture kv transfer log
DECODE_POD=$(kubectl get pods -n llm-d-pd --no-headers -o custom-columns=":metadata.name" | grep decode)
PREFILL_POD=$(kubectl get pods -n llm-d-pd --no-headers -o custom-columns=":metadata.name" | grep prefill)

kubectl logs "${DECODE_POD}" -n llm-d-pd --tail=0 -f | \
    tee \
      >(grep --line-buffered "kv transfer | done pull" > "${OUTPUT_DIR}/kv_transfer.log") \
      >(grep --line-buffered "\[metric\]" > "${OUTPUT_DIR}/decode_jnt_metrics.log") \
    > /dev/null &
DECODE_POD_LOG_CAPTURE_PID=$!

kubectl logs "${PREFILL_POD}" -n llm-d-pd --tail=0 -f | grep --line-buffered "\[metric\]" > "${OUTPUT_DIR}/prefill_jnt_metrics.log" &
PREFILL_POD_LOG_CAPTURE_PID=$!

echo "Deploying benchmark job..."
kubectl apply -f "${BENCHMARK_DIR}/manifests.yaml" -n "${NAMESPACE}"

# Launch sar on decode pod to capture rx rate
kubectl exec "${DECODE_POD}" -n "${NAMESPACE}" -- pkill -f sar || true
REMOTE_SAR_LOG="${NAMESPACE}/${DECODE_POD}:/tmp/sar.log"
readonly SAR_CMD="nohup sar -n DEV --iface=eth0,eth1 1 -o /tmp/sar.log > /dev/null 2>&1 &"
SAR_PID=$(kubectl exec "${DECODE_POD}" -n "${NAMESPACE}" -- bash -c "${SAR_CMD} echo \$!")

# Define a cleanup function
cleanup_logs() {
  echo "Cleaning up background log capture processes..."
  kubectl exec "${DECODE_POD}" -n "${NAMESPACE}" -- kill -9 "${SAR_PID}" || true
  kill "${DECODE_POD_LOG_CAPTURE_PID}" "${PREFILL_POD_LOG_CAPTURE_PID}" 2>/dev/null || true
}

# Set a trap to catch the EXIT signal
# EXIT triggers on successful completion, 'set -e' aborts, and manual 'exit' commands
trap cleanup_logs EXIT

# ==============================================================================
# Step 4: Wait for Execution
# ==============================================================================
echo -e "\n--- Waiting for Benchmark Execution ---"

echo "Waiting for pod to be ready..."
if kubectl wait --for=condition=Ready pod -l app=inference-perf -n "${NAMESPACE}" --timeout=1200s > /dev/null; then
  POD=$(kubectl get pods -l app=inference-perf -n "${NAMESPACE}" -o jsonpath='{.items[0].metadata.name}')
  echo -e "Benchmark Pod running: ${GREEN}${POD}${NC}"
else
  echo -e "${RED}Timeout waiting for benchmark pod to be ready.${NC}"
  exit 1
fi

echo "Waiting for benchmark completion (this may take a while)..."
until kubectl logs "${POD}" -n "${NAMESPACE}" 2>/dev/null | grep -q "Benchmark finished"; do
  # Check if pod failed
  PHASE=$(kubectl get pod "${POD}" -n "${NAMESPACE}" -o jsonpath='{.status.phase}')
  if [ "${PHASE}" == "Failed" ]; then
    echo -e "\n${RED}Benchmark Pod Failed.${NC}"
    exit 1
  fi
  echo -n "."
  sleep 5
done
echo ""

echo -e "Benchmark status: ${GREEN}FINISHED${NC}"

# Stop capturing logs
cleanup_logs

# ==============================================================================
# Step 5: Retrieve Results
# ==============================================================================
echo -e "\n--- Retrieving Results ---"

# Get the report directory path from logs
REPORT_DIR=$(kubectl logs "${POD}" -n "${NAMESPACE}" | grep "Report files will be stored at" | awk -F': ' '{print $NF}' | tr -d '\r')

if [ -z "${REPORT_DIR}" ]; then
  echo -e "${RED}Could not determine remote report directory from logs.${NC}"
  exit 1
fi

# Verify the directory actually exists in the pod
if ! kubectl exec "${POD}" -n "${NAMESPACE}" -- test -d "${REPORT_DIR}"; then
  echo -e "${RED}Failed: Report directory ${REPORT_DIR} does not exist in the pod.${NC}"
  exit 1
fi

REMOTE_REPORT_DIR="${NAMESPACE}/${POD}:${REPORT_DIR}"
echo "Copying report from ${REMOTE_REPORT_DIR} to ${OUTPUT_DIR}..."

if kubectl cp "${REMOTE_REPORT_DIR}" "${OUTPUT_DIR}"; then
  echo -e "${GREEN}Results successfully copied to ${OUTPUT_DIR}${NC}"
else
  echo -e "${RED}Failed to copy ${REMOTE_REPORT_DIR}.${NC}"
  exit 1
fi

echo "Copying report from ${REMOTE_SAR_LOG} to ${OUTPUT_DIR}/sar.log..."
if kubectl cp "${REMOTE_SAR_LOG}" "${OUTPUT_DIR}/sar.log"; then
  echo -e "${GREEN}Successfully copied to ${OUTPUT_DIR}${NC}"
else
  echo -e "${RED}Failed to copy ${REMOTE_SAR_LOG}.${NC}"
  exit 1
fi

sar -n DEV -f "${OUTPUT_DIR}/sar.log" --iface=eth0,eth1 > "${OUTPUT_DIR}/sar.csv"

echo -e "\n${GREEN}Benchmark completed successfully!${NC}"
