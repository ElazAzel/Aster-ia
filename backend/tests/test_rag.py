from asterion_api.services.rag import DocumentIndexer


def test_chunk_empty_text():
    assert DocumentIndexer._chunk("") == []
    assert DocumentIndexer._chunk("   ") == []


def test_chunk_short_text():
    result = DocumentIndexer._chunk("hello")
    assert result == ["hello"]


def test_chunk_respects_size():
    text = "word " * 500
    chunks = DocumentIndexer._chunk(text, size=100, overlap=20)
    for chunk in chunks:
        assert len(chunk) <= 100


def test_chunk_has_overlap():
    text = "abcdefghij" * 100
    chunks = DocumentIndexer._chunk(text, size=50, overlap=10)
    assert len(chunks) > 1


def test_cosine_identical_vectors():
    vec = [1.0, 2.0, 3.0]
    score = DocumentIndexer._cosine(vec, vec)
    assert abs(score - 1.0) < 1e-6


def test_cosine_orthogonal_vectors():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    score = DocumentIndexer._cosine(a, b)
    assert abs(score) < 1e-6


def test_cosine_empty_vectors():
    assert DocumentIndexer._cosine([], []) == 0.0
    assert DocumentIndexer._cosine([1.0], []) == 0.0


def test_cosine_different_lengths():
    assert DocumentIndexer._cosine([1.0, 2.0], [1.0]) == 0.0


def test_terms_extraction():
    terms = DocumentIndexer._terms("Hello world тест 123")
    assert "hello" in terms
    assert "world" in terms
    assert "тест" in terms
    assert "123" in terms
