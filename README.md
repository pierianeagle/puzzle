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

# To inspect that image:
docker run -it --rm \
  # I'm using direnv to manage my environment variables. Here I'm converting .envrc to
  # .env (exports only) to add secrets to the image at runtime.
  --env-file <(sed -E 's/^export //; s/"//g' .envrc) \
  -e IBG_HOST=host.docker.internal \
  shittles/jfdi /bin/bash
```
