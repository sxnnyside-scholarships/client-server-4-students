from src.localization.locale_manager import LocaleManager


def test_locale_manager_loads_en(tmp_path):
    # Setup mock localization files
    locales_dir = tmp_path / "localization"
    locales_dir.mkdir()

    en_json = locales_dir / "en.json"
    en_json.write_text('{"en": {"test": {"greeting": "Hello", "nested": {"key": "Value"}}}}')

    es_json = locales_dir / "es.json"
    es_json.write_text('{"es": {"test": {"greeting": "Hola"}}}')

    lm = LocaleManager(locales_dir)

    # Test EN resolution (Default)
    lm.set_locale("en")
    assert lm.get("test.greeting") == "Hello"
    assert lm.get("test.nested.key") == "Value"

    # Test fallback behavior when key doesn't exist at all
    assert lm.get("test.missing") == "[test.missing]"

    # Test ES resolution
    lm.set_locale("es")
    assert lm.get("test.greeting") == "Hola"

    # Test fallback to EN when key is missing in ES
    assert lm.get("test.nested.key") == "Value"


def test_locale_manager_handles_invalid_locale(tmp_path):
    locales_dir = tmp_path / "localization"
    locales_dir.mkdir()

    en_json = locales_dir / "en.json"
    en_json.write_text('{"en": {"test": {"greeting": "Hello"}}}')

    lm = LocaleManager(locales_dir)
    lm.set_locale("invalid_code")

    assert lm.current_locale == "en"
    assert lm.get("test.greeting") == "Hello"
