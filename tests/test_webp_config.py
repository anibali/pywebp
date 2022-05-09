import pytest

import webp


class TestWebPConfig:
    def test_default(self):
        config = webp.WebPConfig.new()
        assert config.lossless is False
        assert config.quality == 75
        assert config.method == 4
        del config

    def test_default_lossless(self):
        config = webp.WebPConfig.new(lossless=True)
        assert config.lossless is True
        assert config.quality == 75
        assert config.method == 4
        del config

    def test_preset(self):
        config = webp.WebPConfig.new(preset=webp.WebPPreset.DRAWING)
        assert config.lossless is False
        assert config.quality == 75
        assert config.method == 4
        del config

    def test_lossless_preset_level(self):
        config = webp.WebPConfig.new(lossless=True, lossless_preset=8)
        assert config.lossless is True
        assert config.quality == 90
        assert config.method == 5
        del config

    def test_lossless_preset_quality_override(self):
        config = webp.WebPConfig.new(lossless=True, lossless_preset=8, quality=60)
        assert config.lossless is True
        assert config.quality == 60
        assert config.method == 5
        del config

    def test_lossy_with_lossless_preset_level(self):
        with pytest.raises(webp.WebPError):
            webp.WebPConfig.new(lossless=False, lossless_preset=8)
