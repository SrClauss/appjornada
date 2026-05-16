# Plano de Implementação — Integração dos Clientes com a API

> **Data:** 16 de maio de 2026  
> **API:** FastAPI + MongoDB (já operacional)  
> **Clientes:** App Flutter (motoristas) + Painel React (administração)

---

## Contexto do Sistema

A API já está operacional com os seguintes recursos:

| Recurso | Endpoints principais | Roles com acesso |
|---|---|---|
| Auth | `POST /auth/login`, `POST /auth/registrar`, `GET /auth/me` | Todos |
| Jornadas | CRUD + `/aberta`, `/fechar`, `/pausas`, `/abastecimentos` | MOTORISTA, GESTOR, ADMIN |
| GPS | `POST /gps/`, `GET /gps/motorista/{id}` | MOTORISTA |
| Veículos | CRUD por placa | GESTOR, ADMIN (escrita); todos (leitura) |
| Usuários/Motoristas | CRUD + perfil CLT, CNH, dados bancários | GESTOR, ADMIN |
| Metas/Bônus | CRUD completo | GESTOR, ADMIN (escrita); todos (leitura) |
| Relatórios | Import CSV Uber/99 + comparativo | GESTOR, ADMIN |
| Manutenções | CRUD completo | GESTOR, ADMIN (escrita); todos (leitura) |
| Uploads | Fotos km, comprovantes, sinistros | Todos autenticados |

**Autenticação:** OAuth2 JWT Bearer Token  
Login via `POST /auth/login` com `Content-Type: application/x-www-form-urlencoded`:
```
username=<email>&password=<senha_ou_pin>
```

**Roles:** `MOTORISTA` · `GESTOR` · `ADMIN`

---

---

# Parte 1 — App Flutter (Motoristas)

O protótipo de referência é um PWA (TypeScript/React em `https://app-jornada.vercel.app`).  
O Flutter substituirá completamente essa implementação.

---

## Fase 1 — Estrutura do Projeto

### Organização de pastas

```
lib/
  core/
    api/
      api_client.dart         # Dio com interceptor JWT
      endpoints.dart          # Constantes de URL
    auth/
      auth_provider.dart      # Gerenciamento de estado de autenticação
      token_storage.dart      # flutter_secure_storage
    errors/
      api_exception.dart      # Mapeamento de erros HTTP
  features/
    auth/
      screens/
        login_screen.dart
      widgets/
        pin_pad.dart
      services/
        auth_service.dart
    home/
      screens/
        home_screen.dart
      widgets/
        jornada_status_card.dart
    jornada/
      screens/
        abrir_jornada_screen.dart
        jornada_ativa_screen.dart
        fechar_jornada_screen.dart
      services/
        jornada_service.dart
    historico/
      screens/
        historico_screen.dart
        jornada_detalhe_screen.dart
    perfil/
      screens/
        perfil_screen.dart
    abastecimento/
      screens/
        abastecimento_screen.dart
  shared/
    widgets/
      app_button.dart
      app_text_field.dart
      loading_overlay.dart
    models/                   # DTOs gerados ou escritos à mão
      user_model.dart
      jornada_model.dart
      pausa_model.dart
      abastecimento_model.dart
      veiculo_model.dart
    utils/
      formatters.dart
      validators.dart
```

### Dependências `pubspec.yaml`

```yaml
dependencies:
  dio: ^5.4.0                        # HTTP client
  flutter_secure_storage: ^9.0.0     # Armazenamento seguro do JWT
  flutter_riverpod: ^2.5.0           # Gerenciamento de estado
  go_router: ^13.0.0                 # Navegação declarativa
  geolocator: ^12.0.0                # GPS do dispositivo
  permission_handler: ^11.0.0        # Permissões (localização, câmera)
  image_picker: ^1.1.0               # Fotos de km e comprovantes
  flutter_background_service: ^5.0.0 # Envio GPS em background
  intl: ^0.19.0                      # Formatação de datas/moedas
  cached_network_image: ^3.3.0       # Cache de imagens de perfil
```

---

## Fase 2 — Camada de Autenticação

### `api_client.dart`

