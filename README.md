# Store — Plataforma de Microsserviços

Plataforma de e-commerce desenvolvida na disciplina de Plataformas, Microsserviços e APIs do Insper. Arquitetura baseada em microsserviços Java Spring Boot, orquestrada com Docker Compose localmente e Kubernetes (EKS) em produção.

## Arquitetura

```
Cliente (React + Vite)
        │
        ▼
    Nginx :8080
        │  (load balance)
        ▼
  Gateway-Service  ←──── auth-service (valida JWT)
   (3 réplicas)
        │
  ┌─────┼───────────────┐
  ▼     ▼               ▼
account auth          product  order
:8080  :8080          :8080    :8080
  │                     │        │
  ▼                     ▼        ▼
PostgreSQL            Redis    Kafka
                    (cache)  (order-events)
                                 │
                                 └──► product-service
                                      (reduz estoque)
```

## Serviços

| Serviço | Descrição | Porta |
|---------|-----------|-------|
| `nginx` | Reverse proxy + load balancer | 8080 |
| `gateway-service` | API Gateway — roteamento e autenticação JWT | — |
| `account-service` | Gerenciamento de contas | — |
| `auth-service` | Autenticação e geração de tokens JWT | — |
| `product-service` | Catálogo de produtos com cache Redis | — |
| `order-service` | Pedidos — publica eventos no Kafka | — |

## Infraestrutura

| Componente | Descrição | Porta |
|------------|-----------|-------|
| PostgreSQL 17 | Banco de dados principal | 5432 |
| Redis 7 | Cache de produtos | 6379 |
| Apache Kafka | Mensageria assíncrona | 9092 |
| Kafka UI | Interface web do Kafka | 8085 |
| Prometheus | Coleta de métricas | 9090 |
| Grafana | Dashboards de monitoramento | 3000 |

## Módulos de contrato

Bibliotecas Maven compartilhadas que definem DTOs e clientes Feign:

| Módulo | Consumido por |
|--------|--------------|
| `api/account` | `auth-service` |
| `api/auth` | `gateway-service` |
| `api/product` | `order-service` |
| `api/order` | `website` |

## Executando localmente

### Pré-requisitos

- Docker + Docker Compose
- Java 25
- Maven

### Variáveis de ambiente

Crie `api/.env` com:

```env
VOLUME_DB=./volume/db
SETUP=./setup
JWT_SECRET_KEY=<base64-secret>
DB_USER=store
DB_PASSWORD=devpass
DB_NAME=store
CORS_ALLOWED_ORIGINS=http://localhost:5173
CORS_ALLOWED_CREDENTIALS=true
```

### Subindo a stack

```bash
# Instalar módulos de contrato
cd api/account && mvn install -DskipTests && cd ../..
cd api/auth    && mvn install -DskipTests && cd ../..
cd api/product && mvn install -DskipTests && cd ../..
cd api/order   && mvn install -DskipTests && cd ../..

# Subir todos os serviços
cd api
docker compose up --build
```

### Frontend

```bash
cd website
npm install
npm run dev   # http://localhost:5173
```

## Documentação

Documentação completa disponível via MkDocs:

```bash
pip install -r requirements.txt
mkdocs serve
```

## Stack

- **Backend:** Java 25 · Spring Boot 4.x · Spring Cloud 2025.x
- **Frontend:** React 19 · Vite 8
- **Dados:** PostgreSQL 17 · Redis 7 · Apache Kafka
- **Observabilidade:** Prometheus · Grafana · Micrometer
- **Infra:** Docker Compose · Kubernetes (EKS) · Nginx · Jenkins (CI/CD)
