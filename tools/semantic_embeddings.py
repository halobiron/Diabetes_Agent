# bge-m3 ranks KB passages markedly better than the MiniLM model it replaced and separates
# out-of-scope questions cleanly (docs/danh_gia_truy_xuat_va_do_tre.md). It needs ~2.3 GB of
# weights and ~3.4 GB peak RAM; the retriever's thresholds are calibrated for this model only.
DEFAULT_MODEL = "BAAI/bge-m3"


class SemanticEmbeddingModel:
    """Sentence-transformer embeddings (unit-normalised, so cosine similarity = dot product).

    The model is loaded on first use so importing the app does not pay the load cost. On a
    CUDA GPU it runs in float16 (half the memory, faster, same metrics on data/eval).
    """

    def __init__(self, model_name=DEFAULT_MODEL):
        self.model_name = model_name
        self._model = None

    @property
    def name(self):
        return self.model_name

    def _load(self):
        if self._model is None:
            import torch
            from sentence_transformers import SentenceTransformer

            if torch.cuda.is_available():
                self._model = SentenceTransformer(
                    self.model_name, device="cuda", model_kwargs={"torch_dtype": torch.float16}
                )
            else:
                self._model = SentenceTransformer(self.model_name, device="cpu")
        return self._model

    def embed_texts(self, texts):
        vectors = self._load().encode(list(texts), normalize_embeddings=True)
        return [vector.astype("float32").tolist() for vector in vectors]

    def embed_text(self, text):
        return self.embed_texts([text])[0]
