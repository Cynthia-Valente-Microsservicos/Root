# Load Testing

Os testes de carga validam que os serviços escalam horizontalmente sob tráfego. Usamos o **HPA (Horizontal Pod Autoscaler)** do Kubernetes, que ajusta automaticamente o número de réplicas de um deployment com base no uso de CPU, e geramos carga de dentro do próprio cluster com pods BusyBox fazendo requisições contínuas.

## Pré-requisitos

- **`metrics-server`** instalado no cluster (o HPA lê as métricas de CPU dele). Verifique com `kubectl top nodes`.
- Os deployments precisam declarar **`resources.requests.cpu`** — o HPA calcula a utilização como `uso / request`. No nosso stack o `exchange` pede `100m` e o `order` pede `300m`.

## Como funciona

```bash
# cria o HPA: mantém ~50% de CPU, entre 1 e 10 réplicas
kubectl autoscale deployment <service> --cpu-percent=50 --min=1 --max=10

# acompanha o autoscaler em tempo real
kubectl get hpa -w

# acompanha os pods escalando
kubectl get pods -l app=<service> -w
```

As definições de HPA também estão versionadas em cada serviço (`k8s/hpa.yaml`), aplicadas com `kubectl apply -f k8s/hpa.yaml`.

Para gerar carga, sobe-se um (ou vários) pods BusyBox que disparam requisições em paralelo contra o `health-check` do serviço — endpoint barato que ainda assim consome CPU sob alta concorrência:

```bash
kubectl run -i --tty load --rm --image=busybox:1.28 --restart=Never -- \
  /bin/sh -c "while true; do wget -q -O- http://<service>:8080/<service>s/health-check; done"
```

> Há também um script reutilizável no repositório — `loadtest.sh <service> <path>` — que cria o HPA, sobe os geradores de carga, acompanha o escalonamento e limpa tudo ao final.

---

## Gateway / Products

Teste original feito no Windows com terminais nativos do Kubernetes:

```powershell
kubectl autoscale deployment gateway --cpu-percent=50 --min=1 --max=10
kubectl get hpa -w
kubectl get pods -l app=gateway -w
kubectl run -i --tty load-generator --rm --image=busybox:1.28 --restart=Never -- /bin/sh -c "while true; do wget -q -O- http://gateway:8080/products; done"
```

### Vídeo demonstrativo do Products

<iframe width="100%" height="470" src="https://youtu.be/SFass6q2tc4" allowfullscreen></iframe>

---

## Exchange (Python / FastAPI)

```bash
kubectl apply -f exchange-service/k8s/hpa.yaml      # HPA exchange: 1..10, alvo 50% CPU
# carga: vários pods BusyBox batendo no health-check do exchange
kubectl run load --image=busybox:1.28 --restart=Never -- \
  /bin/sh -c 'while true; do wget -q -O- http://exchange:8080/exchanges/health-check; done'
```

### Resultado observado

Com o `exchange` pedindo `100m` de CPU e dezenas de conexões simultâneas, o HPA escalou rapidamente do baseline de 1 réplica até o máximo:

| Momento | CPU (uso/alvo) | Réplicas desejadas |
|---|---|---|
| Baseline (sem carga) | `<1%` / 50% | 1 |
| ~70s de carga | `294%` / 50% | 4 |
| Pico (~3min) | `138%` / 50% | **10** |

Cada pod estabilizou em torno de `120–165m` de CPU (acima do request de `100m`), confirmando que o autoscaler distribuiu a carga entre as novas réplicas. Como o cluster tem apenas 2 nós, parte das 10 réplicas desejadas ficou em `Pending` por falta de capacidade — comportamento esperado e que evidencia o limite de recursos do cluster.

---

## Order (Java / Spring Boot)

```bash
kubectl apply -f order-service/k8s/hpa.yaml         # HPA order: 1..10, alvo 50% CPU
kubectl run load --image=busybox:1.28 --restart=Never -- \
  /bin/sh -c 'while true; do wget -q -O- http://order:8080/orders/health-check; done'
```

### Resultado observado

Com o `order` pedindo `300m` de CPU (alvo de `150m` por pod):

| Momento | CPU (uso/alvo) | Réplicas desejadas |
|---|---|---|
| Baseline (sem carga) | `<1%` / 50% | 1 |
| ~70s de carga | `165%` / 50% | 6 |
| Pico (~3min) | `65%` / 50% | **10** |

À medida que novas réplicas entraram em operação, o uso médio de CPU por pod caiu (de `>150%` para `~65%`), mostrando o balanceamento da carga. Assim como no exchange, o teto efetivo de réplicas em execução foi limitado pela capacidade dos 2 nós.

---

## Comportamento esperado (resumo)

1. O uso de CPU sobe acima de 50% do *request* do container.
2. O HPA aumenta o número de réplicas (visível em `kubectl get hpa` e `kubectl get pods`).
3. A carga é distribuída entre as novas réplicas e o CPU por pod cai.
4. Após parar o gerador de carga, as réplicas voltam para 1 depois do período de *cooldown* (padrão ~5 minutos).
