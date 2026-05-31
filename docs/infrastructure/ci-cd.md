# CI/CD

Cada microsserviço tem um **`Jenkinsfile`** próprio que descreve um pipeline declarativo com três (ou quatro) estágios: **build**, **publicação no [ECR](ecr.md)** e **deploy no [EKS](eks.md)**. As credenciais da AWS ficam guardadas no Jenkins como `aws-cynthia-keys` e os parâmetros do ambiente (`AWS_ACCOUNT_ID`, `AWS_REGION`, `CLUSTER_NAME`) são injetados como variáveis.

## Fluxo geral

``` mermaid
flowchart LR
    commit([git push]) --> build[Build]
    build --> ecr["Build & Push<br/>Amazon ECR"]
    ecr --> eks["Deploy<br/>Amazon EKS"]
    eks --> cluster([Pods atualizados])
```

## Pipeline dos serviços Java

```groovy
pipeline {
    agent any
    environment {
        SERVICE      = 'order'  // account, auth, gateway, product, ...
        ECR_REGISTRY = "${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_REGION}.amazonaws.com"
        CLUSTER_NAME = "${env.CLUSTER_NAME}"
    }
    stages {
        stage('Build') {
            steps { sh 'mvn -B -DskipTests clean install' }   // instala módulo compartilhado + gera o jar
        }
        stage('Build & Push to Amazon ECR') {
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-cynthia-keys']]) {
                    sh "aws ecr get-login-password --region ${env.AWS_REGION} | docker login --username AWS --password-stdin ${env.ECR_REGISTRY}"
                    sh "docker build -t ${env.ECR_REGISTRY}/${env.SERVICE}:latest -f ../${env.SERVICE}-service/Dockerfile ."
                    sh "docker push ${env.ECR_REGISTRY}/${env.SERVICE}:latest"
                }
            }
        }
        stage('Deploy to Amazon EKS') {
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-cynthia-keys']]) {
                    sh "aws eks update-kubeconfig --name ${env.CLUSTER_NAME} --region ${env.AWS_REGION}"
                    sh "kubectl apply -f ../${env.SERVICE}-service/k8s/k8s.yaml"
                }
            }
        }
    }
}
```

## Pipeline do Exchange (Python / FastAPI)

O `exchange` substitui o build Maven por um estágio de **testes** com `pytest` em um *virtualenv*, e a imagem é construída a partir do `requirements.txt`:

```groovy
stage('Test') {
    steps {
        sh 'python3 -m venv .venv'
        sh '. .venv/bin/activate && pip install --no-cache-dir -r requirements-dev.txt'
        sh '. .venv/bin/activate && python -m pytest -q'
    }
}
// ...em seguida os mesmos estágios de Build & Push (ECR) e Deploy (EKS)
```

## Observações

- **Tag `:latest` + `imagePullPolicy: Always`** — o `kubectl apply` (ou um `rollout restart`) faz o cluster puxar sempre a imagem recém-publicada.
- **Deploy idempotente** — `kubectl apply -f k8s/k8s.yaml` cria ou atualiza `Deployment`/`Service`. Os manifestos de HPA (`k8s/hpa.yaml`) seguem o mesmo modelo.
- **Segredos** — nunca vão para o Git; são *credentials* do Jenkins e `Secret`s do Kubernetes.
