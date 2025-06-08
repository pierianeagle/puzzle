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
}' .envrc | xargs -I{} echo --from-literal={})

kubectl get secrets

# To inspect a secret:
kubectl get secret ib -o jsonpath="{.data.IB_ACCOUNT_ID}" | base64 --decode

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
kubectl get pods

kubectl describe pod jfdi-5f48ccf986-6cz4m

kubectl logs jfdi-5f48ccf986-6cz4m

kubectl exec -it jfdi-5f48ccf986-6cz4m -- sh

helm uninstall jfdi

kind delete cluster --name puzzle
```
