#!/bin/bash

source env.sh
source utils.sh

readonly IMAGE_DIR="custom_image"

if ! check_artifacts_repository_exists "${ARTIFACT_REGISTRY_REPO}" "${LOCATION}" "${PROJECT_ID}"; then
  gcloud artifacts repositories create "${RARTIFACT_REGISTRY_REPO}" \
    --repository-format=docker \
    --location="${LOCATION}" \
    --project="${PROJECT_ID}" \
    --description="Repository for custom vLLM TPU images used to benchmark KV transfer DCN performance by HostNet team"
fi

gcloud builds submit "${IMAGE_DIR}" --tag "${PD_POD_IMAGE}"
