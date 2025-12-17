# Telegram Runrun.it Bot

Bot em Python para Telegram que cria tarefas no Runrun.it a partir de mensagens, com opção de registrar horas já trabalhadas via API.

---

## Funcionalidades

* Cria tarefas no Runrun.it a partir de mensagens enviadas ao bot no Telegram.
* Define projeto, quadro e tipo de tarefa fixos via configuração.
* Permite registrar horas já trabalhadas usando o endpoint `manual_work_periods`.
* Pode rodar 24/7 como:

  * Contêiner **Docker** (recomendado)
  * Serviço **systemd** em uma VM Linux (modo alternativo/legado)

---

## Requisitos

* **Docker / Docker Compose**

  * ou **Linux (Ubuntu ou similar) + Python 3.8+**
* Acesso à internet
* Conta no **Runrun.it** com:

  * App-Key
  * User-Token
  * IDs de `project_id`, `board_id` e `type_id`
* Bot criado no Telegram via **@BotFather** (token HTTP)

---

## Rodando com Docker (recomendado)

### 1. Clonar o repositório

```bash
cd ~
git clone https://github.com/alexandre6415/telegram-runrun-bot.git
cd telegram-runrun-bot
```

### 2. Criar arquivo `.env`

```bash
nano .env
```

Exemplo de conteúdo:

```env
TELEGRAM_API_TOKEN=seu_token_do_bot_telegram
RUNRUN_APP_KEY=sua_app_key_runrun
RUNRUN_USER_TOKEN=seu_user_token_runrun
```

> ⚠️ O arquivo `.env` já está no `.gitignore` e **não deve ser commitado**.

### 3. Subir o contêiner

#### Usando Docker Compose

```bash
docker compose up --build -d
```

#### Usando Docker puro

```bash
docker build -t telegram-runrun-bot .
docker run -d \
  --name telegram-runrun-bot \
  --env-file .env \
  --restart unless-stopped \
  telegram-runrun-bot
```

### 4. Testar

* Abra o bot no Telegram e envie uma mensagem
* Verifique se a tarefa foi criada no Runrun.it
* Para acompanhar os logs:

```bash
docker logs -f telegram-runrun-bot
```

---

## Rodando sem Docker (venv + systemd – alternativa)

### 1. Clonar o repositório

```bash
cd ~
git clone https://github.com/alexandre6415/telegram-runrun-bot.git
cd telegram-runrun-bot
```

### 2. Criar ambiente virtual e instalar dependências

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente (`.env`)

```bash
nano .env
```

```env
TELEGRAM_API_TOKEN=seu_token_do_bot_telegram
RUNRUN_APP_KEY=sua_app_key_runrun
RUNRUN_USER_TOKEN=seu_user_token_runrun
```

### 4. Testar manualmente

```bash
python3 bot.py
```

* Envie uma mensagem ao bot no Telegram
* Confirme a criação da tarefa no Runrun.it
* Encerre com `Ctrl+C`

### 5. Executar como serviço systemd

```bash
sudo nano /etc/systemd/system/telegram-runrun-bot.service
```

```ini
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

Ativar o serviço:

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-runrun-bot.service
sudo systemctl start telegram-runrun-bot.service
sudo systemctl status telegram-runrun-bot.service
```

---

## Estrutura do projeto

```
telegram-runrun-bot/
├── bot.py              # Código do bot (Telegram + Runrun.it)
├── requirements.txt    # Dependências Python
├── Dockerfile          # Build da imagem Docker
├── docker-compose.yml  # Orquestração simples (opcional)
├── .gitignore          # Arquivos ignorados pelo Git
├── README.md           # Documentação
└── venv/               # Ambiente virtual local (não versionado, opcional)
```

---

## Segurança

* Tokens e chaves de API ficam apenas no arquivo `.env`
* `.env` e `venv/` estão no `.gitignore`
* Em caso de vazamento:

  * Revogue os tokens no Runrun.it
  * Gere um novo token no BotFather

---

## Licença

Projeto pessoal de estudo e automação. Adapte conforme sua necessidade.
