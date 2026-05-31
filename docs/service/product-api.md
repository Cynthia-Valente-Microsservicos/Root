# Product API

#### **Responsável**: Cynthia Naoko Yasutake

Repositórios:

| Parte | Repositório | Documentação |
|---|---|---|
| Interface | [interface](https://github.com/Cynthia-Valente-Microsservicos/product) | [Product](product.md) |
| Serviço | [service](https://github.com/Cynthia-Valente-Microsservicos/product-service.git) | [Product-Service](product-service.md) |

A API é responsável por gerenciar os produtos do e-commerce. Nela, temos rotas que apenas o `ADMIN` possui acesso, como `/POST /products` e o `DELETE /products`

## Diagrama

``` mermaid
flowchart LR
    subgraph api [Trusted Layer]
        direction TB
        gateway --> account
        gateway --> auth
        account --> db@{ shape: cyl, label: "Database" }
        auth --> account
        gateway e5@==> product:::red
        gateway e6@==> order
        product e2@==> db
        order e3@==> db
        order e4@==> product
    end
    internet e1@==>|request| gateway
    e1@{ animate: true }
    e2@{ animate: true }
    e3@{ animate: true }
    e4@{ animate: true }
    e5@{ animate: true }
    e6@{ animate: true }
    classDef red fill:#fcc
    click product "#product-api" "Product API"
```

## Endpoints

`POST /products` - Criar Produto - Apenas o **`ADMIN`** tem acesso a essa rota

=== "Request"

    ``` { .json .copy .select linenums='1' }
    {
        "name": "Tomato",
        "price": 10.12,
        "unit": "kg"
    }
    ```
=== "Response"

    ``` { .json .copy .select linenums='1' }
    {
        "id": "0195abfb-7074-73a9-9d26-b4b9fbaab0a8",
        "name": "Tomato",
        "price": 10.12,
        "unit": "kg"
    }
    ```
    ```bash
    Response code: 201 (created)
    ```

`GET /products` - Devolve todos os produtos cadastrados na loja - Tanto o **`USER`** quanto **`ADMIN`** podem acessá-la

=== "Response"

        ``` { .json .copy .select linenums='1' }
        [
            {
                "id": "0195abfb-7074-73a9-9d26-b4b9fbaab0a8",
                "name": "Tomato",
                "price": 10.12,
                "unit": "kg"
            },
            {
                "id": "0195abfe-e416-7052-be3b-27cdaf12a984",
                "name": "Cheese",
                "price": 0.62,
                "unit": "slice"
            }
        ]
        ```
        ```bash
        Response code: 200 (ok)
        ```

`GET /products/{id}` - Devolve um produto com base no ID - Tanto o **`USER`** quanto **`ADMIN`** podem acessá-la.

 === "Response"

        ``` { .json .copy .select linenums='1' }
        {
            "id": "0195abfb-7074-73a9-9d26-b4b9fbaab0a8",
            "name": "Tomato",
            "price": 10.12,
            "unit": "kg"
        }
        ```
        ```bash
        Response code: 200 (ok)
        ```

`DELETE /products/{id}` - Deleta um produto com base no ID. - Apenas o **`ADMIN`** tem acesso a essa rota

=== "Response"

        ```bash
        Response code: 204 (no content)
        ```

`GET /products/search?name={name}` - Busca produtos cujo nome contenha o termo informado. Se `name` for omitido, retorna todos os produtos. Tanto o **`USER`** quanto **`ADMIN`** podem acessá-la.

=== "Response"

    ``` { .json .copy .select linenums='1' }
    [
        {
            "id": "0195abfb-7074-73a9-9d26-b4b9fbaab0a8",
            "name": "Tomato",
            "price": 10.12,
            "unit": "kg"
        }
    ]
    ```
    ```bash
    Response code: 200 (ok)
    ```

`GET /products/health-check` - Verifica se o serviço está no ar. Usada internamente pelo gateway e pelo Kubernetes.

=== "Response"

    ```bash
    Response code: 200 (ok)
    ```

## Tecnologias

| Tecnologia | Uso |
|---|---|
| Spring Boot | Framework base do serviço |
| PostgreSQL | Banco de dados relacional para persistência dos produtos |
| Redis | Cache dos produtos por ID (TTL de 5 minutos), evitando consultas repetidas ao banco |
| Apache Kafka | Consumidor do tópico `order-events` para reduzir estoque após um pedido ser criado |
| Prometheus + Grafana | Observabilidade e monitoramento de métricas do serviço |
| Kubernetes (HPA) | Escalabilidade horizontal automática com base no uso de CPU |

## Bottlenecks identificados

- **Caching (Redis)** — consultas repetidas ao banco para o mesmo produto são absorvidas pelo cache. Detalhes em [Redis](../bottlenecks/redis.md).
- **Messaging (Kafka)** — a redução de estoque acontece de forma assíncrona via evento, desacoplando o product-service do order-service. Detalhes em [Messaging](../bottlenecks/messaging.md).
- **Observabilidade (Prometheus + Grafana)** — métricas do serviço são expostas e monitoradas para identificar gargalos em produção. Detalhes em [Prometheus](../bottlenecks/prometheus.md).
- **Load Balancing (Nginx + HPA)** — o gateway distribui as requisições e o HPA escala o serviço automaticamente sob carga. Detalhes em [Nginx](../bottlenecks/nginx.md).
