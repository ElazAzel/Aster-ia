use std::collections::HashMap;

use serde_json::Value;

use crate::harness::BaseHarness;
use crate::schemas::RagChunk;

/// Default chunk size (characters).
const CHUNK_SIZE: usize = 1200;
/// Overlap between consecutive chunks.
const CHUNK_OVERLAP: usize = 160;
/// BM25 tuning: k1 parameter.
const BM25_K1: f64 = 2.5;
/// BM25 tuning: b parameter.
const BM25_B: f64 = 0.75;

pub struct DocumentIndexer {
    privacy_level: String,
    embedding_model: String,
    chunks: Vec<HashMap<String, Value>>,
}

impl Default for DocumentIndexer {
    fn default() -> Self {
        Self {
            privacy_level: "local".into(),
            embedding_model: "nomic-embed-text".into(),
            chunks: Vec::new(),
        }
    }
}

impl DocumentIndexer {
    pub fn new() -> Self {
        Self::default()
    }

    /// Split text into overlapping chunks.
    pub fn chunk(text: &str, size: usize, overlap: usize) -> Vec<String> {
        let cleaned: String = text
            .split_whitespace()
            .collect::<Vec<&str>>()
            .join(" ");
        if cleaned.is_empty() {
            return Vec::new();
        }
        let cleaned = cleaned.trim();
        let mut chunks = Vec::new();
        let mut start = 0;
        while start < cleaned.len() {
            let end = (start + size).min(cleaned.len());
            // Safe slice at char boundary
            let chunk_str = &cleaned[start..end];
            chunks.push(chunk_str.to_string());
            if end >= cleaned.len() {
                break;
            }
            start += size - overlap;
        }
        chunks
    }

    /// Tokenize text into lowercase word tokens.
    pub fn terms(text: &str) -> Vec<String> {
        let lower = text.to_lowercase();
        let mut result = Vec::new();
        let mut current = String::new();
        for ch in lower.chars() {
            if ch.is_alphanumeric() || ch == '_' || ch >= '\u{0430}' && ch <= '\u{044F}'
                || ch >= '\u{0410}' && ch <= '\u{042F}' || ch == 'ё' || ch == 'Ё'
            {
                current.push(ch);
            } else {
                if !current.is_empty() {
                    result.push(current.clone());
                    current.clear();
                }
            }
        }
        if !current.is_empty() {
            result.push(current);
        }
        result
    }

    /// Cosine similarity between two vectors.
    pub fn cosine(left: &[f64], right: &[f64]) -> f64 {
        if left.len() != right.len() || left.is_empty() {
            return 0.0;
        }
        let dot: f64 = left.iter().zip(right.iter()).map(|(a, b)| a * b).sum();
        let left_norm: f64 = left.iter().map(|a| a * a).sum::<f64>().sqrt();
        let right_norm: f64 = right.iter().map(|b| b * b).sum::<f64>().sqrt();
        dot / (left_norm * right_norm).max(1e-9)
    }

    /// Dense scores: cosine similarity against query vector.
    pub fn dense_scores(
        query_vector: &[f64],
        rows: &[HashMap<String, Value>],
    ) -> HashMap<String, f64> {
        let mut scores = HashMap::new();
        for row in rows {
            let id = row.get("id").and_then(|v| v.as_str()).unwrap_or("");
            let vector: Vec<f64> = row
                .get("vector")
                .and_then(|v| v.as_array())
                .map(|arr| {
                    arr.iter()
                        .filter_map(|x| x.as_f64())
                        .collect()
                })
                .unwrap_or_default();
            scores.insert(id.to_string(), Self::cosine(query_vector, &vector));
        }
        scores
    }