Instância única do Dio configurada com:
- `baseUrl` via variável de ambiente (`--dart-define=API_BASE_URL=...`)
- `connectTimeout` de 10s, `receiveTimeout` de 30s
- **Interceptor de request:** injeta `Authorization: Bearer <token>` em todas as requisições
- **Interceptor de response:** detecta `401` → limpa token → navega para `/login`

### `auth_service.dart`

```dart
// Login → POST /auth/login (form-urlencoded)
Future<void> login(String email, String pin)

// Logout → limpa token do secure storage
Future<void> logout()

// Recupera dados do usuário logado → GET /auth/me
Future<UserModel> getMe()
```

### Tela de Login

Fluxo visual baseado no PRD do protótipo:
1. Logo do app
2. Campo e-mail
3. **PIN Pad customizado** (4 dígitos, layout 3×4 estilo bancário, botões com 60px mínimo)
4. Botão "Entrar"

Ao confirmar: `AuthService.login(email, pin)` → salva token com `flutter_secure_storage` → navega para `/home`.

**Persistência de sessão:** ao inicializar o app (`main.dart`), verificar se token existe e válido via `GET /auth/me`. Se válido → Home; caso contrário → Login.

---

## Fase 3 — Tela Home

Endpoint: `GET /jornadas/aberta`

A tela adapta seu conteúdo ao estado retornado:

| Estado | Ação principal | Ações secundárias |
|---|---|---|
| `null` (sem jornada) | Botão "Abrir Jornada" | — |
| `ABERTA` / `EM_ANDAMENTO` | Botão "Pausar" + Timer rodando | "Registrar Abastecimento", "Encerrar" |
| `EM_PAUSA` | Botão "Retomar" | "Encerrar" |

Cards informativos exibidos sempre:
- Faturamento acumulado do dia (`faturamento.total_dia`)
- Saldo de horas CLT do dia (`saldo_horas_dia`)
- Km rodados no dia (`km.rodados`)

---

## Fase 4 — Módulo Jornada

### 4.1 Abrir Jornada

**Endpoint:** `POST /jornadas/?pin={pin}&localizacao_lat={lat}&localizacao_lon={lon}`

**Body JSON:**
```json
{
  "motorista_id": "<id do usuário logado>",
  "veiculo_id": "<selecionado pelo motorista>",
  "km": { "inicial": 12500.0 }
}
```

**Fluxo da tela:**
1. Busca lista de veículos disponíveis → `GET /veiculos/`
2. Motorista seleciona veículo (dropdown)
3. Informa km inicial (campo numérico)
4. Captura foto do hodômetro → `POST /uploads/` → retorna URL → inclui no campo `fotos.km_inicial_url`
5. Solicita GPS do dispositivo → preenche `localizacao_lat` e `localizacao_lon`
6. Confirma com PIN pad (4 dígitos) → chama endpoint

### 4.2 Pausar Jornada

**Endpoint:** `POST /jornadas/{id}/pausas?tipo={TIPO}`

Tipos disponíveis:
- `PAUSA_MOTORISTA` — pausa livre
- `ALMOCO` — pausa para almoço
- `ABASTECIMENTO` — registra pausa para abastecer

Body opcional:
```json
{ "localizacao_inicio": { "lat": -23.55, "lon": -46.63 } }
```

**Resposta:** retorna a `Jornada` atualizada com status `EM_PAUSA`. Salvar o `id` da pausa criada para o fechamento.

### 4.3 Retomar Jornada

**Endpoint:** `PATCH /jornadas/{id}/pausas/{pausa_id}/fechar`

Body opcional:
```json
{ "localizacao_fim": { "lat": -23.55, "lon": -46.63 } }
```

### 4.4 Encerrar Jornada

**Endpoint:** `PATCH /jornadas/{id}/fechar`

Query params:
```
km_final=12750
faturamento_uber=185.50
faturamento_99=67.00
faturamento_outros=0
foto_km_final_url=<url_do_upload>
localizacao_lat=<lat>
localizacao_lon=<lon>
observacoes=<opcional>
```

**Fluxo da tela:**
1. Campo km final (obrigatório)
2. Foto do hodômetro final → `POST /uploads/`
3. Campos de faturamento: Uber, 99, Outros
4. Campo de observações (opcional)
5. Botão "Encerrar Jornada" → confirmação via `AlertDialog`

### 4.5 Registrar Abastecimento

