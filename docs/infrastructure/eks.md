# EKS (Amazon Elastic Kubernetes Service)

O cluster **`eks-store`** (Kubernetes `v1.35`, região `us-east-2`) é onde todos os microsserviços rodam. Ele é gerenciado pela AWS (control plane) e tem um *node group* de instâncias EC2 como *workers*.

## Nós

| Nó | Tipo | Zona |
|---|---|---|
| `ip-192-168-157-78` | `t3.medium` (2 vCPU / 4 GiB) | `us-east-2a` |
| `ip-192-168-217-171` | `t3.medium` (2 vCPU / 4 GiB) | `us-east-2b` |

São 2 nós em zonas diferentes (alta disponibilidade). A capacidade total (~4 vCPU) é o que limita o número de réplicas durante os [testes de carga](load-testing.md).

## Workloads

Cada microsserviço é um `Deployment` + `Service`:

| Serviço | Tipo de Service | Exposição |
|---|---|---|
| `gateway` | `LoadBalancer` | ELB público (entrada principal) |
| `exchange` | `LoadBalancer` | ELB público |
| `account` | `LoadBalancer` | ELB público |
| `order` | `LoadBalancer` | ELB público |
| `prometheus` | `LoadBalancer` | ELB público (`:9090`) |
| `auth`, `product` | `ClusterIP` | apenas internos (acessados via gateway) |
| `kafka`, `zookeeper`, `product-redis` | `ClusterIP` | dependências internas |

Os manifestos de cada serviço ficam em `<service>/k8s/k8s.yaml` e são aplicados com `kubectl apply -f` (pelo pipeline de CI/CD).

## Configuração sensível

- **`db-credentials`** (`Secret`) — host e senha do RDS.
- **`postgres-secrets`** / **`postgres-configmap`** — usuário e nome do banco.
- As imagens usam `imagePullPolicy: Always` com a tag `:latest`, então um `kubectl rollout restart deploy/<service>` puxa a versão mais recente do [ECR](ecr.md).

## Health checks e escalabilidade

- Cada serviço expõe um `health-check` usado nas `readinessProbe`/`livenessProbe`.
- O **`metrics-server`** está instalado (`kubectl top nodes`), habilitando o **HPA**. Cada serviço com teste de carga tem um `k8s/hpa.yaml` (1→10 réplicas, alvo de 50% de CPU). Veja [Load Testing](load-testing.md).

## Comandos úteis

```bash
aws eks update-kubeconfig --name eks-store --region us-east-2

kubectl get pods                      # estado dos serviços
kubectl get svc                       # endpoints (ELB) de cada serviço
kubectl top pods                      # uso de CPU/memória
kubectl rollout restart deploy/<svc>  # redeploy puxando :latest do ECR
kubectl logs deploy/<svc> --tail=50   # logs
```
