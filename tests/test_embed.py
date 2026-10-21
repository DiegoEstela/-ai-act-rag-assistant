import numpy as np

from src.embed import embed_passages, embed_query


def test_vectors_have_unit_length_and_expected_shape():
    v = embed_passages(["uno", "dos"])
    assert v.shape == (2, 384)
    assert np.allclose(np.linalg.norm(v, axis=1), 1.0, atol=1e-5)


def test_similar_meaning_is_closer_than_unrelated():
    docs = embed_passages([
        "Está prohibido puntuar socialmente a las personas con sistemas de IA.",
        "La receta lleva dos huevos, harina y una pizca de sal.",
    ])
    q = embed_query("¿Se puede hacer un ranking social de ciudadanos con IA?")
    assert q @ docs[0] > q @ docs[1]