**Endpoint:** `POST /jornadas/{id}/abastecimentos`

Body JSON:
```json
{
  "km": 12600,
  "valor_gasolina": 80.00,
  "valor_gnv": 0,
  "valor_etanol": 0,
  "foto_comprovante_url": "<url_do_upload>"
}
```

---

## Fase 5 — Rastreamento GPS em Background

Durante jornada com status `ABERTA` ou `EM_ANDAMENTO`, o app envia localização periodicamente.

**Endpoint:** `POST /gps/`

```json
{
  "motorista_id": "<id>",
  "jornada_id": "<id da jornada ativa>",
  "lat": -23.5505,
  "lon": -46.6333,
  "timestamp": "2026-05-16T14:30:00Z"
}
```

**Implementação:**
- Usar `flutter_background_service` para manter o serviço ativo com tela desligada
- Intervalo: **15 segundos** entre pontos
- **Pausar envio** quando `status == EM_PAUSA`
- **Parar serviço** quando jornada for encerrada
- Solicitar permissão `ACCESS_BACKGROUND_LOCATION` (Android) e `Always` (iOS) na abertura da jornada

---

## Fase 6 — Histórico de Jornadas

**Endpoint:** `GET /jornadas/?skip=0&limit=20`

- Lista paginada, ordenada por data decrescente
- Motorista autenticado vê apenas as suas próprias jornadas (filtro automático da API)
- Infinite scroll ou botão "carregar mais" com `skip` incremental
- **Pull-to-refresh** para recarregar do início

**Tela de detalhe** (bottom sheet ou nova rota):
- Horário início/fim e duração total
- Km inicial, final e rodados
- Faturamento breakdown: Uber / 99 / Outros / Total
- Saldo horas CLT do dia
- Lista de pausas (tipo + duração cada)
- Lista de abastecimentos (km + valores)

---

## Fase 7 — Perfil do Motorista

**Endpoint:** `GET /auth/me`

O campo `perfil_motorista` do retorno contém:
- CPF, telefone
- `cnh.vencimento` — exibir badge vermelho se data < hoje
- `dados_bancarios` — banco, agência, conta, CNPJ

**Comportamento:**
- CNH expirada: banner vermelho no topo da tela, mas não bloqueia uso
- Botão "Sair" → `AuthService.logout()` → navega para `/login`

**Edição de dados:** `PATCH /users/{id}` (somente campos permitidos para role MOTORISTA)

---

## Fase 8 — Upload de Arquivos

**Endpoint:** `POST /uploads/` com `multipart/form-data`

Wrapper reutilizável:

```dart
class UploadService {
  Future<String> uploadFoto(File file) async {
    // Retorna a URL pública do arquivo salvo
  }
}
```

Utilizações:
| Contexto | Campo destino na jornada |
|---|---|
| Hodômetro inicial | `fotos.km_inicial_url` |
| Hodômetro final | `fotos.km_final_url` |
| Comprovante Uber | `faturamento.comprovante_uber_url` |
| Comprovante 99 | `faturamento.comprovante_99_url` |
| Comprovante abastecimento | `abastecimentos[i].foto_comprovante_url` |
| Foto CNH | `perfil_motorista.cnh.imagem_url` |

---

## Diagrama de Navegação Flutter

```
Splash
  ├─ token inválido/ausente ──→ Login (email + PIN pad)
  └─ token válido ────────────→ Home
                                  ├─ [Botão] Abrir Jornada ──→ Tela Abrir Jornada
                                  │                              └─ (sucesso) ──→ Jornada Ativa
                                  ├─ Jornada Ativa
                                  │   ├─ [Botão] Pausar ────→ Dialog seleção de tipo
                                  │   ├─ [Botão] Retomar ───→ (direto, sem tela)
                                  │   └─ [Botão] Encerrar ──→ Tela Encerrar Jornada
                                  ├─ [Card] Abastecimento ──→ Tela Abastecimento
                                  │
                                  ── Bottom Navigation Bar ──
                                  ├─ Home (ícone: House)
                                  ├─ Histórico (ícone: ClockCounterClockwise)
                                  │   └─ Tap jornada ────────→ Detalhe Jornada
                                  └─ Perfil (ícone: UserCircle)
```

---

---

# Parte 2 — Painel Administrativo React

