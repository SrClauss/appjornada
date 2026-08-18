# 📋 Backlog de Funcionalidades e Métricas

## 1 e 2. Métricas (Faturamento/Km e Ticket Médio)
- [x] **Backend**: Criar endpoints para agregar Faturamento/Km (global vs útil) e Ticket Médio.
- [x] **App (Dashboard da Jornada)**: Exibir Faturamento/Km e Ticket Médio da jornada atual na tela inicial.
- [x] **App (Painel KPI)**: Exibir o acumulado do mês dessas métricas dentro de um novo componente/painel de KPIs para o motorista.

## 3 e 4. Mapa de Calor (Raio de Maior Ticket)
- [x] **Backend**: Criar endpoint que retorna coordenadas GPS (`fase_corrida = EMBARQUE`) ponderadas pelo `valor_reais` da respectiva corrida (GeoJSON).
- [x] **Painel Administrativo (Web)**: Criar uma página dedicada para exibir o Mapa de Calor interativo (Diário, Semanal e Mensal).
- [x] **Painel Administrativo (Web)**: Adicionar recurso para exportar a visualização do mapa como imagem (para apresentações/relatórios).

## 5. Confirmações de Ação e Oficina (UX)
- [x] **App**: Adicionar Modal de Confirmação nos botões de "Abastecimento" e "Manutenção" (para evitar cliques acidentais).
- [x] **App**: Adicionar notificação/modal de confirmação antes de entrar no estado de "Pausa".
- [x] **Backend/App**: Modificar a "Opção B" da Oficina. Deixar o carro na oficina **NÃO deve mais encerrar a jornada**. O status deve ficar em "Manutenção/Pausa Remunerada" até o fechamento automático da carga horária de 8 horas, para não penalizar a meta de horas do motorista.

## 6. Corridas Particulares e Deslocamentos Extraordinários
- [x] **App/Backend**: Reformular o painel de "Corridas Particulares" para suportar dois fluxos manuais durante a jornada:
  - a) Corridas particulares normais (com faturamento).
  - b) Deslocamentos Extraordinários (Socorro, Entrega p/ empresa, Peças) que **não geram faturamento** (exige justificativa).

## 7. Classificação Dinâmica do "KM Vago" (Pós-Jornada)
- [x] **Backend/Painel Administrativo**: Após o fechamento da jornada e processamento do OCR (onde todas as corridas pagas já foram "desenhadas" e demarcadas no mapa), o **gestor da frota** (acessando o painel administrativo) poderá clicar/selecionar esses trechos cinzas no mapa e reclassificá-los.
- [x] **Opções de Classificação do Trecho Vago**:
  - Corrida Particular (esquecida/não registrada)
  - Deslocamento Extraordinário (com justificativa)
  - Deslocamento "A favor da base" (voltando para casa)
  - Deslocamento "Contra a base" (se afastando de casa)

## 8. Desconstrução da Base de Operações Física
- [x] **Backend**: Remover as lógicas que dependem de uma "Base de Operações" fixa da empresa.
- [x] **Backend**: Implementar lógica dinâmica onde a "Base" de uma jornada é definida pelo **primeiro ponto de GPS** registrado ao iniciar aquele turno (geralmente a casa do motorista).

## 9. Novo Sistema de Metas e Dashboard
*Obs: "Meta de KM" foi removida; "Número de corridas diárias" será tratado apenas como métrica, não como meta.*

- [x] **Backend**: Criar estrutura de dados (Tabela de Metas) suportando:
  - [x] Meta de Faturamento / Km (Nova)
  - [x] Meta de Ticket Médio (Nova)
  - [x] Metas de Horas (Diária, Semanal, Mensal/CLT)
  - [x] Metas de Faturamento (Diária, Semanal, Mensal)
- [x] **App**: Criar uma **Tela Separada (Dashboard de Metas e Evolução)** para o motorista acompanhar seu desempenho em relação a essas metas (ex: gráficos, barras de progresso).