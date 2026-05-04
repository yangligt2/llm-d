#!/bin/bash
#
# Helper Functions

# Checks if version $1 is greater than or equal to version $2
version_ge() {
    # If the sorted version of both is the same as sorting them with -V,
    # and the first one comes last or they are equal, it's >=.
    [ "$(printf '%s\n%s' "$1" "$2" | sort -V | head -n1)" == "$2" ]
}

# Checks if a GKE cluster exists.
# Prints a message if the cluster is found.
# Globals: None
# Arguments:
#   1: cluster (string) - The name of the cluster.
#   2: location (string)    - The region or zone of the cluster.
#   3: project (string)  - The Google Cloud project ID.
# Outputs: Echoes "Cluster ... already exists." to stdout if found.
# Returns:
#   0 if the cluster exists.
#   1 if the cluster does not exist.
check_cluster_exists() {
  local cluster="$1"
  local location="$2"
  local project="$3"
  if gcloud container clusters describe "${cluster}" \
    --location="${location}" \
    --project="${project}" > /dev/null 2>&1; then
    echo "Cluster ${cluster} already exists at location ${location} for project ${project}."
    return 0
  else
    return 1
  fi
}


# Checks if a compute network exists.
# Prints a message if the network is found.
# Globals: None
# Arguments:
#   1: net (string) - The name of the network.
#   2: project (string)  - The Google Cloud project ID.
# Outputs: Echoes "Network ... already exists." to stdout if found.
# Returns:
#   0 if the network exists.
#   1 if the network does not exist.
check_net_exists() {
  local net="$1"
  local project="$2"
  if gcloud compute networks describe "${net}" \
    --project="${project}" > /dev/null 2>&1; then
    echo "Network ${net} for project ${project} already exists."
    return 0
  else
    return 1
  fi
}

# Checks if a compute subnet exists.
# Prints a message if the subnet is found.
# Globals: None
# Arguments:
#   1: subnet (string) - The name of the subnet.
#   2: region (string)     - The region of the subnet.
#   3: project (string)  - The Google Cloud project ID.
# Outputs: Echoes "Subnet ... already exists." to stdout if found.
# Returns:
#   0 if the subnet exists.
#   1 if the subnet does not exist.
check_subnet_exists() {
  local subnet="$1"
  local region="$2"
  local project="$3"
  if gcloud compute networks subnets describe "${subnet}" \
    --region="${region}" \
    --project="${project}" > /dev/null 2>&1; then
    echo "Subnet ${subnet} at region ${region} for project ${project} already exists."
    return 0
  else
    return 1
  fi
}

# Checks if a GKE node pool exists.
# Prints a message if the node pool is found.
# Globals: None
# Arguments:
#   1: node_pool (string) - The name of the node pool.
#   2: cluster (string)   - The name of the cluster.
#   3: location (string)       - The region or zone of the cluster.
#   4: project (string)     - The Google Cloud project ID.
# Outputs: Echoes "Node pool ... already exists." to stdout if found.
# Returns:
#   0 if the node pool exists.
#   1 if the node pool does not exist.
check_node_pool_exists() {
  local node_pool="$1"
  local cluster="$2"
  local location="$3"
  local project="$4"
  if gcloud container node-pools describe "${node_pool}" \
    --cluster="${cluster}" \
    --location="${location}" \
    --project="${project}" > /dev/null 2>&1; then
    echo "Node pool ${node_pool} at location ${location} for project ${project} already exists."
    return 0
  else
    return 1
  fi
}

# Checks if a firewall rule exists.
# Prints a message if the firewall rule is found.
# Globals: None
# Arguments:
#   1: fw_rule (string) - The name of the firewall rule.
#   2: project (string)  - The Google Cloud project ID.
# Outputs: Echoes "Firewall rule ... already exists." to stdout if found.
# Returns:
#   0 if the firewall rule exists.
#   1 if the firewall rule does not exist.
check_fw_rule_exists() {
  local fw_rule="$1"
  local project="$2"
  if gcloud compute firewall-rules describe "${fw_rule}" \
    --project="${project}" > /dev/null 2>&1; then
    echo "Firewall rule ${fw_rule} for project ${project} already exists."
    return 0
  else
    return 1
  fi
}
