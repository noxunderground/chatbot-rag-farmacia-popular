import os
import threading
from flask import Flask, render_template, request, jsonify
from rag_engine import RAGEngine

app = Flask(__name__, static_folder="static", template_folder="templates")

print("Agendando inicialização do motor RAG em segundo plano...")
rag_engine = None

# Respostas fallback
RESPOSTAS = {
    "Olá": "Olá! Como posso ajudar você hoje? Posso informar sobre o Programa Farmácia Popular do Brasil.",
    "Oi": "Olá! Como posso ajudar você hoje? Posso informar sobre o Programa Farmácia Popular do Brasil.",
    "o que é": "O Programa Farmácia Popular do Brasil é uma iniciativa do Governo Federal que oferece medicamentos gratuitos ou com descontos de até 90% para tratamento de doenças comuns na população.",
    "como funciona": "O programa funciona em duas modalidades: Rede Própria (unidades próprias) e Sistema de Co-pagamento (parceria com farmácias privadas). Para utilizar, é necessário apresentar documento de identidade, CPF e receita médica válida.",
    "medicamentos": "O programa oferece medicamentos para hipertensão, diabetes, asma, dislipidemia, rinite, doença de Parkinson, osteoporose, glaucoma, entre outros. Alguns são totalmente gratuitos, como os para hipertensão e diabetes.",
    "quem pode usar": "Qualquer cidadão brasileiro pode utilizar o Programa Farmácia Popular, independentemente da idade ou condição socioeconômica. É necessário apenas apresentar documentos pessoais e receita médica válida nas farmácias credenciadas.",
    "onde encontrar": "As farmácias credenciadas podem ser identificadas pela marca do Programa Farmácia Popular do Brasil. Você também pode consultar as unidades mais próximas no site do Ministério da Saúde ou pelo telefone 136.",
    "documentos": "Para adquirir medicamentos, é necessário apresentar: documento de identidade com foto, CPF e receita médica válida (do SUS ou particular) dentro do prazo de validade (geralmente 120 dias para medicamentos de uso contínuo).",
    "gratuitos": "Os medicamentos gratuitos incluem: Losartana, Captopril, Propranolol, Atenolol, Metformina, Glibenclamida, Insulina NPH, Insulina Regular, Salbutamol e outros para hipertensão, diabetes e asma."
}

# Mapeamento simples de sinônimos/variações para chaves conhecidas
SINONIMOS = {
    "oi": "Oi",
    "olá": "Olá",
    "ola": "Olá",
    "bom dia": "Olá",
    "boa tarde": "Olá",
    "boa noite": "Olá",
    "gratuidade": "gratuitos",
    "gratis": "gratuitos",
    "gratuito": "gratuitos"
}

def match_fallback(query_lower: str):
    # casa primeiro por sinônimos
    for termo, chave in SINONIMOS.items():
        if termo in query_lower:
            return RESPOSTAS.get(chave)
    # depois tenta chaves originais
    for palavra_chave, texto in RESPOSTAS.items():
        if palavra_chave.lower() in query_lower:
            return texto
    return None


def initialize_rag():
    """Inicializa o motor RAG de forma síncrona (usado pela thread)."""
    global rag_engine
    try:
        # Configuração via variáveis de ambiente
        embeddings_model = os.environ.get('EMBEDDINGS_MODEL')
        qa_model = os.environ.get('QA_MODEL')
        top_k = int(os.environ.get('TOP_K', '5'))
        chunk_chars = int(os.environ.get('CHUNK_CHARS', '700'))
        chunk_overlap = int(os.environ.get('CHUNK_OVERLAP', '80'))
        batch_size = int(os.environ.get('BATCH_SIZE', '32'))
        reranker_model = os.environ.get('RERANKER_MODEL')
        pre_k = int(os.environ.get('RERANK_PRE_K', str(max(top_k * 3, top_k))))
        cache_dir = os.environ.get('CACHE_DIR', 'cache')

        # Cria instância e roda inicialização
        rag_engine = RAGEngine(
            model_name=embeddings_model,
            qa_model_name=qa_model,
            top_k=top_k,
            chunk_chars=chunk_chars,
            chunk_overlap=chunk_overlap,
            batch_size=batch_size,
            reranker_model_name=reranker_model,
            pre_k=pre_k,
            cache_dir=cache_dir
        )
        rag_engine.initialize()
        print("Motor RAG inicializado com sucesso!")
    except Exception as e:
        print(f"Erro ao inicializar o motor RAG: {e}")
        rag_engine = None


# Inicialização assíncrona para não bloquear o start do servidor
def initialize_rag_async():
    t = threading.Thread(target=initialize_rag, daemon=True)
    t.start()
    return t

# Dispara a inicialização em background
initialize_rag_async()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/status')
def status():
    """Retorna o status do motor RAG."""
    if rag_engine and getattr(rag_engine, "initialized", False):
        return jsonify({"status": "ready"})
    else:
        return jsonify({"status": "loading"})


@app.route('/api/chat', methods=['POST'])
def chat():
    """Endpoint principal do chat"""
    data = request.json
    query = data.get('message', '').strip()
    query_lower = query.lower()

    if not query:
        return jsonify({
            "answer": "Por favor, envie uma pergunta válida.",
            "source": "Sistema"
        })

    # Primeiro, verifica respostas de cortesia/sinônimos antes do RAG
    resposta_fallback = match_fallback(query_lower)
    if resposta_fallback:
        print("Pergunta:", query)
        print("Resposta fallback (sinônimos):", resposta_fallback)
        return jsonify({
            "answer": resposta_fallback,
            "source": "Ministério da Saúde - Programa Farmácia Popular do Brasil"
        })

    # 1️⃣ Usa o RAG Engine se disponível
    if rag_engine and getattr(rag_engine, 'initialized', False):
        try:
            result = rag_engine.query(query)
            print("Pergunta:", query)
            print("Resposta RAG:", result['answer'])
            return jsonify({
                "answer": result['answer'],
                "source": result['source']
            })
        except Exception as e:
            print(f"Erro ao usar RAG: {e}")

    # Fallback — mensagem padrão quando RAG não está pronto ou houve erro
    resposta = (
        "O Programa Farmácia Popular oferece medicamentos gratuitos ou com desconto "
        "para a população. Para mais informações, pergunte sobre como funciona, "
        "medicamentos disponíveis, documentos necessários ou onde encontrar."
    )

    print("Pergunta:", query)
    print("Resposta fallback:", resposta)

    return jsonify({
        "answer": resposta,
        "source": "Ministério da Saúde - Programa Farmácia Popular do Brasil"
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug, host=host, port=port)
