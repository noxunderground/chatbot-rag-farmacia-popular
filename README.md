# Chatbot RAG - Programa Farmácia Popular

Chatbot inteligente baseado em RAG (Retrieval-Augmented Generation) para responder perguntas sobre o Programa Farmácia Popular do Brasil.

## 🖥️ Execução Local (sem deploy)

Esta versão roda totalmente local, sem necessidade de deploy em provedores.

### Pré-requisitos
- Python 3.9+
- pip
- Windows, macOS ou Linux

### Passo a passo

```bash
# (opcional) criar ambiente virtual
python -m venv .venv
# Linux/Mac
source .venv/bin/activate
# Windows
.venv\Scripts\activate

# instalar dependências
pip install -r requirements.txt

# iniciar o servidor Flask
python app.py
```

- Acesse `http://localhost:8000` no navegador.
- No primeiro start, os modelos serão baixados:
  - Embeddings: `sentence-transformers/all-mpnet-base-v2` (robusto)
  - QA: `deepset/roberta-base-squad2` (respostas focadas)
- Enquanto carrega, a interface exibirá “Carregando base de conhecimento...”. Assim que finalizar, muda para “Sistema pronto”.

### Variáveis de ambiente (opcionais)
- `EMBEDDINGS_MODEL`: modelo de embeddings (padrão robusto)
- `QA_MODEL`: modelo de QA para respostas focadas
- `TOP_K`: quantidade final de trechos usados na resposta
- `CHUNK_CHARS`: tamanho do chunk em caracteres
- `CHUNK_OVERLAP`: overlap entre chunks
- `BATCH_SIZE`: lote para cálculo de embeddings
- `RERANKER_MODEL`: modelo de reranqueamento (CrossEncoder)
- `RERANK_PRE_K`: candidatos iniciais antes do reranqueamento
- `CACHE_DIR`: diretório para cache de embeddings

### Dicas de desempenho
- Se for necessário reduzir latência, aumente recursos da máquina local (RAM/CPU).
- Para inicialização mais rápida, mantenha o app rodando para evitar novo download/parse em cada execução.

---

## 🚀 Deploy em Produção

### Pré-requisitos
- Python 3.8+
- pip
- Sistema operacional Linux/Windows

### 1. Configuração do Ambiente

```bash
# Clone o repositório
git clone <seu-repositorio>
cd chatbox_rag_pfpb

# Crie ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instale dependências
pip install -r requirements.txt
```

### 2. Configuração das Variáveis de Ambiente

```bash
# Copie o arquivo de exemplo
cp .env.example .env

# Edite as variáveis conforme necessário
nano .env  # ou use seu editor preferido
```

**Variáveis importantes:**
- `FLASK_ENV`: `production` para produção
- `PORT`: Porta do servidor (padrão: 8000)
- `HOST`: Host para bind (padrão: 0.0.0.0)
- `SERPAPI_KEY`: Chave API para buscas (opcional)

### 3. Preparação dos Dados

```bash
# Execute o scraper para coletar dados
python scraper.py

# Isso criará arquivos JSON na pasta data/
```

### 4. Deploy com Gunicorn (Recomendado)

```bash
# Para Render (uso de memória otimizado)
gunicorn -w 2 -b 0.0.0.0:$PORT app:app

# Para VPS/Linux (mais recursos disponíveis)
gunicorn -w 4 -b 0.0.0.0:8000 app:app

# Para background (Linux)
nohup gunicorn -w 4 -b 0.0.0.0:8000 app:app > app.log 2>&1 &
```

### 5. Deploy com Flask (Desenvolvimento)

```bash
# Configure variáveis de ambiente
export FLASK_ENV=production
export PORT=8000
export HOST=0.0.0.0

# Inicie o servidor
python app.py
```

### 6. Configuração Nginx (Opcional - Recomendado)

```nginx
server {
    listen 80;
    server_name seu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /caminho/para/seu/projeto/static;
    }
}
```

## 📁 Estrutura do Projeto

```
chatbox_rag_pfpb/
├── app.py              # Aplicação Flask principal
├── chat.py             # API de chat
├── rag_engine.py       # Motor RAG
├── scraper.py          # Coletor de dados
├── requirements.txt    # Dependências
├── .env.example       # Exemplo de variáveis
├── data/              # Dados coletados
├── templates/         # Templates HTML
└── static/            # Arquivos estáticos
```

## 🔧 Solução de Problemas

### Porta já em uso
```bash
# Encontre o processo
sudo lsof -i :8000
# Mate o processo
sudo kill -9 <PID>
```

### Erro de memória
- Reduza o número de workers do Gunicorn
- Use um servidor com mais RAM
- Considere usar um modelo menor de embeddings

### RAG não responde
- Verifique se os arquivos JSON existem em `data/`
- Confira os logs do aplicativo
- Teste a API diretamente: `curl http://localhost:8000/api/status`

## 📝 Comandos Úteis

```bash
# Ver logs em tempo real
tail -f app.log

# Restart do serviço
sudo systemctl restart seu-servico

# Testar API
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "O que é o Farmácia Popular?"}'
```

## 🔐 Segurança

- Sempre use HTTPS em produção
- Configure firewall adequadamente
- Mantenha dependências atualizadas
- Use variáveis de ambiente para senhas e chaves

## 📞 Suporte

Para problemas ou dúvidas:
1. Verifique os logs da aplicação
2. Teste localmente primeiro
3. Confira as configurações de ambiente
4. Consulte a documentação dos frameworks utilizados do Brasil

Este projeto implementa um chatbox utilizando Retrieval-Augmented Generation (RAG) para fornecer informações sobre o Programa Farmácia Popular do Brasil do Ministério da Saúde.

## Funcionalidades

- Interface de chat para consultas sobre o Programa Farmácia Popular
- Processamento de linguagem natural para entender perguntas em português
- Recuperação de informações relevantes de documentos oficiais
- Geração de respostas precisas baseadas em fontes confiáveis

## Estrutura do Projeto

- `app/` - Código principal da aplicação
  - `api/` - Endpoints da API
  - `core/` - Configurações e utilitários
  - `data/` - Scripts para coleta e processamento de dados
  - `models/` - Modelos e schemas
  - `rag/` - Implementação do sistema RAG
  - `static/` - Arquivos estáticos (CSS, JS)
  - `templates/` - Templates HTML
- `data/` - Dados coletados e processados
- `docs/` - Documentação adicional

## Instalação

1. Clone o repositório
2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
3. Configure as variáveis de ambiente (crie um arquivo `.env` baseado no `.env.example`)
4. Execute a aplicação:
   ```
   python -m app.main
   ```

## Tecnologias Utilizadas

- FastAPI - Framework web
- LangChain - Framework para aplicações de LLM
- ChromaDB - Banco de dados vetorial
- OpenAI - Modelos de linguagem