# ECR (Amazon Elastic Container Registry)

As imagens Docker de cada microsserviço são publicadas em um registro privado do **ECR**:

```
730335608828.dkr.ecr.us-east-2.amazonaws.com
```

## Repositórios

Há um repositório por serviço, todos com a tag `:latest` apontando para a build mais recente:

| Repositório | Serviço | Stack |
|---|---|---|
| `gateway` | API Gateway | Java / Spring Cloud Gateway |
| `auth` | Autenticação (JWT) | Java / Spring Boot |
| `account` | Contas de usuário | Java / Spring Boot |
| `product` | Catálogo de produtos | Java / Spring Boot |
| `order` | Pedidos | Java / Spring Boot |
| `exchange` | Conversão de moedas | Python / FastAPI |

## Fluxo de publicação

```bash
# 1. autenticar o Docker no registro
aws ecr get-login-password --region us-east-2 \
  | docker login --username AWS --password-stdin 730335608828.dkr.ecr.us-east-2.amazonaws.com

# 2. construir a imagem (plataforma do cluster: linux/amd64)
docker build -t 730335608828.dkr.ecr.us-east-2.amazonaws.com/<service>:latest .

# 3. publicar
docker push 730335608828.dkr.ecr.us-east-2.amazonaws.com/<service>:latest
```

Esse fluxo é executado pelo [CI/CD](ci-cd.md) a cada build. Como os deployments usam `imagePullPolicy: Always` com a tag `:latest`, um `kubectl rollout restart deploy/<service>` faz o cluster puxar a imagem recém-publicada.

> **Multi-arquitetura:** quando a imagem é construída em uma máquina ARM (ex.: Apple Silicon), usa-se `docker buildx build --platform linux/amd64` para garantir compatibilidade com os nós `t3.medium` (x86-64) do cluster.

## Serviços Java com módulos compartilhados

Os serviços Java dependem de uma biblioteca de contratos (ex.: `store:order`, `store:account`). Por isso o build instala o módulo no Maven local **antes** de empacotar o serviço:

```bash
mvn -B -DskipTests clean install   # instala o módulo compartilhado + gera o jar do serviço
```

O `exchange` (Python) não tem essa etapa — sua imagem apenas instala o `requirements.txt`.
