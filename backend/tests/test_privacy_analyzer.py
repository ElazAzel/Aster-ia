from asterion_api.services.privacy_analyzer import PrivacyAnalyzer


def test_local_model_green():
    analyzer = PrivacyAnalyzer()
    report = analyzer.analyze(
        model_type="local",
        files_attached=False,
        memory_enabled=False,
        web_access=False,
    )
    assert report.level == "green"
    assert len(report.items) == 1
    assert report.items[0].risk == "green"


def test_api_model_red():
    analyzer = PrivacyAnalyzer()
    report = analyzer.analyze(
        model_type="api",
        files_attached=False,
        memory_enabled=False,
        web_access=False,
    )
    assert report.level == "red"


def test_local_with_files_yellow():
    analyzer = PrivacyAnalyzer()
    report = analyzer.analyze(
        model_type="local",
        files_attached=True,
        memory_enabled=False,
        web_access=False,
    )
    assert report.level == "yellow"
    risks = {item.risk for item in report.items}
    assert "yellow" in risks


def test_local_with_web_yellow():
    analyzer = PrivacyAnalyzer()
    report = analyzer.analyze(
        model_type="local",
        files_attached=False,
        memory_enabled=False,
        web_access=True,
    )
    assert report.level == "yellow"


def test_api_with_files_and_web_red():
    analyzer = PrivacyAnalyzer()
    report = analyzer.analyze(
        model_type="api",
        files_attached=True,
        memory_enabled=False,
        web_access=True,
    )
    assert report.level == "red"


def test_memory_always_yellow():
    analyzer = PrivacyAnalyzer()
    report = analyzer.analyze(
        model_type="local",
        files_attached=False,
        memory_enabled=True,
        web_access=False,
    )
    assert report.level == "yellow"
    memory_items = [i for i in report.items if i.what == "memory"]
    assert len(memory_items) == 1
    assert memory_items[0].destination == "encrypted_local_sqlcipher"
