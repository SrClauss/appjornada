# AppJornada Coletor (Flutter)

Aplicativo Android para coleta em background das activities dos pacotes:

- `com.app99.driver`
- `com.ubercab.driver`
- `com.github.android` (teste)
- `com.github.android.beta` (variante beta)

## Como funciona

1. O app abre as configurações de acessibilidade para ativar `Monitor AppJornada`.
2. O serviço Android captura mudanças de tela (`TYPE_WINDOW_STATE_CHANGED`) dos pacotes monitorados.
3. Os eventos ficam armazenados localmente e podem ser vistos na aba **Dados**.
4. Na aba **Envio**, toque em **Enviar dados do dia** para enviar para:
   - `http://2.24.121.189/api/coleta/upload`
5. A aba **Envio** também exibe logs da tentativa de envio e resposta do servidor.

Cabeçalho usado no envio:

- `X-API-Key: coleta-dev-key`

## Observações

- O monitoramento em background depende da permissão de acessibilidade ativada pelo usuário.
- O envio é manual (botão) para evitar tráfego contínuo durante os testes de campo.
- Existe workflow manual no GitHub Actions: **Gerar APK do Coletor**.
