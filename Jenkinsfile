pipeline {
  agent any

  triggers {
    // GitHub webhook should point to: https://<jenkins-url>/github-webhook/
    githubPush()
  }

  options {
    disableConcurrentBuilds()
    timestamps()
  }

  environment {
    HELM_RELEASE = 'simple-web'
    HELM_NAMESPACE = 'default'
    HELM_CHART_PATH = '.'
    HELM_VALUES_FILE = 'values.yaml'

    // Jenkins file credential that contains kubeconfig for the target AKS cluster.
    KUBECONFIG_CREDENTIAL_ID = 'aks-kubeconfig'
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Detect Helm Chart Changes') {
      steps {
        script {
          String diffOutput = sh(
            returnStdout: true,
            script: '''#!/usr/bin/env bash
            set -euo pipefail
            if [ -n "${GIT_PREVIOUS_SUCCESSFUL_COMMIT:-}" ]; then
            git diff --name-only "$GIT_PREVIOUS_SUCCESSFUL_COMMIT" "$GIT_COMMIT"
            else
            git show --pretty="" --name-only "$GIT_COMMIT"
            fi
            '''
          ).trim()

          List<String> changedFiles = diffOutput ? diffOutput.split('\n') as List<String> : []
          List<String> helmRelevant = changedFiles.findAll { file ->
            file == 'Chart.yaml' ||
            file == 'values.yaml' ||
            file.startsWith('templates/') ||
            file.startsWith('charts/')
          }

          if (helmRelevant.isEmpty()) {
            env.SKIP_DEPLOY = 'true'
            currentBuild.description = 'No Helm chart changes detected'
            echo "No Helm chart changes in commit ${env.GIT_COMMIT}. Skipping deployment."
          } else {
            env.SKIP_DEPLOY = 'false'
            echo "Helm-related changes detected: ${helmRelevant.join(', ')}"
          }
        }
      }
    }

    stage('Validate Helm') {
      when {
        expression { env.SKIP_DEPLOY != 'true' }
      }
      steps {
        sh '''#!/usr/bin/env bash
        set -euo pipefail
        helm version
        kubectl version --client
        helm lint "$HELM_CHART_PATH"
        helm template "$HELM_RELEASE" "$HELM_CHART_PATH" -f "$HELM_VALUES_FILE" >/dev/null
        '''
      }
    }

    stage('Deploy To AKS') {
      when {
        expression { env.SKIP_DEPLOY != 'true' }
      }
      steps {
        withCredentials([file(credentialsId: env.KUBECONFIG_CREDENTIAL_ID, variable: 'KUBECONFIG')]) {
        sh '''#!/usr/bin/env bash
        set -euo pipefail
        kubectl get ns "$HELM_NAMESPACE" >/dev/null 2>&1 || kubectl create ns "$HELM_NAMESPACE"

        helm upgrade --install "$HELM_RELEASE" "$HELM_CHART_PATH" \
        --namespace "$HELM_NAMESPACE" \
        --create-namespace \
        -f "$HELM_VALUES_FILE" \
        --atomic \
        --wait \
        --timeout 5m

        helm status "$HELM_RELEASE" --namespace "$HELM_NAMESPACE"
        '''
        }
      }
    }
  }

  post {
    success {
      echo 'Helm deployment pipeline completed successfully.'
    }
    failure {
      echo 'Pipeline failed. Check stage logs for details.'
    }
  }
}
