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
                set -euo pipefail
                if [ -n "${GIT_PREVIOUS_SUCCESSFUL_COMMIT:-}" ] && git cat-file -e "${GIT_PREVIOUS_SUCCESSFUL_COMMIT}^{commit}" >/dev/null 2>&1; then
                git diff --name-only "$GIT_PREVIOUS_SUCCESSFUL_COMMIT" "$GIT_COMMIT"
                else
                # First run or shallow clone without previous commit available.
                git ls-files
                fi
                kubectl version --client
                kubectl get all -n "$HELM_NAMESPACE"
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
            echo "No Helm chart changes detected from SCM diff."
          } else {
            env.CHART_CHANGED = 'true'
            echo "Helm-related changes detected: ${helmRelevant.join(', ')}"
          }
        }
      }
    }

//     stage('Determine Deploy Action') {
//       steps {
//         script {
//           String detectReleaseScript = '''#!/usr/bin/env bash
//             set -euo pipefail
//             if [ -n "${LOCAL_KUBECONFIG_PATH:-}" ]; then
//               export KUBECONFIG="$LOCAL_KUBECONFIG_PATH"
//             elif [ -f "$HOME/.kube/config" ]; then
//               export KUBECONFIG="$HOME/.kube/config"
//             fi

//             # Fail fast if cluster auth/connectivity is broken.
//             kubectl cluster-info >/dev/null

//             set +e
//             status_output=$(helm status "$HELM_RELEASE" --namespace "$HELM_NAMESPACE" 2>&1)
//             status_rc=$?
//             set -e

//             if [ "$status_rc" -eq 0 ]; then
//               echo "EXISTS"
//               exit 0
//             fi

//             if echo "$status_output" | grep -qiE 'release: not found|not found'; then
//               echo "NOT_FOUND"
//               exit 0
//             fi

//             echo "$status_output" >&2
//             exit 2
//             '''

//           String releaseState = sh(returnStdout: true, script: detectReleaseScript).trim()

//           if (releaseState == 'NOT_FOUND') {
//             env.DEPLOY_ACTION = 'install'
//             currentBuild.description = 'First-time install: Helm release not found'
//             echo "Release ${env.HELM_RELEASE} not found in namespace ${env.HELM_NAMESPACE}. Action: install."
//           } else if (releaseState == 'EXISTS' && env.CHART_CHANGED == 'true') {
//             env.DEPLOY_ACTION = 'upgrade'
//             echo "Release ${env.HELM_RELEASE} exists and chart changed. Action: upgrade."
//           } else if (releaseState == 'EXISTS') {
//             env.DEPLOY_ACTION = 'skip'
//             currentBuild.description = 'No Helm chart changes detected'
//             echo "Release ${env.HELM_RELEASE} already exists and no chart changes. Action: skip."
//           } else {
//             error("Unable to determine Helm release state. Expected EXISTS or NOT_FOUND, got: ${releaseState}")
//           }
//         }
//       }
//     }

//     stage('Validate Helm') {
//       when {
//         expression { env.DEPLOY_ACTION != 'skip' }
//       }
//       steps {
//         sh '''#!/usr/bin/env bash
//             set -euo pipefail
//             helm version
//             kubectl version --client
//             helm lint "$HELM_CHART_PATH"
//             helm template "$HELM_RELEASE" "$HELM_CHART_PATH" -f "$HELM_VALUES_FILE" >/dev/null
//             '''
//       }
//     }

//     stage('Install To AKS') {
//       when {
//         expression { env.DEPLOY_ACTION == 'install' }
//       }
//       steps {
//         script {
//           String installScript = '''#!/usr/bin/env bash
//             set -euo pipefail
//             if [ -n "${LOCAL_KUBECONFIG_PATH:-}" ]; then
//               export KUBECONFIG="$LOCAL_KUBECONFIG_PATH"
//             elif [ -f "$HOME/.kube/config" ]; then
//               export KUBECONFIG="$HOME/.kube/config"
//             fi

//             helm install "$HELM_RELEASE" "$HELM_CHART_PATH" \
//             --namespace "$HELM_NAMESPACE" \
//             -f "$HELM_VALUES_FILE" \
//             --atomic \
//             --wait \
//             --timeout 5m

//             helm status "$HELM_RELEASE" --namespace "$HELM_NAMESPACE"
//             '''
//           sh installScript
//         }
//       }
//     }

//     stage('Upgrade On AKS') {
//       when {
//         expression { env.DEPLOY_ACTION == 'upgrade' }
//       }
//       steps {
//         script {
//           String upgradeScript = '''#!/usr/bin/env bash
//         set -euo pipefail
//         if [ -n "${LOCAL_KUBECONFIG_PATH:-}" ]; then
//           export KUBECONFIG="$LOCAL_KUBECONFIG_PATH"
//         elif [ -f "$HOME/.kube/config" ]; then
//           export KUBECONFIG="$HOME/.kube/config"
//         fi

//         helm upgrade "$HELM_RELEASE" "$HELM_CHART_PATH" \
//         --namespace "$HELM_NAMESPACE" \
//         -f "$HELM_VALUES_FILE" \
//         --atomic \
//         --wait \
//         --timeout 5m

//         helm status "$HELM_RELEASE" --namespace "$HELM_NAMESPACE"
//         '''
//           sh upgradeScript
//         }
//       }
//     }
//   }

//   post {
//     success {
//       echo 'Helm deployment pipeline completed successfully.'
//     }
//     failure {
//       echo 'Pipeline failed. Check stage logs for details.'
//     }
//   }
// }}