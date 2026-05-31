# AWS

Toda a infraestrutura do projeto roda na **AWS**, na região **`us-east-2`** (Ohio), sob a conta `730335608828`. O acesso programático (CI/CD e `kubectl`) é feito por um usuário IAM dedicado com chaves de acesso.

## Serviços utilizados

| Serviço | Papel no projeto |
|---|---|
| **EKS** (Elastic Kubernetes Service) | Cluster `eks-store` que orquestra todos os microsserviços. Detalhes em [EKS](eks.md). |
| **ECR** (Elastic Container Registry) | Registro privado das imagens Docker de cada serviço. Detalhes em [ECR](ecr.md). |
| **RDS** (PostgreSQL) | Banco gerenciado `store-db` compartilhado pelos serviços (cada um com seu *schema*: `accounts`, `orders`, etc.). |
| **ELB** (Elastic Load Balancer) | Provisionado automaticamente para cada `Service` do tipo `LoadBalancer` (gateway, exchange, account, order, prometheus). |
| **IAM** | Usuário/credenciais usados pelo Jenkins e pelo `kubectl` para autenticar nos serviços acima. |

## Topologia

``` mermaid
flowchart TB
    internet([Internet]) -->|HTTP :8080| elb[ELB / LoadBalancer]
    elb --> gateway
    subgraph eks [EKS - cluster eks-store]
        gateway --> auth
        gateway --> account
        gateway --> product
        gateway --> order
        gateway --> exchange
    end
    account --> rds[(RDS PostgreSQL<br/>store-db)]
    order --> rds
    product --> rds
    exchange -->|cotações| ext[(API de câmbio<br/>externa)]
    eks -. pull de imagens .-> ecr[(ECR)]
```

## Acesso

```bash
# configura o kubectl para o cluster EKS
aws eks update-kubeconfig --name eks-store --region us-east-2

# login no registro de imagens
aws ecr get-login-password --region us-east-2 \
  | docker login --username AWS --password-stdin 730335608828.dkr.ecr.us-east-2.amazonaws.com
```

> **Segurança:** as credenciais de acesso (IAM keys, senha do RDS) nunca são versionadas. No CI/CD elas vivem como *credentials* do Jenkins (`aws-cynthia-keys`) e, no cluster, como `Secret`s do Kubernetes (`db-credentials`, `postgres-secrets`).
