#!/bin/bash
# Create GKE resources including networks, subnets, node pools, firewall rules
# and cluster.

set -e

# Source the env vars
source env.sh
source utils.sh

# Set the project
gcloud config set project "${PROJECT_ID}"

# Create networks if needed
if ! check_net_exists "${NETWORK_NAME_1}" "${PROJECT_ID}"; then
  gcloud compute networks create "${NETWORK_NAME_1}" \
    --project="${PROJECT_ID}" \
    --subnet-mode=auto \
    --mtu=8896 \
    --bgp-routing-mode=regional
fi

if ! check_net_exists "${NETWORK_NAME_2}" "${PROJECT_ID}"; then
  gcloud compute networks create "${NETWORK_NAME_2}" \
    --project="${PROJECT_ID}" \
    --subnet-mode=custom \
    --mtu=8896 \
    --bgp-routing-mode=regional
fi

# Create proxy only subnet needed by GKE gateway
if ! check_subnet_exists "${SUBNET_NAME_1}" "${LOCATION}" "${PROJECT_ID}"; then
  gcloud compute networks subnets create "${SUBNET_NAME_1}" \
    --purpose=REGIONAL_MANAGED_PROXY \
    --role=ACTIVE \
    --project="${PROJECT_ID}" \
    --region="${LOCATION}" \
    --network="${NETWORK_NAME_1}" \
    --range="${SUBNET_CIDR_RANGE_1}"
fi

# Create 2nd subnet needed by GKE multi-networking
if ! check_subnet_exists "${SUBNET_NAME_2}" "${LOCATION}" "${PROJECT_ID}"; then
  gcloud compute networks subnets create "${SUBNET_NAME_2}" \
    --project="${PROJECT_ID}" \
    --region="${LOCATION}" \
    --network="${NETWORK_NAME_2}" \
    --range="${SUBNET_CIDR_RANGE_2}"
fi

# Command to check available gke versions on each channel in a region:
# $ gcloud container get-server-config --region us-central1 --format="yaml(channels)"
MIN_VERSION="1.34.1-gke.1829001"  # min gke version required by tpuv7x
# Get default gke version on RAPID channel
CURRENT_VERSION=$(gcloud container get-server-config --region "${LOCATION}" \
    --flatten="channels" \
    --filter="channels.channel=RAPID" \
    --format='value(channels.defaultVersion)')

if version_ge "${CURRENT_VERSION}" "${MIN_VERSION}"; then
  echo "Version ${CURRENT_VERSION} meets the minimum requirement of ${MIN_VERSION}."
else
  echo "Error: Version ${CURRENT_VERSION} is too old."
  exit 1
fi

# Create a GKE cluster and pin to a specific GKE version for reproducibility.
if ! check_cluster_exists "${CLUSTER}" "${LOCATION}" "${PROJECT_ID}"; then
  gcloud container clusters create "${CLUSTER}" \
    --project="${PROJECT_ID}" \
    --location="${LOCATION}" \
    --gateway-api=standard \
    --monitoring=SYSTEM,DCGM \
    --enable-ip-alias \
    --enable-dataplane-v2 \
    --enable-multi-networking \
    --network="${NETWORK_NAME_1}" \
    --subnetwork="${NETWORK_NAME_1}" \
    --release-channel "rapid" \
    --cluster-version="1.35.0-gke.3047000"

    # Other useful flags (not needed in this setup)
    # --enable-dataplane-v2-metrics  \
    # --enable-dataplane-v2-flow-observability \
    # --machine-type=n2-standard-8 \
    # --scopes cloud-platform \
    # --enable-ip-access \
fi

# Create nodepools
if ! check_node_pool_exists "${NODE_POOL}" "${CLUSTER}" "${LOCATION}" "${PROJECT_ID}"; then
  gcloud container node-pools create "${NODE_POOL}" \
    --project="${PROJECT_ID}" \
    --cluster="${CLUSTER}" \
    --location="${LOCATION}" \
    --node-locations="${ZONE}" \
    --machine-type="${MACHINE_TYPE}" \
    --num-nodes=2 \
    --disk-size=800 \
    --reservation-affinity=specific \
    --reservation="${RESERVATION}" \
    --additional-node-network "network=${NETWORK_NAME_2},subnetwork=${SUBNET_NAME_2}"
    # --enable-gvnic # is implicitly specified for tpu machine type
fi

if ! check_node_pool_exists "${BENCHMARK_NODE_POOL}" "${CLUSTER}" "${LOCATION}" "${PROJECT_ID}"; then
  gcloud container node-pools create "${BENCHMARK_NODE_POOL}" \
    --project="${PROJECT_ID}" \
    --cluster="${CLUSTER}" \
    --location="${LOCATION}" \
    --node-locations="${ZONE}" \
    --machine-type=e2-standard-4 \
    --num-nodes=1 \
    --disk-size=100
fi

# Config kubectl so kubectl context points to the correct cluster and location.
gcloud container clusters get-credentials "${CLUSTER}" --location="${LOCATION}"

# Create firewall rule with source ranges described in
# https://docs.cloud.google.com/kubernetes-engine/docs/concepts/firewall-rules#gateway-fws
NODE=$(kubectl get nodes -l cloud.google.com/gke-nodepool="${NODE_POOL}" -o jsonpath='{.items[0].metadata.name}')
TARGET_TAG=$(gcloud compute instances describe "${NODE}" --zone="${ZONE}" --project="${PROJECT_ID}" --format="value(tags.items)")
if ! check_fw_rule_exists "${FW_RULE_NAME_1}" "${PROJECT_ID}"; then
  gcloud compute firewall-rules create "${FW_RULE_NAME_1}" \
    --project="${PROJECT_ID}" \
    --target-tags="${TARGET_TAG}" \
    --network="${NETWORK_NAME_1}" \
    --allow=all \
    --source-ranges=35.191.0.0/16,130.211.0.0/22 # Google health check ip range
fi

if ! check_fw_rule_exists "${FW_RULE_NAME_2}" "${PROJECT_ID}"; then
  gcloud compute firewall-rules create "${FW_RULE_NAME_2}" \
    --project="${PROJECT_ID}" \
    --target-tags="${TARGET_TAG}" \
    --network="${NETWORK_NAME_2}" \
    --allow=tcp,udp,icmp
fi
