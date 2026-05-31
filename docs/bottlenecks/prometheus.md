# Prometheus e Grafana

## Identificação do problema

Em uma arquitetura de microsserviços, falhas e lentidões são difíceis de rastrear sem observabilidade centralizada. Sem métricas, um aumento de latência no gateway ou um pico de erros no product-service só seria percebido por reclamação de usuário — tarde demais para agir preventivamente.

## Solução

Cada microsserviço expõe um endpoint `/actuator/prometheus` via Spring Boot Actuator + Micrometer. O Prometheus coleta essas métricas a cada segundo e o Grafana as exibe em dashboards em tempo real, permitindo identificar gargalos antes que virem incidentes.

### 1. Dependências nos microsserviços

Cada serviço inclui no `pom.xml` o actuator e o registry do Prometheus:

```xml
<!-- api/product-service/pom.xml -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>
```

### 2. Exposição do endpoint de métricas

Cada serviço configura o actuator para expor apenas os endpoints necessários, com um caminho que evita colisão com as rotas da API:

```yaml
# api/product-service/src/main/resources/application.yaml
management:
  endpoints:
    web:
      base-path: /product/actuator
      exposure:
        include: ['prometheus', 'health']
```

```yaml
# api/gateway-service/src/main/resources/application.yaml
management:
  endpoints:
    web:
      base-path: /gateway/actuator
      exposure:
        include: ['prometheus', 'health']
```

O gateway também ativa métricas nativas do Spring Cloud Gateway:

```yaml
# api/gateway-service/src/main/resources/application.yaml
spring:
  cloud:
    gateway:
      metrics:
        enabled: true
```

### 3. Coleta pelo Prometheus

O `prometheus.yml` define um job de scrape por microsserviço, com intervalo de **1 segundo** para alta granularidade:

```yaml
# api/setup/prometheus/prometheus.yml
scrape_configs:

  - job_name: 'GatewayMetrics'
    metrics_path: '/gateway/actuator/prometheus'
    scrape_interval: 1s
    static_configs:
      - targets:
        - gateway:8080
        labels:
          application: 'Gateway Application'

  - job_name: 'ProductMetrics'
    metrics_path: '/products/actuator/prometheus'
    scrape_interval: 1s
    static_configs:
      - targets:
        - product:8080
        labels:
          application: 'Product Application'

  - job_name: 'OrderMetrics'
    metrics_path: '/orders/actuator/prometheus'
    scrape_interval: 1s
    static_configs:
      - targets:
        - order:8080
        labels:
          application: 'Order Application'

  # ... AuthMetrics, AccountMetrics, ExchangeMetrics
```

### 4. Stack no compose

```yaml
# api/compose.yaml
prometheus:
  image: prom/prometheus:latest
  hostname: prometheus
  ports:
    - 9090:9090
  volumes:
    - $SETUP/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml

grafana:
  image: grafana/grafana-enterprise
  hostname: grafana
  ports:
    - 3000:3000
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
  volumes:
    - $SETUP/grafana:/var/lib/grafana
    - $SETUP/grafana/provisioning/datasources:/etc/grafana/provisioning/datasources
```

### 5. Dashboards no Grafana

> **Imagem — visão geral do dashboard:**
> *(adicionar screenshot)*

> **Imagem — latência por rota do gateway:**
> *(adicionar screenshot)*

> **Imagem — uso de memória e CPU por serviço:**
> *(adicionar screenshot)*

## Fluxo de observabilidade

```
Microsserviço (/actuator/prometheus)
        ↓  scrape a cada 1s
    Prometheus :9090
        ↓  datasource
    Grafana :3000
        ↓
    Dashboard (latência, erros, throughput, memória)
```
