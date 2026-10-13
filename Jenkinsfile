pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timeout(time: 45, unit: 'MINUTES')
    }

    environment {
        APP_NAME = 'python-devops-demo'
        // Set DOCKERHUB_USER as a Jenkins global environment variable (username only).
        DOCKERHUB_USER = 'replace-with-your-dockerhub-username'
        DOCKER_IMAGE = "${DOCKERHUB_USER}/${APP_NAME}"
        AWS_REGION = 'eu-west-1'
        TF_IN_AUTOMATION = 'true'
        PIP_DISABLE_PIP_VERSION_CHECK = '1'
    }

    stages {
        stage('Checkout and identify flow') {
            steps {
                checkout scm
                script {
                    env.SOURCE_BRANCH = env.BRANCH_NAME ?: 'unknown'
                    if (env.BRANCH_NAME == 'main') {
                        env.IMAGE_TAG = "1.0.${env.BUILD_NUMBER}"
                    } else if (env.BRANCH_NAME == 'develop') {
                        env.IMAGE_TAG = "dev-${env.BUILD_NUMBER}"
                    } else if (env.BRANCH_NAME.startsWith('release/')) {
                        env.IMAGE_TAG = "rc-${env.BUILD_NUMBER}"
                    } else if (env.BRANCH_NAME.startsWith('hotfix/')) {
                        env.IMAGE_TAG = "hotfix-${env.BUILD_NUMBER}"
                    } else {
                        env.IMAGE_TAG = "feature-${env.BUILD_NUMBER}"
                    }
                    echo "GitFlow branch=${env.SOURCE_BRANCH}, image tag=${env.IMAGE_TAG}"
                }
            }
        }

        stage('Install dependencies') {
            steps {
                sh 'python3 --version'
                sh 'python3 -m venv .venv'
                sh '. .venv/bin/activate && pip install -r requirements.txt -r requirements-dev.txt'
            }
        }

        stage('Lint and formatting') {
            steps {
                sh '. .venv/bin/activate && ruff check app tests'
            }
        }

        stage('Unit tests') {
            steps {
                sh '. .venv/bin/activate && pytest -m "not performance" tests/test_unit.py --junitxml=unit-results.xml'
            }
            post { always { junit allowEmptyResults: true, testResults: 'unit-results.xml' } }
        }

        stage('Integration tests') {
            steps {
                sh '. .venv/bin/activate && pytest -m "not performance" tests/test_integration.py --junitxml=integration-results.xml'
            }
            post { always { junit allowEmptyResults: true, testResults: 'integration-results.xml' } }
        }

        stage('Coverage') {
            steps {
                sh '. .venv/bin/activate && pytest -m "not performance" --cov=app --cov-report=xml:coverage.xml --cov-report=term'
            }
        }

        stage('Security - Python') {
            steps {
                sh '. .venv/bin/activate && bandit -r app -ll -f json -o bandit-report.json'
                sh '. .venv/bin/activate && pip-audit -r requirements.txt'
            }
            post { always { archiveArtifacts artifacts: 'bandit-report.json', allowEmptyArchive: true } }
        }

        stage('Security - source filesystem') {
            when {
                anyOf {
                    branch 'develop'
                    branch 'main'
                    branch pattern: 'release/*', comparator: 'GLOB'
                    branch pattern: 'hotfix/*', comparator: 'GLOB'
                }
            }
            steps {
                sh 'trivy fs --exit-code 1 --severity CRITICAL --ignore-unfixed .'
            }
        }

        stage('SonarQube analysis') {
            when {
                not { changeRequest() }
            }
            steps {
                withSonarQubeEnv('sonarqube') {
                    sh '. .venv/bin/activate && sonar-scanner'
                }
            }
        }

        stage('SonarQube Quality Gate') {
            when {
                not { changeRequest() }
            }
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Performance smoke test') {
            when {
                anyOf {
                    branch 'develop'
                    branch 'main'
                    branch pattern: 'release/*', comparator: 'GLOB'
                    branch pattern: 'hotfix/*', comparator: 'GLOB'
                }
            }
            steps {
                sh '''
                    . .venv/bin/activate
                    (uvicorn app.main:app --host 127.0.0.1 --port 8000 > app.log 2>&1 & echo $! > app.pid)
                    trap 'kill $(cat app.pid) 2>/dev/null || true' EXIT
                    for i in $(seq 1 20); do
                      curl -fsS http://127.0.0.1:8000/health && break
                      sleep 1
                    done
                    locust -f locustfile.py --headless -u 5 -r 1 -t 30s --host http://127.0.0.1:8000 \
                      --only-summary --exit-code-on-error 1
                '''
            }
        }

        stage('Docker build') {
            when {
                anyOf {
                    branch 'develop'
                    branch 'main'
                    branch pattern: 'release/*', comparator: 'GLOB'
                    branch pattern: 'hotfix/*', comparator: 'GLOB'
                }
            }
            steps {
                sh 'docker build --pull -t ${DOCKER_IMAGE}:${IMAGE_TAG} -t ${DOCKER_IMAGE}:candidate .'
            }
        }

        stage('Security - Docker image') {
            when {
                anyOf {
                    branch 'develop'
                    branch 'main'
                    branch pattern: 'release/*', comparator: 'GLOB'
                    branch pattern: 'hotfix/*', comparator: 'GLOB'
                }
            }
            steps {
                sh 'trivy image --exit-code 1 --severity CRITICAL --ignore-unfixed ${DOCKER_IMAGE}:${IMAGE_TAG}'
            }
        }

        stage('Push image to Docker Hub') {
            when {
                anyOf {
                    branch 'develop'
                    branch 'main'
                    branch pattern: 'release/*', comparator: 'GLOB'
                    branch pattern: 'hotfix/*', comparator: 'GLOB'
                }
            }
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DH_USER', passwordVariable: 'DH_TOKEN')]) {
                    sh '''
                      echo "$DH_TOKEN" | docker login -u "$DH_USER" --password-stdin
                      docker push "${DOCKER_IMAGE}:${IMAGE_TAG}"
                      docker logout
                    '''
                }
            }
        }

        stage('Terraform validate') {
            when {
                anyOf {
                    branch 'develop'
                    branch 'main'
                    branch pattern: 'release/*', comparator: 'GLOB'
                }
            }
            steps {
                dir('infra/terraform') {
                    sh 'terraform fmt -check -recursive'
                    sh 'terraform init -backend=false'
                    sh 'terraform validate'
                }
            }
        }

        stage('Terraform plan - production') {
            when { branch 'main' }
            steps {
                dir('infra/terraform') {
                    sh 'terraform init'
                    sh 'terraform plan -out=tfplan'
                    archiveArtifacts artifacts: 'tfplan', fingerprint: true
                }
            }
        }

        stage('Approve production deployment') {
            when { branch 'main' }
            steps {
                input message: "Deploy ${DOCKER_IMAGE}:${IMAGE_TAG} to production AWS?", ok: 'Deploy'
            }
        }

        stage('Terraform apply - production') {
            when { branch 'main' }
            steps {
                dir('infra/terraform') {
                    sh 'terraform apply -auto-approve tfplan'
                    sh 'terraform output -raw public_ip > ../../public_ip.txt'
                }
                archiveArtifacts artifacts: 'public_ip.txt', fingerprint: true
            }
        }

        stage('Ansible deploy - production') {
            when { branch 'main' }
            steps {
                withCredentials([sshUserPrivateKey(credentialsId: 'ansible-ssh-key',
                    keyFileVariable: 'SSH_KEY', usernameVariable: 'SSH_USER')]) {
                    sh '''
                      IP=$(cat public_ip.txt)
                      ansible-playbook -i "${IP}," infra/ansible/deploy.yml \
                        -u "$SSH_USER" --private-key "$SSH_KEY" \
                        -e "docker_image=${DOCKER_IMAGE}:${IMAGE_TAG}"
                    '''
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'coverage.xml,app.log', allowEmptyArchive: true
            sh 'docker image prune -f || true'
            cleanWs()
        }
        success { echo "Pipeline succeeded for ${env.BRANCH_NAME}" }
        failure { echo "Pipeline failed for ${env.BRANCH_NAME}; inspect stage logs and archived reports." }
    }
}