O protótipo de referência está em `https://app-jornada-alap.vercel.app`.  
A base do projeto já existe (Vite + React + TypeScript + Tailwind + shadcn/ui).

---

## Fase 1 — Fundação do Projeto

### Dependências adicionais

```bash
npm install axios @tanstack/react-query react-router-dom recharts
npm install react-hook-form zod @hookform/resolvers
npm install date-fns
npm install @tanstack/react-table   # tabelas com sort/filter/pagination
```

### Estrutura de pastas

```
src/
  api/
    client.ts               # Axios com interceptor JWT
    endpoints.ts            # Constantes de URL
    hooks/
      useAuth.ts
      useJornadas.ts
      useMotoristas.ts
      useVeiculos.ts
      useMetas.ts
      useManutencoes.ts
      useRelatorios.ts
  contexts/
    AuthContext.tsx
  pages/
    Login/
      LoginPage.tsx
    Dashboard/
      DashboardPage.tsx
      components/
        KpiCard.tsx
        AlertsTable.tsx
        RevenueChart.tsx
        HoursChart.tsx
        StatusPieChart.tsx
    Motoristas/
      MotoristasPage.tsx
      components/
        MotoristasTable.tsx
        MotoristaDrawer.tsx
        CltProgressBar.tsx
    Jornadas/
      JornadasPage.tsx
      components/
        JornadasTable.tsx
        JornadaModal.tsx
        KmChart.tsx
    Veiculos/
      VeiculosPage.tsx
      components/
        VeiculoCard.tsx
        VeiculoModal.tsx
    Relatorios/
      RelatoriosPage.tsx
      components/
        ComparativoTable.tsx
        PerformanceRadar.tsx
        CsvImporter.tsx
    Metas/
      MetasPage.tsx
      components/
        MetaCard.tsx
        MetaModal.tsx
        BonusChart.tsx
    Manutencoes/
      ManutencoesPage.tsx
      components/
        ManutencoesTable.tsx
        ManutencaoModal.tsx
  components/
    shared/
      Sidebar.tsx
      ProtectedRoute.tsx
      PageHeader.tsx
      DataTable.tsx
      FileUploader.tsx
  lib/
    utils.ts
    formatters.ts
```

### `client.ts` — Axios configurado

```typescript
// Interceptor request: injeta Bearer token
config.headers.Authorization = `Bearer ${localStorage.getItem('token')}`

// Interceptor response: trata 401
// → limpa token → window.location = '/login'
```

### React Query

`QueryClientProvider` no root com:
- `staleTime: 30_000` (30s) para dados de dashboard
- `retry: 1` para evitar múltiplas tentativas em erros de auth

---

## Fase 2 — Autenticação

**Endpoint:** `POST /auth/login`  
Body: `application/x-www-form-urlencoded` com `username` e `password`

**`AuthContext`** expõe:
```typescript
interface AuthContextType {
  user: UserPublic | null
  isAuthenticated: boolean
  login: (email: string, senha: string) => Promise<void>
  logout: () => void
}
```

**Fluxo:**
1. Usuário preenche e-mail + senha no `LoginPage`
2. `AuthContext.login()` → `POST /auth/login` → salva token em `localStorage`
3. `GET /auth/me` → preenche dados do usuário no contexto
4. `ProtectedRoute` redireciona para `/login` se `!isAuthenticated`

---

## Fase 3 — Dashboard

### KPIs (compostos de múltiplas queries paralelas)

| Card | Fonte de dados | Cálculo |
|---|---|---|
| Motoristas ativos hoje | `GET /jornadas/?data=hoje` | Contar `motorista_id` únicos com status `ABERTA` ou `EM_ANDAMENTO` |
| KM total do dia | `GET /jornadas/?data=hoje` | Somar `km.rodados` das jornadas encerradas |
| Faturamento do dia | `GET /jornadas/?data=hoje` | Somar `faturamento.total_dia` |
| Alertas ativos | Jornadas abertas há > 12h ou sem GPS recente | Flag manual |

### Gráficos (Recharts)

- **`BarChart` — Faturamento semanal:** `GET /jornadas/?data=X` para os últimos 7 dias, agrupando por motorista
- **`LineChart` — Horas CLT:** horas acumuladas no mês vs. meta de 220h, por motorista (calculado no frontend)
- **`PieChart` — Status das jornadas:** distribuição de `ABERTA` / `EM_ANDAMENTO` / `EM_PAUSA` / `ENCERRADA` no dia

