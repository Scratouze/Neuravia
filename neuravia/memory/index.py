from __future__ import annotations
from .db import MemoryDB

class TextIndexerSimple:
    """Façade simple au-dessus de MemoryDB pour l'index texte.
    - Tokenisation basique alphanumérique
    - Similarité Jaccard
    """
    def __init__(self, db: MemoryDB) -> None:
        self.db = db

    def add(self, doc_id: str, text: str) -> None:
        self.db.index_add_document(doc_id, text)

    def search(self, query: str, top_k: int = 5):
        return self.db.index_search(query, top_k=top_k)
