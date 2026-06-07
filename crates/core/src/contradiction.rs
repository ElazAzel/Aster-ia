use std::collections::HashMap;
use std::collections::HashSet;

use serde_json::Value;

use crate::harness::BaseHarness;
use crate::schemas::ContradictionMatch;

const POSITIVE: &[&str] = &["good", "works", "safe", "valid", "true", "supports", "лучше", "работает"];
const NEGATIVE: &[&str] = &["bad", "fails", "unsafe", "invalid", "false", "breaks", "хуже", "не"];

pub struct ContradictionFinder;

impl Default for ContradictionFinder {
    fn default() -> Self {
        Self
    }
}

impl ContradictionFinder {
    pub fn new() -> Self {
        Self
    }

    pub fn cosine(left: &[f64], right: &[f64]) -> f64 {
        let dot: f64 = left.iter().zip(right.iter()).map(|(a, b)| a * b).sum();
        let left_norm: f64 = left.iter().map(|a| a * a).sum::<f64>().sqrt();
        let right_norm: f64 = right.iter().map(|b| b * b).sum::<f64>().sqrt();
        dot / (left_norm * right_norm).max(1e-9)
    }

    pub fn sentiment(text: &str) -> &str {
        let lower = text.to_lowercase();
        let terms: HashSet<&str> = lower.split(|c: char| !c.is_alphanumeric() && c != '_').collect();

        let has_negative = terms.iter().any(|t| NEGATIVE.contains(t));
        let has_positive = terms.iter().any(|t| POSITIVE.contains(t));

        if has_negative {
            "negative"
        } else if has_positive {
            "positive"
        } else {
            "neutral"
        }
    }

    pub fn find(
        &self,
        claims: &[String],
        similarities: &[Vec<f64>],
        threshold: f64,
    ) -> Vec<ContradictionMatch> {
        let mut matches = Vec::new();
        for i in 0..claims.len() {
            for j in (i + 1)..claims.len() {
                let similarity = similarities[i][j];
                let left_sentiment = Self::sentiment(&claims[i]);
                let right_sentiment = Self::sentiment(&claims[j]);
                if similarity >= threshold
                    && left_sentiment != "neutral"
                    && right_sentiment != "neutral"
                    && left_sentiment != right_sentiment
                {
                    matches.push(ContradictionMatch {
                        left: claims[i].clone(),
                        right: claims[j].clone(),
                        similarity,
                        sentiment_left: left_sentiment.into(),
                        sentiment_right: right_sentiment.into(),
                    });
                }
            }
        }
        matches
    }

    pub fn find_with_embeddings(
        &self,
        claims: &[String],
        embeddings: &[Vec<f64>],
        threshold: f64,
    ) -> Vec<ContradictionMatch> {
        let mut matches = Vec::new();
        for i in 0..claims.len() {
            for j in (i + 1)..claims.len() {
                let similarity = Self::cosine(&embeddings[i], &embeddings[j]);
                let left_sentiment = Self::sentiment(&claims[i]);
                let right_sentiment = Self::sentiment(&claims[j]);
                if similarity >= threshold
                    && left_sentiment != "neutral"
                    && right_sentiment != "neutral"
                    && left_sentiment != right_sentiment
                {
                    matches.push(ContradictionMatch {
                        left: claims[i].clone(),
                        right: claims[j].clone(),
                        similarity,
                        sentiment_left: left_sentiment.into(),
                        sentiment_right: right_sentiment.into(),
                    });
                }
            }
        }
        matches
    }
}

impl BaseHarness for ContradictionFinder {
    fn privacy_level(&self) -> &str {
        "local"
    }

    fn execute(&self, _payload: Option<HashMap<String, Value>>) -> Value {
        Value::Null
    }

    fn get_state(&self) -> HashMap<String, Value> {
        HashMap::new()
    }

    fn set_state(&self, _state: HashMap<String, Value>) {}
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cosine_identical() {
        let v = vec![1.0, 2.0, 3.0];
        let sim = ContradictionFinder::cosine(&v, &v);
        assert!((sim - 1.0).abs() < 1e-6);
    }

    #[test]
    fn test_cosine_orthogonal() {
        let sim = ContradictionFinder::cosine(&[1.0, 0.0], &[0.0, 1.0]);
        assert!((sim - 0.0).abs() < 1e-6);
    }

    #[test]
    fn test_cosine_opposite() {
        let sim = ContradictionFinder::cosine(&[1.0, 0.0], &[-1.0, 0.0]);
        assert!((sim - (-1.0)).abs() < 1e-6);
    }

    #[test]
    fn test_cosine_zero_vectors() {
        let sim = ContradictionFinder::cosine(&[0.0, 0.0], &[1.0, 0.0]);
        assert!((sim - 0.0).abs() < 1e-6);
    }

    #[test]
    fn test_sentiment_positive() {
        assert_eq!(ContradictionFinder::sentiment("this works well"), "positive");
        assert_eq!(ContradictionFinder::sentiment("хорошо работает"), "positive");
    }

    #[test]
    fn test_sentiment_negative() {
        assert_eq!(ContradictionFinder::sentiment("this fails badly"), "negative");
        assert_eq!(ContradictionFinder::sentiment("не работает"), "negative");
    }

    #[test]
    fn test_sentiment_neutral() {
        assert_eq!(ContradictionFinder::sentiment("the sky is blue"), "neutral");
    }

    #[test]
    fn test_sentiment_positive_wins_over_negative() {
        assert_eq!(ContradictionFinder::sentiment("good but fails"), "negative");
    }

    #[test]
    fn test_find_no_matches() {
        let cf = ContradictionFinder::new();
        let claims = vec!["sky is blue".into(), "grass is green".into()];
        let embeddings = vec![vec![1.0, 0.0], vec![0.0, 1.0]];
        let matches = cf.find_with_embeddings(&claims, &embeddings, 0.8);
        assert!(matches.is_empty());
    }

    #[test]
    fn test_find_contradiction() {
        let cf = ContradictionFinder::new();
        let claims = vec!["this is good".into(), "this is bad".into()];
        let embeddings = vec![vec![1.0, 0.0], vec![0.9, 0.1]];
        let matches = cf.find_with_embeddings(&claims, &embeddings, 0.8);
        assert_eq!(matches.len(), 1);
        assert_eq!(matches[0].sentiment_left, "positive");
        assert_eq!(matches[0].sentiment_right, "negative");
    }

    #[test]
    fn test_find_below_threshold() {
        let cf = ContradictionFinder::new();
        let claims = vec!["this is good".into(), "this is bad".into()];
        let embeddings = vec![vec![1.0, 0.0], vec![0.0, 1.0]];
        let matches = cf.find_with_embeddings(&claims, &embeddings, 0.8);
        assert!(matches.is_empty());
    }

    #[test]
    fn test_privacy_level() {
        let cf = ContradictionFinder::new();
        assert_eq!(cf.privacy_level(), "local");
    }
}
