# my-task

## Helm chart

This repository includes a Helm chart for deploying `simple-web` from `acrinterview.azurecr.io`.

- Chart path: `/charts/simple-web`
- Image: `acrinterview.azurecr.io/simple-web:latest`

## Jenkins pipeline trigger

A `Jenkinsfile` is included to trigger builds from GitHub push events and run the main pipeline stage only for changes on the `main` branch.
