import json
import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from typing import List, Dict


class MuseumKnowledge:
    def __init__(self, data_dir: str = "data/datasets"):
        self.qa_pairs = self._load_datasets(data_dir)
        self.vectorizer = TfidfVectorizer()
        self._build_search_index()

    def _load_datasets(self, data_dir: str) -> List[Dict]:
        datasets = []
        for filename in os.listdir(data_dir):
            if filename.endswith('.json'):
                with open(os.path.join(data_dir, filename), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Extraer solo la parte de la pregunta del prompt
                    for item in data:
                        question = item["prompt"].split("\n")[-1].replace("¿", "").strip()
                        datasets.append({
                            "sala": item["sala"],
                            "question": question,
                            "completion": item["completion"],
                            "full_prompt": item["prompt"]
                        })
        return datasets

    def _build_search_index(self):
        questions = [qa["question"] for qa in self.qa_pairs]
        self.vectors = self.vectorizer.fit_transform(questions)

    def search(self, query: str, top_n: int = 3) -> List[Dict]:
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.vectors)
        top_indices = np.argsort(similarities[0])[-top_n:][::-1]

        # Filtrar solo resultados con similitud significativa
        return [
            self.qa_pairs[i]
            for i in top_indices
            if similarities[0][i] > 0.3  # Umbral de similitud
        ]


def cosine_similarity(a, b):
    return (a @ b.T).toarray()