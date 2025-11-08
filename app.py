import os
from flask import Flask, render_template, request, jsonify
from rag_engine import RAGEngine

app = Flask(__name__, static_folder="static", template_folder="templates")

print("Inicializando o motor RAG... (isso pode levar alguns minutos)")
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


def initialize_rag():
    """Inicializa o motor RAG"""
    global rag_engine
    try:
        rag_engine = RAGEngine()
        rag_engine.initialize()
        print("Motor RAG inicializado com sucesso!")
    except Exception as e:
        print(f"Erro ao inicializar o motor RAG: {e}")
        rag_engine = None


# Inicializar o RAG (pode demorar alguns segundos)
initialize_rag()


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

    if not query:
        return jsonify({
            "answer": "Por favor, envie uma pergunta válida.",
            "source": "Sistema"
        })

    # 1️⃣ Tenta usar o RAG Engine
    if rag_engine and getattr(rag_engine, 'initialized', False):
        try:
            result = rag_engine.query(query)
            print("Pergunta:", query)
            print("Resposta RAG:", result['answer'])
            return jsonify({
                "answer": result['answer'],  # 🔹 chave 'answer' que o front-end espera
                "source": result['source']
            })
        except Exception as e:
            print(f"Erro ao usar RAG: {e}")

    # Fallback — usa respostas predefinidas
    resposta = None
    query_lower = query.lower()

    for palavra_chave, texto in RESPOSTAS.items():
        if palavra_chave in query_lower:
            resposta = texto
            break

    if not resposta:
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