### Tabela de alertas

Linha por jornada que atende qualquer condição:
- Status `ABERTA` com horário de início há mais de 12h
- Status `EM_PAUSA` há mais de 2h
- Faturamento `total_dia == 0` em jornada encerrada

---

## Fase 4 — Gestão de Motoristas

### Listagem

**Endpoint:** `GET /users/` (filtrar role = MOTORISTA no frontend ou query param)

Tabela com colunas: nome, e-mail, status CNH, horas acumuladas no mês, ação "Ver detalhes".  
Filtros: busca por nome, filtro por status CNH (válida/expirada).

### Cadastro

**Endpoint:** `POST /auth/registrar`

```json
{
  "nome": "João Silva",
  "email": "joao@empresa.com",
  "senha": "1234",
  "role": "MOTORISTA",
  "perfil_motorista": {
    "cpf": "000.000.000-00",
    "telefone": "11 99999-9999",
    "cnh": { "vencimento": "2027-03-15" }
  }
}
```

### Drawer de Perfil (`Sheet` do shadcn)

Abas:
1. **Dados Pessoais** — nome, CPF, telefone, `PATCH /users/{id}` ao salvar
2. **CNH** — data de vencimento com barra de alerta visual (verde/amarelo/vermelho por prazo)
3. **Dados Bancários** — banco, agência, conta, CNPJ
4. **Horas CLT** — `ProgressBar` com total horas do mês vs. 220h (agrega `jornadas`)
5. **Histórico** — últimas 10 jornadas do motorista (`GET /jornadas/?motorista_id=X&limit=10`)
6. **Bônus** — bônus acumulado no mês (`bonus_acumulado_mes` das jornadas)

---

## Fase 5 — Jornadas

### Listagem com filtros

**Endpoint:** `GET /jornadas/?data=X&motorista_id=X&status_filtro=X&skip=0&limit=50`

Filtros na UI:
- Date picker (intervalo de datas)
- Select de motorista
- Select de status

Gráfico acima da tabela: `BarChart` de km rodados por jornada no período filtrado.

### Modal de Detalhes (`Dialog` do shadcn)

Seções:
- **Cabeçalho:** data, motorista, veículo, status com badge colorido
- **Horários:** início, fim, duração total, saldo CLT
- **Quilometragem:** inicial, final, rodados, km morta
- **Faturamento:** Uber / 99 / Outros / Total, com links para comprovantes
- **Pausas:** timeline visual com tipo e duração de cada pausa
- **Abastecimentos:** tabela com km, valores por tipo de combustível
- **GPS:** placeholder de mapa com coordenadas inicial e final

---

## Fase 6 — Veículos, Manutenções e Metas

### Veículos

| Operação | Endpoint |
|---|---|
| Listar | `GET /veiculos/` |
| Criar | `POST /veiculos/` |
| Editar | `PATCH /veiculos/{placa}` |

**Grid de cards** com: placa, modelo, status (badge colorido), alertas de IPVA/inspeção expirados ou próximos (60d/30d → amarelo/vermelho).  
Barra de status rápida no topo: contagem por status.

### Manutenções

| Operação | Endpoint |
|---|---|
| Listar | `GET /manutencoes/` + filtro por `veiculo_id` |
| Criar | `POST /manutencoes/` |
| Atualizar status | `PATCH /manutencoes/{id}` |

KPIs no topo da página:
- Custo total do mês
- Manutenções em andamento
- Próximas revisões por km (alerta a 500km do intervalo)

### Metas e Bônus

| Operação | Endpoint |
|---|---|
| Listar | `GET /metas/` |
| Criar | `POST /metas/` |
| Editar | `PATCH /metas/{id}` |
| Excluir | `DELETE /metas/{id}` |

Modal "Nova Meta" com campos: tipo (faturamento/km/horas), escopo (individual/equipe), motorista_id (se individual), thresholds, valor do bônus.

`BarChart` de bônus acumulado por motorista no mês corrente (agrega `bonus_acumulado_mes` das jornadas).

---

## Fase 7 — Relatórios

