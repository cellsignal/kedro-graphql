export SHELL:=/bin/bash
export SHELLOPTS:=$(if $(SHELLOPTS),$(SHELLOPTS):)pipefail:errexit

# https://stackoverflow.com/questions/4122831/disable-make-builtin-rules-and-variables-from-inside-the-make-file
MAKEFLAGS += --no-builtin-rules


BUILD_DATE            := $(shell date -u +'%Y-%m-%dT%H:%M:%SZ')
GIT_COMMIT            := $(shell git rev-parse HEAD)
GIT_REMOTE            := origin
GIT_BRANCH            := $(shell git rev-parse --symbolic-full-name --verify --quiet --abbrev-ref HEAD)
GIT_TAG               := $(shell git describe --exact-match --tags --abbrev=0  2> /dev/null || echo untagged)
GIT_TREE_STATE        := $(shell if [ -z "`git status --porcelain`" ]; then echo "clean" ; else echo "dirty"; fi)
RELEASE_TAG           := $(shell if [[ "$(GIT_TAG)" =~ ^v[0-9]+\.[0-9]+\.[0-9]+.*$$ ]]; then echo "true"; else echo "false"; fi)
SCRIPT_DIR            := $(shell cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
OVERLAYS_DIR          ?= manifests/overlays
OVERLAY               ?= dev
WORKING_DIR           := $(OVERLAYS_DIR)/$(OVERLAY)


.PHONY: dev
dev:
	docker-compose up -d

.PHONY: dev-cluster
dev-cluster:
	k3d cluster create --config ./k3d-cluster.yaml
	kubectl config use-context k3d-kedro-graphql
	kubectl apply -f https://github.com/argoproj/argo-workflows/releases/download/v3.4.7/namespace-install.yaml
	kubectl patch deployment argo-server --type='json' -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/readinessProbe/httpGet/scheme", "value": "HTTP"},{"op": "replace", "path": "/spec/template/spec/containers/0/args", "value": ["server", "--auth-mode=server", "--secure=false"]}]'
	kubectl patch service argo-server --type='json' -p='[{"op": "add", "path": "/spec/ports/0/nodePort", "value": 30080},{"op": "replace", "path": "/spec/type", "value": "NodePort"}]'


.PHONY: clean
clean:
	kubectl config use-context k3d-kedro-graphql
	k3d cluster delete --config ./k3d-cluster.yaml
