# Telegram Runrun.it Bot

Bot em Python para Telegram que integra com o Runrun.it, permitindo criar e gerenciar tarefas diretamente pelo chat.

---

## Funcionalidades

- **Criar tarefas** com fluxo de confirmação antes de enviar (evita erros de digitação)
- **Listar tarefas em aberto** e gerenciá-las via botões
- **Entregar tarefas** diretamente pelo bot
- **Registrar tempo trabalhado** (30min, 1h, 2h, 3h, 4h)
- **Adicionar comentários** em tarefas existentes
- **Marcar/desmarcar tarefas como urgentes**
- **Controle de acesso por whitelist** de IDs do Telegram
- **Timeout automático** em operações pendentes (5 minutos)
- **Proteção contra duplo clique** em ações

---

## Comandos disponíveis

| Comando             | Descrição                           |
|---------------------|-------------------------------------|
| `/start` ou `/help` | Exibe a mensagem de ajuda           |
| `/minhas_tarefas`   | Lista suas tarefas em aberto        |
| `/cancelar`         | Cancela qualquer operação pendente  |
| _(texto livre)_     | Inicia o fluxo de criação de tarefa |

> 💡 Configure os comandos no @BotFather com `/setcommands` para que apareçam no menu do Telegram.

---

## Requisitos

- **Docker + Docker Compose**
- Acesso à internet
- Conta no **Runrun.it** com acesso à API (plano pago)
- Bot criado no Telegram via **@BotFather**
- IDs dos usuários autorizados no Telegram

> 📌 Para descobrir seu ID no Telegram: https://t.me/userinfobot

---

## Instalação

### 1. Clonar o repositório

```bash
git clone https://github.com/alexandre6415/telegram-runrun-bot.git
cd telegram-runrun-bot
```

### 2. Criar o arquivo `.env`

```bash
cp .env.example .env
nano .env
```

Preencha todas as variáveis conforme as instruções dentro do `.env.example`.

### 3. Subir o contêiner

```bash
docker compose up --build -d
```

### 4. Verificar logs

```bash
docker logs -f telegram-runrun-bot
```

---

## Como encontrar os IDs do Runrun.it

| Variável              | Como encontrar                                                                 |
|-----------------------|--------------------------------------------------------------------------------|
| `RUNRUN_APP_KEY`      | Runrun.it → Integrações e Apps → API e Webhooks                               |
| `RUNRUN_USER_TOKEN`   | Runrun.it → Integrações e Apps → API e Webhooks                               |
| `RUNRUN_RESPONSIBLE_ID` | Slug visível na URL do perfil do usuário. Ex: `joao-silva`                  |
| `RUNRUN_PROJECT_ID`   | Acesse `GET /api/v1.0/projects` na API ou inspecione a URL do projeto         |
| `RUNRUN_BOARD_ID`     | Acesse `GET /api/v1.0/projects/:id` — campo `board_id` na resposta            |
| `RUNRUN_TYPE_ID`      | Acesse `GET /api/v1.0/task_types` na API                                      |

Exemplo de chamada para listar projetos:

```bash
curl "https://runrun.it/api/v1.0/projects" \
  -H "App-Key: SEU_APP_KEY" \
  -H "User-Token: SEU_USER_TOKEN"
```

---

## Atualização

```bash
git pull
docker compose up --build -d
```

---

## Estrutura do projeto

```
telegram-runrun-bot/
├── bot.py               # Código principal do bot
├── requirements.txt     # Dependências Python
├── Dockerfile
├── docker-compose.yml
├── .env                 # Variáveis de ambiente (não commitado)
├── .env.example         # Modelo do .env
├── .gitignore
└── README.md
```

---

## Segurança

- Tokens e chaves de API ficam **apenas no `.env`**, que está no `.gitignore`
- Acesso restrito por **whitelist de IDs do Telegram**
- Nenhum valor de configuração está hardcoded no código
- Em caso de vazamento de credenciais:
  - Revogue os tokens no Runrun.it
  - Gere um novo token no @BotFather
  - Atualize o `.env` imediatamente

---

## Licença

Projeto pessoal de estudo e automação. Adapte conforme sua necessidade.
