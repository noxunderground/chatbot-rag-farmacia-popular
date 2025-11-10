import os
import glob
import json
import hashlib
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer, CrossEncoder
from transformers import pipeline
import numpy as np
import re

class RAGEngine:
    def __init__(self, knowledge_base_dir: str = "knowledge_base", model_name: str = None, qa_model_name: str = None, chunk_chars: int = 700, chunk_overlap: int = 80, batch_size: int = 32, top_k: int = 5, reranker_model_name: str = None, pre_k: int = None, cache_dir: str = "cache"):
        self.knowledge_base_dir = knowledge_base_dir
        self.model_name = model_name or 'sentence-transformers/all-mpnet-base-v2'
        self.qa_model_name = qa_model_name or 'deepset/roberta-base-squad2'
        self.reranker_model_name = reranker_model_name or 'cross-encoder/ms-marco-MiniLM-L-6-v2'
        self.chunk_chars = chunk_chars
        self.chunk_overlap = chunk_overlap
        self.batch_size = batch_size
        self.top_k = top_k
        self.pre_k = pre_k or max(top_k * 3, top_k)
        self.cache_dir = cache_dir

        self.documents: List[Dict[str, str]] = []   # [{'title','content'}]
        self.chunks: List[Dict[str, str]] = []      # [{'id','title','text'}]
        self.embeddings = None
        self.model = None
        self.qa = None
        self.reranker = None
        self._fingerprint = None
        self.initialized = False

    def initialize(self):
        try:
            print("[RAG] Carregando documentos...")
            self._load_documents()
            print("[RAG] Gerando chunks...")
            self._chunk_documents()
            self._ensure_cache_dir()
            self._fingerprint = self._compute_fingerprint()

            print(f"[RAG] Carregando embeddings: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            if not self._load_cache():
                print("[RAG] Calculando embeddings dos chunks...")
                texts = [c['text'] for c in self.chunks]
                self.embeddings = self.model.encode(texts, show_progress_bar=True, batch_size=self.batch_size, normalize_embeddings=True)
                print(f"[RAG] {len(self.chunks)} chunks indexados.")
                self._save_cache()
            else:
                print(f"[RAG] Embeddings carregados do cache ({len(self.chunks)} chunks).")
            print(f"[RAG] Carregando QA: {self.qa_model_name}")
            try:
                self.qa = pipeline("question-answering", model=self.qa_model_name)
            except Exception as e:
                print(f"[RAG] QA indisponível, usando fallback simples: {e}")
                self.qa = None
            # Reranker
            try:
                self.reranker = CrossEncoder(self.reranker_model_name)
                print(f"[RAG] Reranker carregado: {self.reranker_model_name}")
            except Exception as e:
                print(f"[RAG] Reranker indisponível, seguindo sem reranqueamento: {e}")
                self.reranker = None
            self.initialized = True
            print("[RAG] Inicialização concluída.")
        except Exception as e:
            print(f"[RAG] Erro na inicialização: {e}")
            self.initialized = False

    def _load_documents(self):
        self.documents = []
        files = glob.glob(os.path.join(self.knowledge_base_dir, "*.txt"))
        if not files:
            print("⚠️ Nenhum documento encontrado em", self.knowledge_base_dir)
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    title = os.path.basename(file_path)
                    if content:
                        self.documents.append({"title": title, "content": content})
                    else:
                        print(f"⚠️ Documento vazio: {file_path}")
            except Exception as e:
                print(f"[RAG] Falha ao ler {file_path}: {e}")
        print(f"[RAG] Documentos carregados: {len(self.documents)}")

    def _chunk_documents(self):
        self.chunks = []
        chunk_id = 0
        for doc in self.documents:
            paragraphs = [p.strip() for p in doc['content'].split('\n') if p.strip()]
            for para in paragraphs:
                if len(para) <= self.chunk_chars:
                    self.chunks.append({'id': chunk_id, 'title': doc['title'], 'text': para})
                    chunk_id += 1
                else:
                    start = 0
                    while start < len(para):
                        end = min(len(para), start + self.chunk_chars)
                        text = para[start:end]
                        self.chunks.append({'id': chunk_id, 'title': doc['title'], 'text': text})
                        chunk_id += 1
                        if end == len(para):
                            break
                        start = max(0, end - self.chunk_overlap)
        print(f"[RAG] Chunks gerados: {len(self.chunks)}")

    def _ensure_cache_dir(self):
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except Exception as e:
            print(f"[RAG] Não foi possível criar cache dir: {e}")

    def _compute_fingerprint(self) -> str:
        m = hashlib.sha256()
        m.update((self.model_name or '').encode('utf-8'))
        m.update(str(self.chunk_chars).encode('utf-8'))
        m.update(str(self.chunk_overlap).encode('utf-8'))
        files = sorted(glob.glob(os.path.join(self.knowledge_base_dir, "*.txt")))
        for fp in files:
            try:
                st = os.stat(fp)
                m.update(os.path.basename(fp).encode('utf-8'))
                m.update(str(st.st_size).encode('utf-8'))
                m.update(str(int(st.st_mtime)).encode('utf-8'))
            except Exception:
                pass
        return m.hexdigest()[:16]

    def _cache_paths(self):
        emb_path = os.path.join(self.cache_dir, f"embeddings-{self._fingerprint}.npy")
        chunks_path = os.path.join(self.cache_dir, f"chunks-{self._fingerprint}.json")
        return emb_path, chunks_path

    def _load_cache(self) -> bool:
        emb_path, chunks_path = self._cache_paths()
        if os.path.exists(emb_path) and os.path.exists(chunks_path):
            try:
                with open(chunks_path, 'r', encoding='utf-8') as f:
                    cached_chunks = json.load(f)
                if isinstance(cached_chunks, list) and len(cached_chunks) == len(self.chunks):
                    self.chunks = cached_chunks
                    self.embeddings = np.load(emb_path)
                    return True
            except Exception as e:
                print(f"[RAG] Falha ao carregar cache: {e}")
        return False

    def _save_cache(self):
        emb_path, chunks_path = self._cache_paths()
        try:
            np.save(emb_path, self.embeddings)
            with open(chunks_path, 'w', encoding='utf-8') as f:
                json.dump(self.chunks, f, ensure_ascii=False)
        except Exception as e:
            print(f"[RAG] Falha ao salvar cache: {e}")

    def query(self, question: str) -> Dict[str, Any]:
        if not self.initialized:
            return {"answer": "Sistema RAG não inicializado.", "source": "Sistema"}

        try:
            if not self.chunks:
                return {"answer": "Nenhum conteúdo disponível na base.", "source": "Sistema"}

            query_embedding = self.model.encode([question], normalize_embeddings=True)[0]
            sims = np.dot(self.embeddings, query_embedding)  # embeddings normalizados → cosseno
            pre_k = min(len(self.chunks), self.pre_k)
            pre_indices = np.argsort(sims)[-pre_k:][::-1]
            pre_chunks = [self.chunks[i] for i in pre_indices]

            if self.reranker is not None:
                try:
                    pairs = [(question, c['text']) for c in pre_chunks]
                    scores = self.reranker.predict(pairs)
                    ranked = sorted(zip(pre_chunks, scores), key=lambda x: x[1], reverse=True)
                    top_chunks = [c for c, _ in ranked[:self.top_k]]
                except Exception as e:
                    print(f"[RAG] Falha no reranqueamento: {e}")
                    top_chunks = pre_chunks[:self.top_k]
            else:
                top_chunks = pre_chunks[:self.top_k]
            context = "\n\n".join([c['text'] for c in top_chunks])
            sources = [c['title'] for c in top_chunks]

            # Tenta responder com QA para foco
            if self.qa is not None:
                try:
                    qa_out = self.qa(question=question, context=context)
                    answer = qa_out.get('answer', '').strip()
                    score = qa_out.get('score', 0.0)
                    if answer and score >= 0.15:
                        # Se a resposta for muito curta, enriquecemos com trechos relevantes
                        if len(answer) < 40:
                            enriched = self._build_answer(question, top_chunks, base_answer=answer)
                            return {"answer": enriched, "source": ", ".join(dict.fromkeys(sources))}
                        return {"answer": answer, "source": ", ".join(dict.fromkeys(sources))}
                except Exception as e:
                    print(f"[RAG] Falha no QA: {e}")

            # Fallback: devolve melhores trechos com fonte
            answer = self._build_answer(question, top_chunks)
            return {"answer": answer, "source": ", ".join(dict.fromkeys(sources))}

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"answer": f"Erro ao processar: {e}", "source": "Sistema"}

    def _build_answer(self, question: str, top_chunks: List[Dict[str, str]], base_answer: str = "") -> str:
        # Palavras da pergunta para seleção de sentenças
        q = question.lower()
        tokens = [t for t in re.split(r"\W+", q) if len(t) > 2]
        selected_sentences = []
        for c in top_chunks:
            sentences = re.split(r"(?<=[.!?])\s+", c['text'])
            for s in sentences:
                s_clean = s.strip()
                if not s_clean:
                    continue
                if any(tok in s_clean.lower() for tok in tokens):
                    selected_sentences.append(s_clean)
        # Usa sentenças selecionadas ou os primeiros trechos
        if not selected_sentences:
            selected_sentences = [c['text'].strip() for c in top_chunks[:2] if c['text'].strip()]
        # Limita tamanho e remove quebras excessivas
        summary = " ".join(selected_sentences)
        summary = re.sub(r"\s+", " ", summary).strip()
        if len(summary) > 800:
            summary = summary[:800].rsplit(" ", 1)[0]
        if base_answer:
            intro = f"{base_answer}. " if base_answer.endswith('.') else f"{base_answer}: "
        else:
            intro = "De acordo com o Programa Farmácia Popular, "
        return f"{intro}{summary}"