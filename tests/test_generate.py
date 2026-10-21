from src.generate import NOT_FOUND, SYSTEM, build_user_message


CHUNKS = [
    {"source": "Artículo 99", "text": "Artículo 99 - Sanciones\nMultas de hasta X."},
    {"source": "Anexo III", "text": "Anexo III - Alto riesgo\nÁmbitos..."},
]


def test_prompt_labels_every_fragment_with_its_source():
    msg = build_user_message("¿Cuánto es la multa?", CHUNKS)
    assert "[Artículo 99]" in msg and "[Anexo III]" in msg
    assert msg.startswith("<fragmentos>") and msg.endswith("Pregunta: ¿Cuánto es la multa?")


def test_system_prompt_forces_context_only_and_abstention():
    assert NOT_FOUND in SYSTEM
    assert "SOLO" in SYSTEM and "Citá" in SYSTEM