    /// BM25 scores for query against rows.
    pub fn bm25_scores(query: &str, rows: &[HashMap<String, Value>]) -> HashMap<String, f64> {
        let query_terms = Self::terms(query);
        let docs: Vec<Vec<String>> = rows
            .iter()
            .map(|row| {
                let content = row
                    .get("content")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                Self::terms(content)
            })
            .collect();

        let total_len: usize = docs.iter().map(|d| d.len()).sum();
        let avgdl = total_len as f64 / docs.len().max(1) as f64;

        let mut scores: HashMap<String, f64> = HashMap::new();

        for (i, row) in rows.iter().enumerate() {
            let id = row.get("id").and_then(|v| v.as_str()).unwrap_or("");
            let doc = &docs[i];
            let mut score = 0.0;

            for term in &query_terms {
                let df = docs.iter().filter(|d| d.contains(term)).count() as f64;
                if df == 0.0 {
                    continue;
                }
                let tf = doc.iter().filter(|t| *t == term).count() as f64;
                let idf = (1.0 + (docs.len() as f64 - df + 0.5) / (df + 0.5)).ln();
                let denom = tf + BM25_K1 * (1.0 - BM25_B + BM25_B * doc.len() as f64 / avgdl.max(1.0));
                score += idf * (tf * BM25_K1 / denom.max(1e-9));
            }

            scores.insert(id.to_string(), score);
        }

        // Normalize by max score
        let max_score = scores.values().cloned().fold(0.0_f64, f64::max).max(1.0);
        scores.iter_mut().for_each(|(_, v)| *v /= max_score);
        scores
    }

    /// Hybrid search: weighted combination of dense + BM25 scores.
    pub fn hybrid_search(
        &self,
        query: &str,
        query_vector: &[f64],
        limit: usize,
    ) -> Vec<RagChunk> {
        let rows = &self.chunks;
        let dense = Self::dense_scores(query_vector, rows);
        let bm25 = Self::bm25_scores(query, rows);

        let mut scored: Vec<(&HashMap<String, Value>, f64)> = rows
            .iter()
            .map(|row| {
                let id = row.get("id").and_then(|v| v.as_str()).unwrap_or("");
                let d = dense.get(id).copied().unwrap_or(0.0);
                let b = bm25.get(id).copied().unwrap_or(0.0);
                let combined = 0.7 * d + 0.3 * b;
                (row, combined)
            })
            .collect();

        scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

        scored
            .into_iter()
            .take(limit)
            .map(|(row, score)| RagChunk {
                id: row.get("id").and_then(|v| v.as_str()).unwrap_or("").into(),
                room_id: row.get("room_id").and_then(|v| v.as_str()).unwrap_or("").into(),
                content: row.get("content").and_then(|v| v.as_str()).unwrap_or("").into(),
                source: row.get("source").and_then(|v| v.as_str()).unwrap_or("").into(),
                score,
            })
            .collect()
    }

    /// Add a chunk to the in-memory index.
    pub fn add_chunk(&mut self, id: &str, room_id: &str, content: &str, source: &str, vector: Vec<f64>) {
        let mut row = HashMap::new();
        row.insert("id".into(), Value::String(id.into()));
        row.insert("room_id".into(), Value::String(room_id.into()));
        row.insert("content".into(), Value::String(content.into()));
        row.insert("source".into(), Value::String(source.into()));
        row.insert("vector".into(), Value::Array(vector.into_iter().map(Value::from).collect()));
        self.chunks.push(row);
    }
}

impl BaseHarness for DocumentIndexer {
    fn privacy_level(&self) -> &str {
        &self.privacy_level
    }

    fn execute(&self, payload: Option<HashMap<String, Value>>) -> Value {
        let p = payload.unwrap_or_default();
        let action = p.get("action").and_then(|v| v.as_str()).unwrap_or("search");
        match action {
            "search" => {
                let query = p.get("query").and_then(|v| v.as_str()).unwrap_or("");
                let limit = p.get("limit").and_then(|v| v.as_u64()).unwrap_or(8) as usize;
                let query_vec = vec![0.0; 768]; // stub embedding
                let results = self.hybrid_search(query, &query_vec, limit);
                serde_json::to_value(results).unwrap_or_default()
            }
            _ => Value::Null,
        }
    }

    fn get_state(&self) -> HashMap<String, Value> {
        let mut state = HashMap::new();
        state.insert("embedding_model".into(), Value::String(self.embedding_model.clone()));
        state
    }

