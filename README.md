# Telegram Runrun.it Bot

Bot em Python para Telegram que cria tarefas no Runrun.it a partir de
mensagens, com opção de registrar horas já trabalhadas via API.

## Funcionalidades

-   Cria tarefas no Runrun.it a partir de mensagens enviadas ao bot no
    Telegram.
-   Define projeto, quadro e tipo de tarefa fixos via configuração.
-   Permite registrar horas já trabalhadas usando o endpoint
    `manual_work_periods`.
-   Pode rodar 24/7 como serviço `systemd` em uma VM Linux.

## Requisitos

-   Linux (Ubuntu ou similar)
-   Python 3.8+
-   Acesso à internet
-   Conta no Runrun.it com:
    -   App-Key
    -   User-Token
    -   IDs de `project_id`, `board_id` e `type_id`
-   Bot criado no Telegram via `@BotFather` (token HTTP)

## Instalação em uma VM limpa

### 1. Clonar o repositório

``` bash
cd ~
git clone https://github.com/alexandre6415/telegram-runrun-bot.git
cd telegram-runrun-bot
```

### 2. Criar ambiente virtual e instalar dependências

``` bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente (.env)

Crie o arquivo `.env` na raiz do projeto:

``` bash
nano .env
```

Conteúdo de exemplo:

``` env
TELEGRAM_API_TOKEN=seu_token_do_bot_telegram
RUNRUN_APP_KEY=sua_app_key_runrun
RUNRUN_USER_TOKEN=seu_user_token_runrun
```

> ⚠️ Importante: o arquivo `.env` já está no `.gitignore` e **não deve
> ser commitado**.

### 4. Testar o bot manualmente

Com o `venv` ativo:

``` bash
python3 bot.py
```

-   Abra o bot no Telegram e envie uma mensagem
-   Verifique se a tarefa foi criada no Runrun.it
-   Interrompa com `Ctrl+C` após o teste

## Executando como serviço systemd

Crie o arquivo de serviço:

``` bash
sudo nano /etc/systemd/system/telegram-runrun-bot.service
```

Exemplo de configuração:

``` ini
[Unit]
Description=Telegram Runrun.it Bot
After=network.target

[Service]
Type=simple
User=alexandre
WorkingDirectory=/home/alexandre/telegram-runrun-bot
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/alexandre/telegram-runrun-bot/venv/bin/python3 /home/alexandre/telegram-runrun-bot/bot.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

> Ajuste `User`, `WorkingDirectory` e `ExecStart` conforme o usuário e o
> caminho da sua VM.

Ativar e iniciar o serviço:

``` bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-runrun-bot.service
sudo systemctl start telegram-runrun-bot.service
sudo systemctl status telegram-runrun-bot.service
```

## Estrutura do projeto

    telegram-runrun-bot/
    ├── bot.py              # Código do bot (Telegram + Runrun.it)
    ├── requirements.txt    # Dependências Python
    ├── .gitignore          # Arquivos ignorados pelo Git
    ├── README.md           # Documentação
    └── venv/               # Ambiente virtual (não versionado)

## Segurança

-   Tokens e chaves de API ficam apenas no `.env` local
-   `.env` e `venv/` estão no `.gitignore`
-   Em caso de vazamento de tokens:
    -   Revogue no Runrun.it
    -   Gere um novo token no BotFather

## Licença

Projeto pessoal de estudo e automação. Adapte conforme sua necessidade.
