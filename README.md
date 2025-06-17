# jfdi
A nautilus-trader-based quantitative trading system.

```zsh
# To install a package:
uv sync --group jfdi

# To install every package:
uv sync --all-groups

# To build a package's docker image:
docker build \
  -t shittles/jfdi:latest \
  --build-arg PACKAGE=jfdi \
  -f docker/Dockerfile .

# To inspect an image:
docker run -it --rm \
  # I'm using direnv to manage my environment variables. Here I'm converting .envrc to
  # .env (exports only) to add secrets to the image at runtime.
  --env-file <(sed -E 's/^export //; s/"//g' .envrc) \
  -e IBG_HOST=host.docker.internal \
  shittles/jfdi /bin/bash

# To push an image to the cloud:
docker push shittles/jfdi:latest

# And for amd64 for kind:
docker buildx create --use --name multiarch-builder

docker buildx inspect --bootstrap

docker buildx build \
  --platform linux/amd64 \
  -t shittles/jfdi:latest \
  --build-arg PACKAGE=jfdi \
  -f docker/Dockerfile \
  --load .

# To avoid pulling an image from the cloud:
kind load docker-image shittles/jfdi:latest --name puzzle

# To use kind:
kind create cluster --config k8s/kind/cluster.yaml --name puzzle

kubectl config get-contexts

kubectl config use-context kind-puzzle

kubectl cluster-info

kubectl get nodes -o wide

# To label a node:
# kubectl label node puzzle-control-plane dedicated=trading

# To taint a node (make it pod-phobic):
kubectl taint nodes puzzle-control-plane dedicated=trading:NoSchedule

# To add namespaces to a kubernetes cluster:
kubectl apply -f k8s/manifests/namespaces.yaml

# To add secrets to a kubernetes cluster:
kubectl create secret generic ib $(sed -nE '/^export IB_/{
  s/^export //;
  s/"//g;
  p
}' .envrc | xargs -I{} echo --from-literal={}) \
  --namespace trading

# To inspect a secret:
kubectl get secrets --all-namespaces

kubectl get secret ib \
  -o jsonpath="{.data.IB_ACCOUNT_ID}" | base64 \
  --namespace trading \
  --decode

# To render helm chart templates to kubernetes manifests:
helm template jfdi k8s/helm/jfdi

# To do a dry run:
helm upgrade --install jfdi-paper k8s/helm/jfdi \
  -f k8s/helm/jfdi/values/paper.yaml \
  --namespace trading \
  --dry-run \
  --debug

# To install a chart:
helm upgrade --install jfdi-paper k8s/helm/jfdi \
  -f k8s/helm/jfdi/values/paper.yaml \
  --namespace trading

# To inspect a pod:
kubectl get pods --all-namespaces

kubectl describe pod jfdi-5f48ccf986-6cz4m

kubectl logs jfdi-5f48ccf986-6cz4m

kubectl exec -it jfdi-5f48ccf986-6cz4m -- sh

# To add a local persistent volume to a kubernetes cluster:
kubectl apply -f k8s/manifests/storage_classes.yaml
kubectl apply -f k8s/manifests/persistent_volumes.yaml

# To install MinIO operator:
# helm repo add minio-operator https://operator.min.io

helm install \
  -f k8s/helm/operator/custom_values.yaml \
  # --create-namespace \
  # operator minio-operator/operator \
  --namespace minio-operator \
  operator k8s/helm/operator

# In a change of heart, I'm going to sacrifice my Minecraft server to save on compute
# and deploy my application to the Mac Mini it was running on. I've got Cloudflare Zero
# Trust set up, so all I need to do is move cloudflared inside the cluster.

kubectl get all --namespace minio-operator

# To add secrets that're expected as config.env:
kubectl create secret generic tenant-env-configuration \
  --from-file=config.env=<(sed -n '/^export MINIO_/p' .envrc) \
  --namespace minio-tenant

# To inspect a secret that's created from file:
kubectl get secret tenant-env-configuration \
  -o jsonpath="{.data.config\.env}" | base64 \
  --namespace minio-tenant \
  --decode

# To patch the node label (if required):
# kubectl get nodes --show-labels

# kubectl label node puzzle-worker kubernetes.io/hostname=puzzle-worker

# To install MinIO tenant:
helm install \
  -f k8s/helm/tenant/custom_values.yaml \
  tenant k8s/helm/tenant \
  # --create-namespace \
  # tenant minio-operator/tenant \
  --namespace minio-tenant

# To inspect the tenant:
kubectl logs -n minio-operator deploy/minio-operator

kubectl exec -n minio-tenant tenant-pool-0-0 -- env | grep MINIO_ROOT

kubectl get pv

kubectl get pvc -n minio-tenant

# To check out the UI:
kubectl get svc -n minio-tenant

kubectl port-forward -n minio-tenant svc/tenant-console 9443:9443

# To clean up:
helm uninstall jfdi -n trading
helm uninstall tenant -n minio-tenant
helm uninstall operator -n minio-operator

# To delete a secret:
# kubectl delete secret -n trading ib
# kubectl delete secret -n minio-tenant tenant-env-configuration

kind delete cluster --name puzzle
```
