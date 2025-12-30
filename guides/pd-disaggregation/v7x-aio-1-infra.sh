# Source the env vars
source v7x-aio-0-env.sh

# Set the project
gcloud config set project $PROJECT_ID

# Create GKE Cluster
gcloud container clusters create $CLUSTER \
--location=$LOCATION \
--gateway-api=standard \
--monitoring=SYSTEM,DCGM

# Create nodepool
gcloud container node-pools create $NODE_POOL \
--cluster=$CLUSTER --project=$PROJECT_ID --location=$LOCATION \
--node-locations=$ZONE --machine-type=$MACHINE_TYPE \
--num-nodes=2 --disk-size=800 --reservation-affinity=specific --reservation=$RESERVATION

# Config kubectl
gcloud container clusters get-credentials $CLUSTER --location=$LOCATION

# Create proxy only subnet needed by GKE gateway
gcloud compute networks subnets create proxy-only-subnet \
    --purpose=REGIONAL_MANAGED_PROXY \
    --role=ACTIVE \
    --region=$REGION \
    --network=$VPC_NETWORK_NAME \
    --range=$CIDR_RANGE

# Create firewall rule with source ranges described in GCP docs
NODE=$(kubectl get nodes -l cloud.google.com/gke-nodepool=$NODE_POOL -o jsonpath='{.items[0].metadata.name}')
TARGET_TAG=$(gcloud compute instances describe ${NODE} --zone=${ZONE} --project=${PROJECT_ID} --format="value(tags.items)")
gcloud compute firewall-rules create gke-gateway-firewall-${CLUSTER}-${NODE_POOL} --project=${PROJECT_ID} \
    --target-tags=$TARGET_TAG \
    --allow=all \
    --source-ranges=35.191.0.0/16,130.211.0.0/22