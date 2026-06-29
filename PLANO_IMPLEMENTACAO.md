# Plano de Implementação — Integração dos Clientes com a API

> **Data:** 16 de maio de 2026  
> **API:** FastAPI + MongoDB (já operacional)  
> **Clientes:** App Flutter (motoristas) + Painel React (administração)

## Repositórios de Referência

| Projeto | Repositório GitHub | Deploy do Protótipo |
|---|---|---|
| App do Motorista (Flutter) | [SrClauss/app-jornada](https://github.com/SrClauss/app-jornada) | [app-jornada.vercel.app](https://app-jornada.vercel.app) |
| Painel Administrativo (React) | [SrClauss/app-jornada-painel-d](https://github.com/SrClauss/app-jornada-painel-d) | [app-jornada-alap.vercel.app](https://app-jornada-alap.vercel.app) |

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

## Visão Geral das 20 Fases

| # | Título | Domínio |
|---|---|---|
| 1 | Infraestrutura Comum e CORS | Ambos |
| 2 | Flutter — Estrutura do Projeto | Flutter |
| 3 | Flutter — Cliente HTTP e Modelos | Flutter |
| 4 | Flutter — Autenticação e Tela de Login | Flutter |
| 5 | Flutter — Tela Home | Flutter |
| 6 | Flutter — Abrir Jornada | Flutter |
| 7 | Flutter — Jornada Ativa (Pausar / Retomar) | Flutter |
| 8 | Flutter — Encerrar Jornada | Flutter |
| 9 | Flutter — Abastecimento | Flutter |
| 10 | Flutter — Upload de Arquivos | Flutter |
| 11 | Flutter — Rastreamento GPS em Background | Flutter |
| 12 | Flutter — Histórico de Jornadas | Flutter |
| 13 | Flutter — Perfil do Motorista | Flutter |
| 14 | React — Fundação do Projeto | React |
| 15 | React — Autenticação e Roteamento | React |
| 16 | React — Dashboard | React |
| 17 | React — Gestão de Motoristas | React |
| 18 | React — Jornadas | React |
| 19 | React — Veículos, Manutenções e Metas | React |
| 20 | React — Relatórios | React |

---

---

# Fase 1 — Infraestrutura Comum e CORS

**Domínio:** Ambos os clientes  
**Pré-requisito:** nenhum  
**Entregável:** ambiente de desenvolvimento funcional com API acessível

### 1.1 CORS no Backend

Verificar `backend/app/main.py` e garantir que `CORSMiddleware` esteja configurado:

```python
# Origens a liberar
# Desenvolvimento: http://localhost:5173 (Vite) e http://localhost:3000
# Produção: domínio do painel React e bundle do Flutter (origem nativa)
```

### 1.2 Variáveis de Ambiente

**Flutter** — via `--dart-define` (ou pacote `envied` para type-safety):
```
API_BASE_URL=https://api.suaempresa.com
```

**React** — `.env.local` (nunca commitar valores reais):
```
VITE_API_BASE_URL=https://api.suaempresa.com
```

### 1.3 Tratamento de Erros HTTP Padrão

Ambos os clientes devem mapear os seguintes status de forma centralizada:

| HTTP | Ação |
|---|---|
| `401` | Limpar token + redirecionar para login |
| `403` | Exibir mensagem "Sem permissão" |
| `409` | Exibir mensagem de conflito (ex: "Jornada já aberta hoje") |
| `422` | Exibir erros de validação por campo |
| `500` | Toast genérico de erro do servidor |

### 1.4 Segurança

- **Flutter:** usar `flutter_secure_storage` (keystore da plataforma — nunca `SharedPreferences` para tokens)
- **React:** em produção, preferir `httpOnly cookie` ao `localStorage` para mitigar XSS; adicionar `Content-Security-Policy` no servidor
- O PIN de 4 dígitos é enviado como `password` no fluxo OAuth2 — **HTTPS obrigatório** em qualquer ambiente além do desenvolvimento local

---

---

# Parte 1 — App Flutter (Motoristas)

> **Repositório do protótipo:** [github.com/SrClauss/app-jornada](https://github.com/SrClauss/app-jornada)  
> **Deploy do protótipo:** [app-jornada.vercel.app](https://app-jornada.vercel.app)  
> **Stack atual do protótipo:** PWA (TypeScript + React + Vite + shadcn/ui + Tailwind)  
> O Flutter substituirá completamente essa implementação.

---

# Fase 2 — Flutter — Estrutura do Projeto

**Pré-requisito:** Flutter SDK instalado  
**Entregável:** projeto criado, dependências instaladas, estrutura de pastas definida

### 2.1 Organização de Pastas

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
    models/
      user_model.dart
      jornada_model.dart
      pausa_model.dart
      abastecimento_model.dart
      veiculo_model.dart
    utils/
      formatters.dart
      validators.dart
```

### 2.2 Dependências `pubspec.yaml`

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

### 2.3 Diagrama de Navegação

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

# Fase 3 — Flutter — Cliente HTTP e Modelos

**Pré-requisito:** Fase 2  
**Entregável:** `api_client.dart` funcional e modelos Dart correspondentes aos schemas da API

### 3.1 `api_client.dart`

Instância única do Dio configurada com:
- `baseUrl` via variável de ambiente (`--dart-define=API_BASE_URL=...`)
- `connectTimeout` de 10s, `receiveTimeout` de 30s
- **Interceptor de request:** injeta `Authorization: Bearer <token>` em todas as requisições
- **Interceptor de response:** detecta `401` → limpa token → navega para `/login`; mapeia demais status conforme Fase 1.3

### 3.2 `endpoints.dart`

```dart
class Endpoints {
  static const login           = '/auth/login';
  static const me              = '/auth/me';
  static const jornadas        = '/jornadas';
  static const jornadaAberta   = '/jornadas/aberta';
  static const veiculos        = '/veiculos';
  static const gps             = '/gps';
  static const uploads         = '/uploads';
  static const users           = '/users';
}
```

### 3.3 Modelos Dart

Criar classes com `fromJson` / `toJson` para cada entidade da API:

| Modelo | Campos principais |
|---|---|
| `UserModel` | `id`, `nome`, `email`, `role`, `perfilMotorista` |
| `JornadaModel` | `id`, `status`, `data`, `km`, `horario`, `faturamento`, `pausas`, `abastecimentos` |
| `PausaModel` | `id`, `tipo`, `inicio`, `fim`, `duracaoSegundos` |
| `AbastecimentoModel` | `id`, `km`, `valorGasolina`, `valorGnv`, `valorEtanol`, `fotoComprovante` |
| `VeiculoModel` | `idPlaca`, `modelo`, `ano`, `status` |

---

# Fase 4 — Flutter — Autenticação e Tela de Login

**Pré-requisito:** Fase 3  
**Entregável:** fluxo de login completo com persistência de sessão

### 4.1 `auth_service.dart`

```dart
// Login → POST /auth/login (form-urlencoded)
Future<void> login(String email, String pin)

// Logout → limpa token do secure storage
Future<void> logout()

// Recupera dados do usuário logado → GET /auth/me
Future<UserModel> getMe()
```

### 4.2 `token_storage.dart`

Wrapper sobre `flutter_secure_storage`:
- `saveToken(String token)`
- `readToken() → Future<String?>`
- `deleteToken()`

### 4.3 Tela de Login

Fluxo visual baseado no PRD do protótipo:
1. Logo do app
2. Campo e-mail
3. **PIN Pad customizado** — widget `PinPad` com layout 3×4 estilo bancário, botões com 60px mínimo, feedback visual por dígito preenchido
4. Botão "Entrar"

Ao confirmar: `AuthService.login(email, pin)` → salva token → navega para `/home`.

### 4.4 Persistência de Sessão

Em `main.dart`, antes de renderizar a tela inicial:
1. `TokenStorage.readToken()` — se nulo, redireciona para `/login`
2. `AuthService.getMe()` — se retornar 401, redireciona para `/login`; se OK, prossegue para `/home`

---

# Fase 5 — Flutter — Tela Home

**Pré-requisito:** Fase 4  
**Entregável:** tela Home adaptativa ao estado da jornada

**Endpoint:** `GET /jornadas/aberta`

A tela adapta seu conteúdo ao estado retornado:

| Estado | Ação principal | Ações secundárias |
|---|---|---|
| `null` (sem jornada) | Botão "Abrir Jornada" | — |
| `ABERTA` / `EM_ANDAMENTO` | Timer rodando + Botão "Pausar" | "Registrar Abastecimento", "Encerrar" |
| `EM_PAUSA` | Botão "Retomar" | "Encerrar" |

Cards informativos exibidos em qualquer estado:
- Faturamento acumulado do dia (`faturamento.total_dia`)
- Saldo de horas CLT do dia (`saldo_horas_dia`)
- Km rodados no dia (`km.rodados`)

O timer de jornada ativa é calculado localmente a partir de `horario.inicio` e atualizado a cada segundo com `Timer.periodic`.

---

# Fase 6 — Flutter — Abrir Jornada

**Pré-requisito:** Fase 5  
**Entregável:** tela de abertura de jornada integrada à API

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
1. Carrega veículos disponíveis → `GET /veiculos/` → exibe em dropdown
2. Motorista seleciona veículo
3. Informa km inicial (campo numérico, obrigatório)
4. Captura foto do hodômetro via `image_picker` → `POST /uploads/` → obtém URL → inclui em `fotos.km_inicial_url`
5. Solicita GPS do dispositivo (`geolocator`) → preenche query params `localizacao_lat` e `localizacao_lon`
6. Confirma com PIN pad → chama endpoint
7. Em caso de sucesso: navega para `JornadaAtivaScreen`; em caso de `409`: exibe alerta "Jornada já aberta hoje"

---

# Fase 7 — Flutter — Jornada Ativa (Pausar / Retomar)

**Pré-requisito:** Fase 6  
**Entregável:** controles de pausa e retomada funcionais na tela de jornada ativa

### 7.1 Pausar

**Endpoint:** `POST /jornadas/{id}/pausas?tipo={TIPO}`

Tipos disponíveis:
- `PAUSA_MOTORISTA` — pausa livre
- `ALMOCO` — pausa para almoço
- `ABASTECIMENTO` — pausa para abastecer

**Fluxo:**
1. Botão "Pausar" → abre `AlertDialog` com seleção de tipo
2. Obtém GPS atual (opcional)
3. Chama endpoint com `tipo` e `localizacao_inicio` (se disponível)
4. Resposta retorna jornada com status `EM_PAUSA` e a pausa criada — salva `pausa.id` no estado local para uso no retomar
5. Para o serviço de GPS (Fase 11)

### 7.2 Retomar

**Endpoint:** `PATCH /jornadas/{id}/pausas/{pausa_id}/fechar`

Body opcional:
```json
{ "localizacao_fim": { "lat": -23.55, "lon": -46.63 } }
```

Após retomar: reinicia o serviço de GPS.

---

# Fase 8 — Flutter — Encerrar Jornada

**Pré-requisito:** Fase 7  
**Entregável:** fluxo completo de encerramento com registro de faturamento

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
observacoes=<texto_opcional>
```

**Fluxo da tela:**
1. Campo km final (obrigatório, validar que km_final > km_inicial)
2. Botão para capturar foto do hodômetro final → `POST /uploads/`
3. Campos de faturamento: Uber, 99, Outros (todos numéricos, permitem zero)
4. Campo de observações (opcional)
5. Botão "Encerrar Jornada" → `AlertDialog` de confirmação → chama endpoint
6. Em caso de sucesso: para serviço GPS, limpa estado da jornada ativa, navega para Home

---

# Fase 9 — Flutter — Abastecimento

**Pré-requisito:** Fase 6 (requer jornada ativa)  
**Entregável:** tela de registro de abastecimento integrada

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

**Fluxo da tela:**
1. Acessível via card na Home ou durante pausa do tipo `ABASTECIMENTO`
2. Campo km atual (pré-preenchido com `km.inicial` da jornada)
3. Campos de valor por tipo de combustível (gasolina, GNV, etanol — somar os preenchidos)
4. Foto do comprovante → `POST /uploads/` (opcional, mas recomendado)
5. Salvar → retorna para tela anterior

---

# Fase 10 — Flutter — Upload de Arquivos

**Pré-requisito:** Fase 3  
**Entregável:** `UploadService` reutilizável em todas as features

**Endpoint:** `POST /uploads/` com `multipart/form-data`

```dart
class UploadService {
  Future<String> uploadFoto(File file) async {
    // Retorna a URL pública do arquivo salvo
  }
}
```

Mapeamento de utilizações:

| Contexto | Campo destino |
|---|---|
| Hodômetro inicial | `fotos.km_inicial_url` |
| Hodômetro final | `fotos.km_final_url` |
| Comprovante Uber | `faturamento.comprovante_uber_url` |
| Comprovante 99 | `faturamento.comprovante_99_url` |
| Comprovante abastecimento | `abastecimentos[i].foto_comprovante_url` |
| Foto CNH | `perfil_motorista.cnh.imagem_url` |

Solicitar permissão de câmera (`permission_handler`) antes do primeiro uso. Exibir preview da imagem antes de confirmar o upload.

---

# Fase 11 — Flutter — Rastreamento GPS em Background

**Pré-requisito:** Fase 6  
**Entregável:** serviço GPS ativo durante toda a jornada, mesmo com app em background

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
- Usar `flutter_background_service` para manter o isolate ativo com tela desligada
- Intervalo: **15 segundos** entre pontos
- **Pausar envio** quando `status == EM_PAUSA` (Fase 7)
- **Parar serviço** ao encerrar jornada (Fase 8)
- Solicitar permissão `ACCESS_BACKGROUND_LOCATION` (Android) e modo `Always` (iOS) no momento de abertura da jornada — explicar ao usuário o motivo antes de solicitar
- **Alerta de Inatividade Configurável:** O backend monitora a imobilidade e emite alertas com base no tempo limiar parametrizado por motorista (`perfil_motorista.limiar_inatividade_minutos`).
- **Notificação no Painel:** Os alertas gerados são consumidos no dashboard para notificar o gestor em tempo real.

---

# Fase 12 — Flutter — Histórico de Jornadas

**Pré-requisito:** Fase 4  
**Entregável:** tela de histórico com paginação e detalhe completo

**Endpoint:** `GET /jornadas/?skip=0&limit=20`

A API filtra automaticamente pelo motorista autenticado quando `role == MOTORISTA`.

**Tela de lista:**
- Ordenada por data decrescente
- Infinite scroll: incrementa `skip` a cada página
- Pull-to-refresh: reinicia com `skip=0`
- Cada item exibe: data, status (badge), km rodados, faturamento total

**Bottom sheet de detalhe** (abre ao tocar na linha):
- Horário início/fim e duração total
- Km inicial, final e rodados
- Faturamento breakdown: Uber / 99 / Outros / Total
- Saldo horas CLT do dia (`saldo_horas_dia`)
- Lista de pausas com tipo e duração
- Lista de abastecimentos com km e valores

---

# Fase 13 — Flutter — Perfil do Motorista

**Pré-requisito:** Fase 4  
**Entregável:** tela de perfil com alertas de CNH e fluxo de logout

**Endpoint:** `GET /auth/me`

O campo `perfil_motorista` contém:
- `cpf`, `telefone`
- `cnh.vencimento` — comparar com data atual; se expirada, exibir banner vermelho proeminente (não bloqueia uso)
- `dados_bancarios` — banco, agência, conta, CNPJ

**Edição de dados:** `PATCH /users/{id}` com somente os campos permitidos para `role == MOTORISTA`.

**Logout:** `AuthService.logout()` → `TokenStorage.deleteToken()` → navega para `/login` e limpa stack de navegação.

---

---

# Parte 2 — Painel Administrativo React

> **Repositório:** [github.com/SrClauss/app-jornada-painel-d](https://github.com/SrClauss/app-jornada-painel-d)  
> **Deploy do protótipo:** [app-jornada-alap.vercel.app](https://app-jornada-alap.vercel.app)  
> **Stack:** Vite + React + TypeScript + Tailwind + shadcn/ui (scaffold já gerado)

---

# Fase 14 — React — Fundação do Projeto

**Pré-requisito:** Fase 1  
**Entregável:** projeto configurado com cliente HTTP, React Query e estrutura de pastas

### 14.1 Dependências

```bash
npm install axios @tanstack/react-query react-router-dom recharts
npm install react-hook-form zod @hookform/resolvers
npm install date-fns @tanstack/react-table
```

### 14.2 Estrutura de Pastas

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
    Dashboard/
    Motoristas/
    Jornadas/
    Veiculos/
    Relatorios/
    Metas/
    Manutencoes/
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

### 14.3 `client.ts`

```typescript
// Interceptor request: injeta Bearer token
config.headers.Authorization = `Bearer ${localStorage.getItem('token')}`

// Interceptor response:
// 401 → limpa token → window.location = '/login'
// outros erros → mapear conforme Fase 1.3
```

### 14.4 React Query

`QueryClientProvider` no root com:
- `staleTime: 30_000` (30s) para dados de dashboard
- `retry: 1` para evitar múltiplas tentativas em erros de autenticação

---

# Fase 15 — React — Autenticação e Roteamento

**Pré-requisito:** Fase 14  
**Entregável:** login funcional, contexto de auth e rotas protegidas

### 15.1 `AuthContext`

```typescript
interface AuthContextType {
  user: UserPublic | null
  isAuthenticated: boolean
  login: (email: string, senha: string) => Promise<void>
  logout: () => void
}
```

**Fluxo de login:**
1. `POST /auth/login` (body: `application/x-www-form-urlencoded`)
2. Salva token em `localStorage`
3. `GET /auth/me` → preenche `user` no contexto

### 15.2 `ProtectedRoute`

Redireciona para `/login` se `!isAuthenticated`. `MOTORISTA` não deve acessar o painel — verificar role após login e redirecionar com mensagem.

### 15.3 Rotas React Router

```
/login
/                           → Dashboard
/motoristas                 → Gestão de motoristas
/jornadas                   → Listagem de jornadas
/veiculos                   → Frota de veículos
/manutencoes                → Manutenções
/metas                      → Metas e bônus
/relatorios                 → Relatórios
```

Todas as rotas exceto `/login` são envolvidas por `ProtectedRoute`.

---

# Fase 16 — React — Dashboard

**Pré-requisito:** Fase 15  
**Entregável:** página inicial com KPIs, gráficos e tabela de alertas

### 16.1 KPIs (queries paralelas)

| Card | Fonte | Cálculo |
|---|---|---|
| Motoristas ativos | `GET /jornadas/?data=hoje` | Contar `motorista_id` únicos com status `ABERTA` ou `EM_ANDAMENTO` |
| KM total do dia | `GET /jornadas/?data=hoje` | Somar `km.rodados` das jornadas encerradas |
| Faturamento do dia | `GET /jornadas/?data=hoje` | Somar `faturamento.total_dia` |
| Alertas | Derivado da mesma query | Jornadas abertas > 12h ou sem GPS |

### 16.2 Gráficos (Recharts)

- **`BarChart`** — Faturamento diário dos últimos 7 dias, agrupado por motorista
- **`LineChart`** — Horas acumuladas no mês vs. meta CLT de 220h, por motorista
- **`PieChart`** — Distribuição de status das jornadas do dia (`ABERTA` / `EM_ANDAMENTO` / `EM_PAUSA` / `ENCERRADA`)

### 16.3 Tabela de Alertas

Uma linha por jornada que atenda qualquer condição:
- Status `ABERTA` com início há mais de 12h
- Status `EM_PAUSA` há mais de 2h
- Jornada encerrada com `faturamento.total_dia == 0`

---

# Fase 17 — React — Gestão de Motoristas

**Pré-requisito:** Fase 15  
**Entregável:** CRUD completo de motoristas com drawer de perfil detalhado

### 17.1 Listagem

**Endpoint:** `GET /users/` (filtrar `role == MOTORISTA`)

Tabela com: nome, e-mail, status CNH, horas acumuladas no mês, botão "Ver detalhes".  
Filtros: busca por nome, filtro por status CNH (válida / expirada).

### 17.2 Cadastro

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

### 17.3 Drawer de Perfil (`Sheet` do shadcn)

Abre ao clicar em "Ver detalhes". Abas:
1. **Dados Pessoais** — nome, CPF, telefone → `PATCH /users/{id}` ao salvar
2. **CNH** — data de vencimento com indicador visual (verde > 60d, amarelo 30–60d, vermelho < 30d / expirada)
3. **Dados Bancários** — banco, agência, conta, CNPJ
4. **Horas CLT** — `ProgressBar` total horas do mês vs. 220h (agrega `GET /jornadas/?motorista_id=X`)
5. **Histórico** — últimas 10 jornadas (`GET /jornadas/?motorista_id=X&limit=10`)
6. **Bônus** — bônus acumulado no mês (`bonus_acumulado_mes` das jornadas)

---

# Fase 18 — React — Jornadas

**Pré-requisito:** Fase 15  
**Entregável:** listagem filtrada de jornadas com modal de detalhes completo

### 18.1 Listagem com Filtros

**Endpoint:** `GET /jornadas/?data=X&motorista_id=X&status_filtro=X&skip=0&limit=50`

Filtros na UI:
- Date picker (intervalo de datas — `date-fns` para manipulação)
- Select de motorista (carregado de `GET /users/`)
- Select de status (`ABERTA`, `EM_ANDAMENTO`, `EM_PAUSA`, `ENCERRADA`)

`BarChart` acima da tabela: km rodados por jornada no período filtrado.

### 18.2 Modal de Detalhes (`Dialog` do shadcn)

Disparado ao clicar em uma linha. Seções:

| Seção | Conteúdo |
|---|---|
| Cabeçalho | data, motorista, veículo, status com badge colorido |
| Horários | início, fim, duração total, saldo CLT |
| Quilometragem | inicial, final, rodados, km morta |
| Faturamento | Uber / 99 / Outros / Total, links para comprovantes |
| Pausas | timeline visual com tipo e duração de cada pausa |
| Abastecimentos | tabela com km e valores por tipo de combustível |
| GPS | coordenadas inicial e final |

---

# Fase 19 — React — Veículos, Manutenções e Metas

**Pré-requisito:** Fase 15  
**Entregável:** três módulos CRUD integrados à API

### 19.1 Veículos

| Operação | Endpoint |
|---|---|
| Listar | `GET /veiculos/` |
| Criar | `POST /veiculos/` |
| Editar | `PATCH /veiculos/{placa}` |

Grid de cards com: placa, modelo, status (badge), alertas de IPVA/inspeção (amarelo ≤ 60d, vermelho ≤ 30d / expirado).  
Barra de status no topo: contagem por status.

### 19.2 Manutenções

| Operação | Endpoint |
|---|---|
| Listar | `GET /manutencoes/?veiculo_id=X` |
| Criar | `POST /manutencoes/` |
| Atualizar | `PATCH /manutencoes/{id}` |

KPIs no topo: custo total do mês, manutenções em andamento, veículos próximos de revisão (500km do intervalo).

### 19.3 Metas e Bônus

| Operação | Endpoint |
|---|---|
| Listar | `GET /metas/` |
| Criar | `POST /metas/` |
| Editar | `PATCH /metas/{id}` |
| Excluir | `DELETE /metas/{id}` |

Modal "Nova Meta": tipo (faturamento/km/horas), escopo (individual/equipe), `motorista_id` (se individual), thresholds mínimo/máximo, valor do bônus.

`BarChart` de bônus acumulado por motorista no mês corrente (agrega `bonus_acumulado_mes` das jornadas).

---

# Fase 20 — React — Relatórios

**Pré-requisito:** Fase 15  
**Entregável:** página de relatórios com importação CSV, comparativo e exportação

Página com três abas (`Tabs` do shadcn):

### Aba 1 — Comparativo de Plataformas

**Endpoints:**
1. `POST /uploads/` — enviar o arquivo CSV
2. `POST /relatorios/comparativo` — processar e retornar comparativo

**Fluxo:**
1. Componente `CsvImporter` com drag & drop para CSV (Uber ou 99)
2. Select de motorista e intervalo de datas
3. `POST /uploads/` com o arquivo → obtém URL
4. `POST /relatorios/comparativo` com a URL do arquivo

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
| Status | Verde (OK) / Vermelho (delta > 20%) |

### Aba 2 — Performance por Motorista

Radar chart (`RadarChart` do Recharts) por motorista, métricas normalizadas 0–100:
- Faturamento médio/dia
- KM médio/dia
- Horas trabalhadas vs. meta CLT
- Taxa de cumprimento de metas

Dados calculados no frontend a partir de `GET /jornadas/?motorista_id=X`.

### Aba 3 — Exportação

Botão "Exportar CSV" gera arquivo client-side (sem nova chamada à API) com os dados da tabela de jornadas atualmente filtrada em memória pelo React Query.