### Aba 1 — Comparativo de Plataformas

**Endpoints:**
1. `POST /uploads/` — enviar arquivo CSV
2. `POST /relatorios/comparativo` — processar comparativo

**Fluxo:**
1. Componente `CsvImporter` — drag & drop ou clique para selecionar CSV (Uber ou 99)
2. Select de motorista e intervalo de datas
3. `POST /uploads/` com o arquivo → obtém URL
4. `POST /relatorios/comparativo` com referência ao arquivo

**Tabela de resultados:**
| Coluna | Fonte |
|---|---|
| Data | Jornada |
| KM jornada | `km.rodados` |
| KM plataforma | CSV (somente 99; Uber não fornece) |
| Delta KM % | Calculado |
| Fat. declarado | `faturamento.total_dia` |
| Fat. plataforma | CSV |
| Delta Fat. % | Calculado |
| Status | 🟢 OK / 🔴 Alerta (> 20%) |

### Aba 2 — Performance por Motorista

Radar chart por motorista normalizado (0–100):
- Faturamento médio/dia
- KM médio/dia
- Horas trabalhadas vs. CLT
- Taxa de cumprimento de metas

Dados calculados no frontend a partir de `GET /jornadas/?motorista_id=X`.

### Aba 3 — Exportação

Botão "Exportar CSV" gera arquivo client-side (sem chamada à API) com os dados da tabela de jornadas atualmente filtrada.

---

## Rotas React Router

```
/login
/                           → Dashboard
/motoristas                 → Tabela de motoristas + Drawer de perfil
/jornadas                   → Tabela de jornadas + Modal de detalhes
/veiculos                   → Grid de veículos + Modais CRUD
/manutencoes                → Tabela de manutenções + Modais CRUD
/metas                      → Grid de metas + Modal de criação/edição
/relatorios                 → Tabs: Comparativo / Performance / Exportação
```

Todas as rotas exceto `/login` são protegidas por `ProtectedRoute`.  
Roles `GESTOR` e `ADMIN` têm acesso total. `MOTORISTA` não deve acessar o painel.

---

---

# Considerações de Integração Comuns

## CORS

Verificar `backend/app/main.py` para garantir que `CORSMiddleware` está configurado com:
- Origens permitidas em produção: domínio do painel React
- Em desenvolvimento: `http://localhost:5173` (Vite)

## Variáveis de Ambiente

**Flutter** — via `--dart-define` (ou pacote `envied` para type-safety):
```
API_BASE_URL=https://api.suaempresa.com
```

**React** — `.env.local`:
```
VITE_API_BASE_URL=https://api.suaempresa.com
```

## Tratamento de Erros HTTP

Ambos os clientes devem mapear os seguintes status:

| HTTP | Ação |
|---|---|
| `401` | Limpar token + redirecionar para login |
| `403` | Exibir mensagem "Sem permissão" |
| `409` | Exibir mensagem de conflito (ex: "Jornada já aberta hoje") |
| `422` | Exibir erros de validação por campo |
| `500` | Toast genérico de erro do servidor |

## Segurança

- **Flutter:** usar `flutter_secure_storage` (armazenamento encriptado pelo keystore da plataforma, nunca `SharedPreferences` para tokens)
- **React:** em produção, preferir `httpOnly cookie` ao `localStorage` para mitigar XSS; adicionar `Content-Security-Policy` no servidor
- O PIN de 4 dígitos é enviado como `password` no fluxo OAuth2 — **HTTPS obrigatório** em qualquer ambiente além do desenvolvimento local

## Ordem de Implementação Sugerida

```
[API] ✅ Pronta

[React — Painel]
  1. Fundação (client, router, auth context)
  2. Login
  3. Motoristas (CRUD completo)
  4. Jornadas (leitura + detalhes)
  5. Dashboard (KPIs + gráficos)
  6. Veículos + Manutenções
  7. Metas e Bônus
  8. Relatórios (CSV import + comparativo)

[Flutter — App]
  1. Projeto + estrutura + auth (login + PIN pad)
  2. Home + integração jornada ativa
  3. Abrir / pausar / retomar / encerrar jornada
  4. Upload de fotos
  5. GPS background service
  6. Histórico de jornadas
  7. Abastecimento
  8. Perfil do motorista
```