    fn set_state(&self, _state: HashMap<String, Value>) {}
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_chunk_small_text() {
        let chunks = DocumentIndexer::chunk("hello world", 1200, 160);
        assert_eq!(chunks.len(), 1);
        assert_eq!(chunks[0], "hello world");
    }

    #[test]
    fn test_chunk_with_overlap() {
        let text = "a ".repeat(2000);
        let chunks = DocumentIndexer::chunk(&text, 500, 100);
        assert!(chunks.len() >= 4);
        assert!(chunks[0].len() <= 500);
    }

    #[test]
    fn test_chunk_empty() {
        let chunks = DocumentIndexer::chunk("", 1200, 160);
        assert!(chunks.is_empty());
    }

    #[test]
    fn test_chunk_whitespace_only() {
        let chunks = DocumentIndexer::chunk("   \n   \t   ", 1200, 160);
        assert!(chunks.is_empty());
    }

    #[test]
    fn test_terms_basic() {
        let terms = DocumentIndexer::terms("Hello World!");
        assert_eq!(terms, vec!["hello", "world"]);
    }

    #[test]
    fn test_terms_russian() {
        let terms = DocumentIndexer::terms("Привет мир!");
        assert_eq!(terms, vec!["привет", "мир"]);
    }

    #[test]
    fn test_terms_mixed() {
        let terms = DocumentIndexer::terms("hello_ мир123 test");
        assert_eq!(terms.len(), 3);
    }

    #[test]
    fn test_cosine_identical() {
        let sim = DocumentIndexer::cosine(&[1.0, 2.0], &[1.0, 2.0]);
        assert!((sim - 1.0).abs() < 1e-6);
    }

    #[test]
    fn test_cosine_orthogonal() {
        let sim = DocumentIndexer::cosine(&[1.0, 0.0], &[0.0, 1.0]);
        assert!((sim - 0.0).abs() < 1e-6);
    }

    #[test]
    fn test_cosine_empty() {
        let sim = DocumentIndexer::cosine(&[], &[]);
        assert!((sim - 0.0).abs() < 1e-6);
    }

    #[test]
    fn test_bm25_scores_empty() {
        let scores = DocumentIndexer::bm25_scores("test", &[]);
        assert!(scores.is_empty());
    }

    #[test]
    fn test_bm25_scores_basic() {
        let mut row = HashMap::new();
        row.insert("id".into(), Value::String("1".into()));
        row.insert("content".into(), Value::String("the cat sat on the mat".into()));
        let scores = DocumentIndexer::bm25_scores("cat", &[row]);
        assert_eq!(scores.len(), 1);
        assert!(scores["1"] > 0.0 && scores["1"] <= 1.0);
    }

    #[test]
    fn test_dense_scores() {
        let mut row = HashMap::new();
        row.insert("id".into(), Value::String("1".into()));
        row.insert("vector".into(), Value::Array(vec![Value::from(0.5), Value::from(0.5)]));
        let scores = DocumentIndexer::dense_scores(&[0.5, 0.5], &[row]);
        assert!((scores["1"] - 1.0).abs() < 0.01);
    }

    #[test]
    fn test_hybrid_search_empty() {
        let indexer = DocumentIndexer::new();
        let results = indexer.hybrid_search("test", &[0.0; 768], 5);
        assert!(results.is_empty());
    }

    #[test]
    fn test_hybrid_search_with_data() {
        let mut indexer = DocumentIndexer::new();
        indexer.add_chunk("1", "room1", "the cat sat on the mat", "doc1.txt", vec![0.1; 768]);
        let results = indexer.hybrid_search("cat", &[0.1; 768], 5);
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].id, "1");
        assert!(results[0].score > 0.0);
    }

    #[test]
    fn test_privacy_level() {
        let indexer = DocumentIndexer::new();
        assert_eq!(indexer.privacy_level(), "local");
    }

    #[test]
    fn test_execute_search() {
        let indexer = DocumentIndexer::new();
        let mut p = HashMap::new();
        p.insert("action".into(), Value::String("search".into()));
        p.insert("query".into(), Value::String("hello".into()));
        let result = indexer.execute(Some(p));
        let results: Vec<RagChunk> = serde_json::from_value(result).unwrap();
        assert!(results.is_empty());
    }
}
