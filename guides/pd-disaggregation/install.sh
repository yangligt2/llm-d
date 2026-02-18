#!/bin/bash

# Install dependencies to cloudtop
sudo apt -y install yq git google-cloud-cli google-cloud-sdk-gke-gcloud-auth-plugin kubectl

# Install helm
curl -fsSL -o ~/Downloads/get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-4
chmod 700 ~/Downloads/get_helm.sh
~/Downloads/get_helm.sh
sudo chmod o+x /usr/local/bin/helm

# Install helm-diff plugin
helm plugin install https://github.com/databus23/helm-diff --verify=false

# Install helmfile
DOWNLOAD_URL=$(curl -s https://api.github.com/repos/helmfile/helmfile/releases/latest | jq -r '.assets[] | select(.name | contains("linux_amd64.tar.gz")) | .browser_download_url')
if [ -z "$DOWNLOAD_URL" ] || [ "$DOWNLOAD_URL" == "null" ]; then
  echo "Could not find the download URL for the latest helmfile Linux AMD64 tar.gz"
  exit 1
fi

# local version=$(echo $url | sed -n 's|.*/download/\(v[^/]*\)/.*|\1|p')
echo "Downloading from: $DOWNLOAD_URL"
OUTPUT_FILE=~/Downloads/$(basename $DOWNLOAD_URL)
wget -O $OUTPUT_FILE "$DOWNLOAD_URL"
EXTRACT_DIR="${OUTPUT_FILE%.tar.gz}"
mkdir -p $EXTRACT_DIR
tar -zxvf $OUTPUT_FILE -C $EXTRACT_DIR
sudo cp ${EXTRACT_DIR}/helmfile /usr/local/bin/
sudo chmod o+x /usr/local/bin/helmfile
