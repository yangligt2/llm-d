#!/bin/bash

source env.sh

# Config kubectl so kubectl context points to correct cluster and location.
gcloud container clusters get-credentials ${CLUSTER} --location=${LOCATION}

helmfile destroy -e gke_tpu -n ${NAMESPACE} --deleteWait --allow-no-matching-release
kubectl delete -f gaie-pd-epp-health-check-policy.yaml -n ${NAMESPACE} --ignore-not-found --wait
kubectl delete -f httproute.gke.yaml -n ${NAMESPACE} --ignore-not-found --wait

kubectl delete -f https://github.com/kubernetes-sigs/gateway-api-inference-extension/raw/v1.2.0-rc.1/config/crd/bases/inference.networking.k8s.io_inferencepools.yaml --ignore-not-found --wait
kubectl delete -f https://github.com/kubernetes-sigs/gateway-api-inference-extension/raw/v1.0.0/config/crd/bases/inference.networking.x-k8s.io_inferenceobjectives.yaml --ignore-not-found --wait

# Delete node pools
gcloud container node-pools delete ${NODE_POOL} --cluster=${CLUSTER} --location=${LOCATION} --quiet
gcloud container node-pools delete ${BENCHMARK_NODE_POOL} --cluster=${CLUSTER} --location=${LOCATION} --quiet

# Delete cluster
gcloud container clusters delete ${CLUSTER} --project=${PROJECT_ID} --location=${LOCATION} --quiet

# Delete firewall rules
gcloud compute firewall-rules delete ${FW_RULE_NAME_1} --project=${PROJECT_ID} --quiet
gcloud compute firewall-rules delete ${FW_RULE_NAME_2} --project=${PROJECT_ID} --quiet

# Delete subnets
gcloud compute networks subnets delete ${SUBNET_NAME_1} --region=${LOCATION} --project=${PROJECT_ID} --quiet
gcloud compute networks subnets delete ${SUBNET_NAME_2} --region=${LOCATION} --project=${PROJECT_ID} --quiet

# Delete networks
gcloud compute networks delete ${NETWORK_NAME_1} --project=${PROJECT_ID} --quiet
gcloud compute networks delete ${NETWORK_NAME_2} --project=${PROJECT_ID} --quiet
