# Cacheing (Redis)

## Identificação do problema

O `product-service` consultava o PostgreSQL a cada requisição de leitura de produto. Em cenários de alta frequência — como listagem de detalhes de um produto popular — isso gerava carga desnecessária no banco e latência perceptível, já que os dados raramente mudam entre uma leitura e outra.

## Solução

Foi adicionado um cache Redis com TTL de 5 minutos usando Spring Cache. Leituras por `id` passam a ser servidas da memória; o banco só é consultado quando o item não está em cache. Escritas e deleções invalidam ou atualizam a entrada correspondente, mantendo a consistência.

### 1. Habilitação do cache na aplicação

```java
// api/product-service/src/main/java/store/product/ProductApplication.java
@SpringBootApplication
@EnableCaching                // <- ativa o mecanismo de cache do Spring
public class ProductApplication {
    public static void main(String[] args) {
        SpringApplication.run(ProductApplication.class, args);
    }
}
```

### 2. Configuração do Redis

O `RedisConfig` define o serializador JSON e o TTL global de 5 minutos para todas as entradas:

```java
// api/product-service/src/main/java/store/product/RedisConfig.java
@Configuration
public class RedisConfig {

    @Bean
    public RedisCacheConfiguration cacheConfiguration() {
        ObjectMapper objectMapper = new ObjectMapper();
        objectMapper.setVisibility(PropertyAccessor.FIELD, Visibility.ANY);

        return RedisCacheConfiguration.defaultCacheConfig()
            .serializeValuesWith(
                RedisSerializationContext.SerializationPair.fromSerializer(
                    new GenericJackson2JsonRedisSerializer(objectMapper)
                )
            )
            .entryTtl(Duration.ofMinutes(5))   // <- expiração automática
            .disableCachingNullValues();        // <- evita cachear "não encontrado"
    }
}
```

### 3. Anotações de cache no serviço

```java
// api/product-service/src/main/java/store/product/ProductService.java

// Leitura: retorna do cache se existir; caso contrário consulta o banco
// e armazena o resultado automaticamente
@Cacheable(value = "products", key = "#id", unless = "#result == null")
public Product findById(String id) {
    return productRepository.findById(id)
        .map(ProductModel::to)
        .orElse(null);
}

// Criação: salva no banco e já insere no cache com a chave do novo id
@CachePut(value = "products", key = "#result.id")
public Product create(Product product) {
    return productRepository.save(new ProductModel(product)).to();
}

// Deleção: remove do banco e expulsa a entrada do cache
@CacheEvict(value = "products", key = "#id")
public void delete(String id) {
    productRepository.deleteById(id);
}
```

### 4. Redis declarado no compose

```yaml
# api/compose.yaml
redis:
  image: redis:7-alpine
  hostname: redis
  ports:
    - 6379:6379
  volumes:
    - redis_data:/data
  command: redis-server --appendonly yes   # <- persistência em disco

# product-service depende do redis
product:
  depends_on:
    - db
    - redis
    - kafka
```

## Fluxo de leitura com cache

```
GET /product/{id}
        ↓
  ProductService.findById
        ↓
  Redis hit? ──→ sim ──→ retorna Product (sem tocar no banco)
        ↓ não
  PostgreSQL query
        ↓
  armazena em Redis (TTL 5 min)
        ↓
  retorna Product
```
