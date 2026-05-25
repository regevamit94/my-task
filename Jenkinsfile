pipeline {
  agent any

  triggers {
    githubPush()
  }

  options {
    disableConcurrentBuilds()
  }

  stages {
    stage('Run for main branch changes') {
      when {
        branch 'main'
      }
      steps {
        echo 'Detected changes on main branch. Running Jenkins pipeline.'
      }
    }

    stage('Skip non-main branches') {
      when {
        not {
          branch 'main'
        }
      }
      steps {
        echo 'Skipping run because this pipeline is configured for main branch changes only.'
      }
    }
  }
}
