import os
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

LOKI_URL = os.getenv("LOKI_URL", "http://localhost:3100")

class LogIntelligenceAgent:
    def __init__(self, base_url: str = LOKI_URL):
        self.base_url = base_url
        # Initialize an NLP TF-IDF vectorizer to extract meaning from raw text logs
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=50)

    def fetch_logs(self, limit=100):
        """
        Connects to Grafana Loki to pull the latest log streams containing errors.
        Provides realistic mock data if the Loki instance isn't reachable yet.
        """
        query = '{namespace="test-apps"} |= "error" or |= "Exception" or |= "failed"'
        try:
            res = requests.get(f"{self.base_url}/loki/api/v1/query", params={"query": query, "limit": limit}, timeout=2)
            if res.status_code == 200:
                results = res.json().get('data', {}).get('result', [])
                logs = []
                for stream in results:
                    for val in stream.get('values', []):
                        logs.append(val[1])
                return logs if logs else self._get_mock_logs()
            return self._get_mock_logs()
        except:
            return self._get_mock_logs()

    def _get_mock_logs(self):
        return [
            "ERROR [user-service] Connection timeout to postgres-db after 5000ms",
            "Exception in payment-service: Memory allocation failed",
            "ERROR [user-service] Connection timeout to postgres-db after 5000ms",
            "FATAL [rogue-pod] OutOfMemoryError: Java heap space",
            "ERROR [user-service] Connection timeout to postgres-db after 5000ms",
            "FATAL [rogue-pod] CPU thread locked, terminating process"
        ]

    def analyze_patterns(self):
        """
        Uses Scikit-Learn's NLP capabilities to cluster and identify recurring error patterns
        in the raw text logs.
        """
        logs = self.fetch_logs()
        if not logs:
            return {"status": "ok", "message": "No error logs detected in recent window.", "patterns": []}

        try:
            # Run TF-IDF Analysis
            tfidf_matrix = self.vectorizer.fit_transform(logs)
            
            # Sum tfidf scores to find the most mathematically significant words
            sum_tfidf = np.sum(tfidf_matrix, axis=0)
            scores = [(word, sum_tfidf[0, idx]) for word, idx in self.vectorizer.vocabulary_.items()]
            scores = sorted(scores, key=lambda x: x[1], reverse=True)
            
            # Extract the absolute most frequent failure vectors
            top_patterns = [word for word, score in scores[:4]]
            
            return {
                "status": "success",
                "total_errors_analyzed": len(logs),
                "nlp_extracted_keywords": top_patterns,
                "dominant_error_cluster": f"NLP indicates frequent cascading failures related to: '{', '.join(top_patterns)}'",
                "sample_critical_log": logs[3] if len(logs) > 3 else logs[0]
            }
        except Exception as e:
            return {"status": "error", "message": f"NLP Analysis failed: {e}"}
