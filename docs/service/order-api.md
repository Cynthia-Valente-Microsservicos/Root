# Order API

#### **Responsável**: Cynthia Naoko Yasutake

Repositórios:

| Parte | Repositório | Documentação |
|---|---|---|
| Interface | [interface](https://github.com/Cynthia-Valente-Microsservicos/order) | — |
| Serviço | [service](https://github.com/Cynthia-Valente-Microsservicos/order-service.git) | [Order-Service](order-service.md) |

A API é responsável por gerenciar os pedidos do e-commerce. Um pedido é criado a partir de uma lista de itens (produto + quantidade); para cada item o serviço consulta o `product-service` via Feign para obter o preço, persiste o pedido no PostgreSQL e publica um evento no Kafka (`order-events`) para que o estoque seja reduzido de forma assíncrona.

## Diagrama

``` mermaid
flowchart LR
    subgraph api [Trusted Layer]
        direction TB
        gateway --> account
        gateway --> auth
        account --> db@{ shape: cyl, label: "Database" }
        auth --> account
        gateway e5@==> product
        gateway e6@==> order:::red
        product e2@==> db
        order e3@==> db
        order e4@==> product
        order e7@==> kafka@{ shape: cyl, label: "Kafka order-events" }
        kafka e8@==> product
    end
    internet e1@==>|request| gateway
    e1@{ animate: true }
    e3@{ animate: true }
    e4@{ animate: true }
    e6@{ animate: true }
    e7@{ animate: true }
    e8@{ animate: true }
    classDef red fill:#fcc
    click order "#order-api" "Order API"
```

## Autenticação

Todas as rotas (exceto o `health-check`) exigem um usuário autenticado. O gateway valida o JWT e injeta o header `id-account`, usado pelo serviço para associar o pedido à conta.

## Endpoints

`POST /orders` - Cria um novo pedido para a conta autenticada. Para cada item, o preço é buscado no `product-service`.

=== "Request"

    ``` { .json .copy .select linenums='1' }
    {
        "items": [
            { "idProduct": "0195abfb-7074-73a9-9d26-b4b9fbaab0a8", "quantity": 2 }
        ]
    }
    ```
=== "Response"

    ``` { .json .copy .select linenums='1' }
    {
        "id": "0195ae95-5be7-7dd3-b35d-7a7d87c404fb",
        "date": "2026-05-30T10:00:00",
        "items": [
            {
                "id": "0195ae95-5be7-7dd3-b35d-7a7d87c404fc",
                "product": { "id": "0195abfb-7074-73a9-9d26-b4b9fbaab0a8" },
                "quantity": 2,
                "total": 20.24
            }
        ],
        "total": 20.24
    }
    ```
    ```bash
    Response code: 201 (created)
    ```

`GET /orders` - Lista (em formato resumido) os pedidos da conta autenticada.

=== "Response"

    ``` { .json .copy .select linenums='1' }
    [
        {
            "id": "0195ae95-5be7-7dd3-b35d-7a7d87c404fb",
            "date": "2026-05-30T10:00:00",
            "total": 20.24
        }
    ]
    ```
    ```bash
    Response code: 200 (ok)
    ```

`GET /orders/{id}` - Devolve os detalhes completos de um pedido (itens e totais).

=== "Response"

    ``` { .json .copy .select linenums='1' }
    {
        "id": "0195ae95-5be7-7dd3-b35d-7a7d87c404fb",
        "date": "2026-05-30T10:00:00",
        "items": [
            {
                "id": "0195ae95-5be7-7dd3-b35d-7a7d87c404fc",
                "product": { "id": "0195abfb-7074-73a9-9d26-b4b9fbaab0a8" },
                "quantity": 2,
                "total": 20.24
            }
        ],
        "total": 20.24
    }
    ```
    ```bash
    Response code: 200 (ok)
    ```

`GET /orders/health-check` - Verifica se o serviço está no ar. Usada internamente pelo gateway, pelo Kubernetes (readiness/liveness) e pelo teste de carga.

=== "Response"

    ```bash
    Response code: 200 (ok)
    ```

## Tecnologias

| Tecnologia | Uso |
|---|---|
| Spring Boot | Framework base do serviço |
| PostgreSQL | Banco relacional para persistência dos pedidos e itens (schema `orders`) |
| OpenFeign | Cliente HTTP síncrono para buscar preços no `product-service` |
| Apache Kafka | Publicação do evento `order-events` após a criação do pedido (redução de estoque assíncrona) |
| Prometheus + Grafana | Observabilidade e monitoramento de métricas do serviço |
| Kubernetes (HPA) | Escalabilidade horizontal automática com base no uso de CPU |

## Bottlenecks identificados

- **Messaging (Kafka)** — a redução de estoque é disparada por um evento assíncrono, desacoplando o `order-service` do `product-service` e evitando que a criação do pedido fique bloqueada. Detalhes em [Messaging](../bottlenecks/messaging.md).
- **Observabilidade (Prometheus + Grafana)** — as métricas do serviço são expostas em `/order/actuator/prometheus` e monitoradas para identificar gargalos. Detalhes em [Prometheus](../bottlenecks/prometheus.md).
- **Load Balancing (Nginx + HPA)** — o gateway distribui as requisições e o HPA escala o serviço automaticamente sob carga. O teste de carga do `order` está documentado em [Load Testing](../infrastructure/load-testing.md).
