# Plataformas, Microsserviços e APIs - Projeto STORE API 

## Grupo 5

1. Cynthia Naoko Yasutake
2. Gustavo Victor Valente de Braga Souza


## Sobre o projeto

O Store API é uma aplicação web feita em arquitetura de microsserviços. Os usuários podem criar pedidos, enquanto os administradores podem criar e deletar produtos. A plataforma é composta por 6 serviços: `Account`, `Auth`, `Gateway`, `Product`, `Order` e `Exchange`

## Repositórios

|Serviço|Repositório|
|-|-|
|Raiz|[Root](https://github.com/Cynthia-Valente-Microsservicos/Root)|
|Product|[Product-Service](https://github.com/Cynthia-Valente-Microsservicos/product-service)|
|Order|[Order-Service](https://github.com/Cynthia-Valente-Microsservicos/order-service)|
|Exchange|[Exchange-Service](https://github.com/Cynthia-Valente-Microsservicos/exchange-service)|
|Account|[Account-Service](https://github.com/Cynthia-Valente-Microsservicos/account-service)|
|Auth|[Auth-Service](https://github.com/Cynthia-Valente-Microsservicos/auth-service)|
|Gateway|[Gateway-Service](https://github.com/Cynthia-Valente-Microsservicos/auth-service)|

## Tarefas Solicitadas
|Tarefa|Status|
|-|-|
|API Gateway|Feito|
|Auth|Feito|
|Account|Feito|
|Exchange|Pendente|
|Bottlenecks|Implementados no Product e no Order|
|AWS|Conta ativa, IAM user configurado|
|EKS|Cluster `eks-store` feito (us-east-2), 2x t3.medium, RDS|
|CI/CD|Com exceção do Exchange, todos as pipelines estão realizadas|
|Load Testing|Pendente|
|Costs & PaaS & SLA|Pendente|
|MkDocs|Em processo|
