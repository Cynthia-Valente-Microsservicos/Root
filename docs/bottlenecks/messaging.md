# Messaging (Apache Kafka)

## Identificação do problema

Ao criar um pedido, o `order-service` precisava atualizar o estoque dos produtos envolvidos. A abordagem direta seria uma chamada REST síncrona do `order-service` para o `product-service` — mas isso cria **acoplamento temporal**: se o product-service estiver lento ou indisponível, a criação do pedido falha junto, mesmo que o pedido em si tenha sido salvo com sucesso.

## Solução

A comunicação entre os serviços foi desacoplada com **Apache Kafka**. Após salvar o pedido, o `order-service` publica um evento no tópico `order-events`. O `product-service` consome esse evento de forma assíncrona e decrementa o estoque. Os dois serviços evoluem e escalam independentemente.

### 1. Configuração do tópico e producer (order-service)

```java
// api/order-service/src/main/java/store/order/KafkaConfig.java
@Bean
public NewTopic orderEventsTopic() {
    return TopicBuilder.name("order-events")
            .partitions(3)    // <- 3 partições para paralelismo
            .replicas(1)
            .build();
}

@Bean
public KafkaTemplate<String, String> kafkaTemplate() {
    return new KafkaTemplate<>(producerFactory());
}
```

### 2. Publicação do evento após criar o pedido

O serviço salva o pedido no banco e, em seguida, publica o evento — sem esperar resposta do product-service:

```java
// api/order-service/src/main/java/store/order/OrderService.java
public Order createOrder(OrderIn in, String idAccount) {

    // ... monta os itens consultando preços via REST no product-service
    OrderModel savedModel = orderRepository.save(orderModel);
    Order orderFinal = savedModel.to();

    orderProducer.sendOrderEvent(OrderParser.to(orderFinal));  // <- evento assíncrono

    return orderFinal;
}
```

```java
// api/order-service/src/main/java/store/order/OrderProducer.java
public void sendOrderEvent(OrderOut orderOut) {
    String message = objectMapper.writeValueAsString(orderOut);
    String key = (orderOut.id() != null) ? orderOut.id() : "";

    kafkaTemplate.send("order-events", key, message)
        .whenComplete((result, ex) -> {
            if (ex != null) {
                System.err.println("[KAFKA] Falha ao entregar evento " + key + ": " + ex.getMessage());
            } else {
                System.out.println("[KAFKA] Evento entregue: " + key
                    + " | partition=" + result.getRecordMetadata().partition()
                    + " | offset=" + result.getRecordMetadata().offset());
            }
        });
}
```

### 3. Consumo do evento (product-service)

O `OrderConsumer` escuta o tópico `order-events` no consumer group `product-service` e chama `ProductService#reduceStock` para cada item do pedido:

```yaml
# api/product-service/src/main/resources/application.yaml
spring:
  kafka:
    bootstrap-servers: ${KAFKA_BOOTSTRAP_SERVERS:localhost:9092}
    consumer:
      group-id: product-service
      auto-offset-reset: earliest
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.apache.kafka.common.serialization.StringDeserializer
```

> **Imagem — Kafka UI mostrando o tópico `order-events` e mensagens:**
> *(adicionar screenshot)*

### 4. Kafka declarado no compose

```yaml
# api/compose.yaml
kafka:
  image: apache/kafka:latest
  hostname: kafka
  ports:
    - 9092:9092
  environment:
    KAFKA_NODE_ID: 1
    KAFKA_PROCESS_ROLES: broker,controller
    KAFKA_LISTENERS: PLAINTEXT://:9092,CONTROLLER://:9093
    KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
    KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:9093
    CLUSTER_ID: mkU3OId9TKiR76mMPwglBZ

kafka-ui:
  image: provectuslabs/kafka-ui:latest
  ports:
    - 8085:8080
  environment:
    KAFKA_CLUSTERS_0_NAME: local
    KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:9092
```

> **Imagem — Kafka UI com partições e offsets do tópico:**
> *(adicionar screenshot)*

## Fluxo de mensageria

```
POST /orders
      ↓
 order-service
      ├── salva pedido no PostgreSQL
      └── publica em "order-events" (key = orderId)
                  ↓  assíncrono
           product-service (group: product-service)
                  └── OrderConsumer → reduceStock(productId, quantity)
                                           └── @CacheEvict invalida Redis
```

## Por que 3 partições?

Com 3 partições no tópico `order-events`, até 3 instâncias do `product-service` podem consumir em paralelo (uma por partição), aumentando o throughput de atualização de estoque sem concorrência entre consumidores.
