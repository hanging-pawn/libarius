from kochassistent.modelle import schluessel


def test_schluessel_findet_aehnliche_namen():
    assert schluessel("unsloth/Qwen3.5-27B") == schluessel("lmstudio-community/Qwen3.5-27B-MLX-8bit")
    assert schluessel("mlx-community/Qwen3.5-122B-A10B-4bit") == schluessel("Qwen3.5-122B-A10B")


def test_schluessel_trennt_groessen():
    assert schluessel("unsloth/Qwen3.5-27B") != schluessel("unsloth/Qwen3.5-4B")
    assert schluessel("unsloth/Qwen3.5-27B") != schluessel("lmstudio-community/Qwen3.8-27B-MLX-8bit")
