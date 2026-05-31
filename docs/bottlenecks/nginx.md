# Nginx

## Identificação do problema

O `gateway-service` foi configurado com **3 réplicas** para suportar maior volume de requisições simultâneas. Porém, sem um ponto de entrada centralizado, o cliente precisaria saber o endereço de cada réplica — e a carga ficaria distribuída de forma desigual ou totalmente concentrada em uma instância.

## Solução

O Nginx atua como **reverse proxy e load balancer** na frente do cluster de gateways. Ele recebe todo o tráfego externo na porta `8080` e distribui as requisições entre as réplicas usando a política `least_conn` — que encaminha cada nova conexão para a instância com menos conexões ativas naquele momento, evitando sobrecarga em réplicas ocupadas.

### 1. Configuração do Nginx

```nginx
# api/setup/nginx/nginx.conf

events {}

http {

    upstream gateway_cluster {
        least_conn;              # <- política: menor número de conexões ativas
        server gateway:8080;     # Docker resolve "gateway" para todas as réplicas
    }

    server {
        listen 80;

        location / {
            proxy_pass         http://gateway_cluster;
            proxy_set_header   Host              $host;
            proxy_set_header   X-Real-IP         $remote_addr;
            proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
            proxy_set_header   X-Forwarded-Proto $scheme;
        }
    }
}
```

O Docker resolve o hostname `gateway` para todas as réplicas do serviço — o Nginx não precisa conhecer seus IPs individualmente.

### 2. Declaração no compose

```yaml
# api/compose.yaml

gateway:
  build:
    context: ./gateway-service
    dockerfile: Dockerfile
  hostname: gateway
  deploy:
    replicas: 3       # <- 3 instâncias do gateway

nginx:
  image: nginx:latest
  ports:
    - 8080:80         # <- única porta exposta ao cliente
  volumes:
    - $SETUP/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
  depends_on:
    - gateway
```

### 3. Por que `least_conn` e não `round-robin`?

O `round-robin` (padrão do Nginx) distribui requisições em rodízio fixo, sem considerar quanto tempo cada uma leva. Em uma API com operações de duração variável (ex.: validação de JWT, consultas ao banco), isso pode sobrecarregar uma réplica que ainda está processando requests lentos enquanto outras ficam ociosas. O `least_conn` corrige isso ao sempre preferir a réplica com menor fila de conexões abertas.

## Fluxo de entrada

```
Cliente :8080
      ↓
   Nginx (least_conn)
      ↓
  ┌───────────────────┐
  │ gateway réplica 1 │
  │ gateway réplica 2 │
  │ gateway réplica 3 │
  └───────────────────┘
      ↓
  AuthorizationFilter → auth-service → microsserviços
```
