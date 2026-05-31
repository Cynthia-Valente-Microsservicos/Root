# Controle de acesso baseado em papéis (RBAC)

## Identificação do problema

Sem controle de acesso granular, qualquer usuário autenticado conseguia chamar **qualquer endpoint** da API — inclusive operações destrutivas como criação e remoção de produtos. O sistema precisava distinguir usuários comuns (`USER`) de administradores (`ADMIN`) sem consultar o banco de dados a cada requisição.

## Solução

A solução foi embutir o papel do usuário diretamente no token JWT e propagá-lo como header HTTP até os microsserviços. Isso elimina uma consulta extra ao banco a cada request, já que a informação já viaja dentro do token assinado.

### 1. Definição dos papéis

O enum `Role` define os dois níveis de acesso possíveis:

```java
// api/account/src/main/java/store/account/Role.java
public enum Role {
    USER, ADMIN
}
```

O papel é persistido junto à conta no banco de dados:

```java
// api/account-service/src/main/java/store/account/AccountModel.java
@Column(name = "role")
private Role role;
```

### 2. Role embutido no JWT

Na geração do token, o campo `role` é adicionado como claim:

```java
// api/auth-service/src/main/java/store/auth/JwtService.java
String jwt = Jwts.builder()
    .claims(Map.of(
        "email", account.email(),
        "role",  account.role()   // <- claim de papel
    ))
    .signWith(getKey())
    // ...
    .compact();
```

E na leitura do token:

```java
// api/auth-service/src/main/java/store/auth/JwtService.java
public String getRole(String jwt) {
    JwtParser parser = Jwts.parser().verifyWith(getKey()).build();
    Claims claims = parser.parseSignedClaims(jwt).getPayload();
    return (String) claims.get("role");
}
```

### 3. Gateway propaga o papel como header

O `AuthorizationFilter` valida o JWT chamando o auth-service e, ao receber `id-account` e `role`, injeta ambos como headers HTTP na requisição encaminhada:

```java
// api/gateway-service/src/main/java/store/gateway/security/AuthorizationFilter.java
private ServerWebExchange updateRequest(ServerWebExchange exchange,
        String idAccount, String role, String jwt) {
    return exchange.mutate()
        .request(exchange.getRequest().mutate()
            .header("id-account", idAccount)
            .header("role", role)               // <- papel propagado
            .header("Authorization", "Bearer" + jwt)
            .build()
        ).build();
}
```

Rotas abertas (registro e login) são ignoradas pelo filtro:

```java
// api/gateway-service/src/main/java/store/gateway/security/RouterValidator.java
private List<String> openApiEndpoints = List.of(
    "POST /auth/register",
    "POST /auth/login"
);
```

### 4. Microsserviço aplica o controle de acesso

O `product-service` lê o header `role` injetado pelo gateway e rejeita com `403 Forbidden` qualquer tentativa de usuários não-administradores:

```java
// api/product-service/src/main/java/store/product/ProductResource.java
@Override
public ResponseEntity<Void> create(@RequestBody ProductIn in,
        @RequestHeader("role") String role) {
    if (role == null || !role.contains("ADMIN")) {
        return ResponseEntity.status(HttpStatus.FORBIDDEN).build();
    }
    // ...
}

@Override
public ResponseEntity<Void> delete(@PathVariable("id") String id,
        @RequestHeader("role") String role) {
    if (role == null || !role.contains("ADMIN")) {
        return ResponseEntity.status(HttpStatus.FORBIDDEN).build();
    }
    // ...
}
```

## Fluxo completo

```
Cliente → [cookie JWT] → Gateway (AuthorizationFilter)
                              ↓ POST /auth/solve
                         Auth Service (JwtService)
                              ↓ {id-account, role}
                         Gateway injeta headers
                              ↓ header: role=ADMIN|USER
                         Microsserviço (ProductResource)
                              ↓ verifica role → 200 ou 403
```
