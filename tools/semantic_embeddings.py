DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class SemanticEmbeddingModel:
    """Sentence-transformer embeddings (unit-normalised, so cosine similarity = dot product).

    The model is loaded on first use so importing the app does not pay the load cost.
    """

    def __init__(self, model_name=DEFAULT_MODEL):
        self.model_name = model_name
        self._model = None

    @property
    def name(self):
        return self.model_name

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_texts(self, texts):
        vectors = self._load().encode(list(texts), normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]

    def embed_text(self, text):
        return self.embed_texts([text])[0]
