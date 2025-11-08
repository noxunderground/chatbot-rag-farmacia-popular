import os
import glob
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import numpy as np
import pdfplumber

class RAGEngine:
    def __init__(self, knowledge_base_dir: str = "knowledge_base"):
        self.knowledge_base_dir = knowledge_base_dir
        self.documents = []
        self.document_embeddings = []
        self.model = None
        self.initialized = False
        
    def initialize(self):
        try:
            # Carregar documentos
            self._load_documents()
            
            # Carregar modelo de embeddings (versão mais leve)
            self.model = SentenceTransformer('paraphrase-MiniLM-L6-v2')  # Modelo menor
            
            # Criar embeddings para os documentos em lotes menores
            batch_size = min(5, len(self.documents))  # Processar no máximo 5 docs por vez
            self.document_embeddings = []
            
            for i in range(0, len(self.documents), batch_size):
                batch = self.documents[i:i+batch_size]
                batch_embeddings = self.model.encode(batch)
                self.document_embeddings.extend(batch_embeddings)
                print(f"Processados {min(i+batch_size, len(self.documents))} de {len(self.documents)} documentos")
            
            self.document_embeddings = np.array(self.document_embeddings)
            self.initialized = True
            print("RAG Engine inicializado com sucesso!")
            
        except Exception as e:
            print(f"Erro ao inicializar RAG Engine: {e}")
            self.initialized = False
    
    

    def _load_documents(self):
        files = glob.glob(os.path.join(self.knowledge_base_dir, "*.txt"))
        if not files:
            print("⚠️ Nenhum documento encontrado em", self.knowledge_base_dir)
        for file_path in files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    self.documents.append(content)
                else:
                    print(f"⚠️ Documento vazio: {file_path}")
        print(f"Documentos carregados: {len(self.documents)}")


    
    def query(self, question: str) -> Dict[str, Any]:
        if not self.initialized:
            return {"answer": "Sistema RAG não inicializado.", "source": "Sistema"}

        try:
            print(f"Pergunta recebida: {question}")
            print(f"Número de documentos: {len(self.documents)}")

            if not self.documents:
                return {"answer": "Nenhum documento disponível na base.", "source": "Sistema"}

            question_embedding = self.model.encode([question])[0]
            similarities = np.dot(self.document_embeddings, question_embedding) / (
                np.linalg.norm(self.document_embeddings, axis=1) * np.linalg.norm(question_embedding)
            )
            print("Similaridades calculadas:", similarities)

            most_similar_idx = np.argmax(similarities)
            most_similar_doc = self.documents[most_similar_idx]
            print("Documento mais similar:", most_similar_idx)

            processed_answer = self._process_document_to_answer(most_similar_doc, question)
            return {"answer": processed_answer, "source": "Base de Conhecimento"}

        except Exception as e:
            import traceback
            traceback.print_exc()  # 🔥 imprime o erro completo
            return {"answer": f"Erro ao processar: {e}", "source": "Sistema"}

            
    def _process_document_to_answer(self, document: str, question: str) -> str:
        """
        Processa o documento para extrair uma resposta mais concisa e relevante,
        formatando-a como um diálogo natural.
        """
        try:
            # Remover marcadores Markdown se existirem
            clean_doc = document.replace('#', '')
            
            # Dividir o documento em parágrafos
            paragraphs = [p.strip() for p in clean_doc.split('\n') if p.strip()]
            
            # Verificar se há uma pergunta específica
            question_lower = question.lower()
            keywords = [
                "documento", "fraldas", "acamados", "representante", 
                "medicamento", "gratuito", "desconto", "farmácia", "popular"
            ]
            
            # Encontrar parágrafos relevantes com base em palavras-chave
            relevant_paragraphs = []
            for paragraph in paragraphs:
                # Considera relevante se a palavra-chave estiver **na pergunta ou no parágrafo**
                if any(keyword in question_lower or keyword in paragraph.lower() for keyword in keywords):
                    relevant_paragraphs.append(paragraph)

            
            # Preparar a resposta em formato de diálogo natural
            if not relevant_paragraphs and len(paragraphs) > 0:
                relevant_paragraphs = paragraphs[:2]  # Usar os dois primeiros parágrafos se não encontrar relevantes
            
            # Formatar a resposta como diálogo natural
            if "?" in question:
                intro = "Com base nas informações do Programa Farmácia Popular, "
            else:
                intro = "Sobre o que você perguntou, "
                
            if len(relevant_paragraphs) > 0:
                content = " ".join(relevant_paragraphs)
                # Remover quebras de linha e espaços extras
                content = " ".join(content.split())
                return f"{intro}{content}"
            else:
                return "Desculpe, não encontrei informações específicas sobre sua pergunta no Programa Farmácia Popular. Posso ajudar com informações sobre medicamentos disponíveis, documentos necessários, ou como funciona o programa?"
            
        except Exception as e:
            print(f"Erro ao processar documento para resposta: {e}")
            return "Desculpe, ocorreu um erro ao processar sua pergunta. Por favor, tente perguntar de outra forma ou sobre outro aspecto do Programa Farmácia Popular."