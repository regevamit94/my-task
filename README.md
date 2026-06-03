# simple-web Helm chart

This repository contains a Helm chart for deploying the `simple-web` application to Kubernetes.

## Contents

- `Chart.yaml`: chart metadata
- `values.yaml`: default configuration values
- `templates/`: Kubernetes manifests rendered by Helm
- `Jenkinsfile`: CI pipeline for validating, deploying, and destroying the release
- `azure-pipelines.yml`: Azure DevOps pipeline for validating, deploying, and destroying the release from a VM Scale Set agent pool

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

## Azure DevOps pipeline

This repository now includes `/tmp/workspace/regevamit94/my-task/azure-pipelines.yml` for Azure DevOps.

### Expected Azure DevOps setup

- Create a self-hosted Azure DevOps agent pool backed by an Azure VM Scale Set.
- Install and validate `az`, `helm`, `kubectl`, and Git on the VM image used by that scale set.
- Create an Azure Resource Manager service connection with access to the target AKS cluster.
- Define the following pipeline variables in Azure DevOps:
  - `AKS_RESOURCE_GROUP`
  - `AKS_CLUSTER_NAME`
- Optionally configure approvals on the Azure DevOps environment used by the deployment job.

### Pipeline behavior

- Runs on pushes and pull requests.
- Uses a VM Scale Set agent pool, not AKS-hosted runner pods.
- Verifies required CLI tools on the agent before deployment stages run.
- For `DEPLOY`, the pipeline:
  - fetches AKS credentials with `az aks get-credentials`
  - runs `helm lint`
  - renders the chart with `helm template`
  - performs a Helm dry-run upgrade
  - deploys the release
  - optionally runs `helm test`
- For `DESTROY`, the pipeline removes the Helm release if it exists.

### Queue-time parameters

- `action`: `DEPLOY` or `DESTROY`
- `vmssPool`: Azure DevOps VM Scale Set agent pool name
- `azureServiceConnection`: Azure service connection name
- `environmentName`: Azure DevOps environment name used for deployment jobs
- `runHelmTests`: whether to run `helm test` after deployment