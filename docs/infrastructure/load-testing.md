# Load Testing

O load testing foi feito no Windows usando ferramentas nativas do Kubernetes e um pod BusyBox para simular tráfego contra o serviço de gateway.

## Configuração

Foram usados 3 terminais simultaneamente: um para criar o HPA e acompanhar seu status, um para observar os pods escalando, e um para gerar a carga.

---

## Terminal 1 — Criar o HPA e acompanhar

```powershell
kubectl autoscale deployment gateway --cpu-percent=50 --min=1 --max=10
kubectl get hpa -w
```

O primeiro comando cria um HPA que mantém o uso de CPU em torno de 50%, escalando o deployment `gateway` entre 1 e 10 réplicas automaticamente. O segundo acompanha o status do HPA em tempo real, mostrando o uso de CPU atual e o número de réplicas desejadas vs. ativas.

---

## Terminal 2 — Acompanhar os pods escalando

```powershell
kubectl get pods -l app=gateway -w
```

Observa apenas os pods do gateway, mostrando novas réplicas sendo criadas (ou encerradas) conforme o autoscaler reage à carga.

---

## Terminal 3 — Gerar carga

```powershell
kubectl run -i --tty load-generator --rm --image=busybox:1.28 --restart=Never -- /bin/sh -c "while true; do wget -q -O- http://gateway:8080/products; done"
```

Sobe um pod temporário de BusyBox dentro do cluster que fica fazendo requisições contínuas ao endpoint `/products`. O pod é removido automaticamente (`--rm`) ao sair do shell.

---

## Comportamento esperado

1. O uso de CPU no deployment `gateway` sobe acima de 50%.
2. O HPA aumenta o número de réplicas (visível no Terminal 1 e 2).
3. A carga é distribuída entre as novas réplicas e o CPU por pod cai.
4. Após parar o gerador de carga, as réplicas voltam para 1 após o período de cooldown (normalmente ~5 minutos).

## Vídeo demonstrativo do Products

<iframe width="100%" height="470" src="https://youtu.be/SFass6q2tc4" allowfullscreen></iframe>