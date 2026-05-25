pipeline {
  agent any

  parameters {
    string(name: 'LOCAL_KUBECONFIG_PATH', defaultValue: '/var/lib/jenkins/.kube/config', description: 'Kubeconfig path on Jenkins VM (set empty to use process default)')
  }

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
    HELM_NAMESPACE = 'amit'
    HELM_CHART_PATH = '.'
    HELM_VALUES_FILE = 'values.yaml'
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
                export KUBECONFIG="$LOCAL_KUBECONFIG_PATH"
                set -euo pipefail
                if [ -n "${GIT_PREVIOUS_SUCCESSFUL_COMMIT:-}" ] && git cat-file -e "${GIT_PREVIOUS_SUCCESSFUL_COMMIT}^{commit}" >/dev/null 2>&1; then
                git diff --name-only "$GIT_PREVIOUS_SUCCESSFUL_COMMIT" "$GIT_COMMIT"
                else
                # First run or shallow clone without previous commit available.
                git ls-files
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
            env.CHART_CHANGED = 'false'
            echo 'No Helm chart changes detected from SCM diff.'
          } else {
            env.CHART_CHANGED = 'true'
            echo "Helm-related changes detected: ${helmRelevant.join(', ')}"
          }
        }
      }
    }

    stage('Validate Helm') {
      when {
        expression { env.CHART_CHANGED == 'true' }
      }
      steps {
        sh '''#!/usr/bin/env bash
            set -euo pipefail
            export KUBECONFIG="$LOCAL_KUBECONFIG_PATH"
            helm version
            kubectl version --client
            helm lint "$HELM_CHART_PATH"
            helm template "$HELM_RELEASE" "$HELM_CHART_PATH" -f "$HELM_VALUES_FILE" >/dev/null
            '''
      }
    }

    stage('Deploy To AKS') {
      when {
        expression { env.CHART_CHANGED == 'true' }
      }
      steps {
        script {
          String deployScript = '''#!/usr/bin/env bash
            set -euo pipefail
            if [ -n "${LOCAL_KUBECONFIG_PATH:-}" ]; then
              export KUBECONFIG="$LOCAL_KUBECONFIG_PATH"
            elif [ -f "$HOME/.kube/config" ]; then
              export KUBECONFIG="$HOME/.kube/config"
            fi

            helm upgrade --install "$HELM_RELEASE" "$HELM_CHART_PATH" \
            --namespace "$HELM_NAMESPACE" \
            -f "$HELM_VALUES_FILE" \

            helm status "$HELM_RELEASE" --namespace "$HELM_NAMESPACE"
            '''
          sh deployScript
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