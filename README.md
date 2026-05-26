# simple-web Helm chart

This repository contains a Helm chart for deploying the `simple-web` application to Kubernetes.

## Contents

- `Chart.yaml`: chart metadata
- `values.yaml`: default configuration values
- `templates/`: Kubernetes manifests rendered by Helm
- `Jenkinsfile`: CI pipeline for validating, deploying, and destroying the release

## Prerequisites

- Helm 3
- Access to a Kubernetes cluster
- `kubectl` configured for the target cluster

## Install

```bash
helm dependency update .
helm lint .
helm install simple-web . --namespace amit --create-namespace -f values.yaml
```

## Upgrade

```bash
helm upgrade --install simple-web . --namespace amit -f values.yaml
```

## Uninstall

```bash
helm uninstall simple-web --namespace amit
```

## Notes

- The Python script under `book_fetcher/` is a separate utility and is not part of this Helm chart project.
- Ingress is enabled by default and uses the `/amit` path from `values.yaml`.