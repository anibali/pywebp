from pathlib import Path

import PIL.Image
import pytest


@pytest.fixture
def test_data_dir():
    return Path(__file__).parent.joinpath('data')


@pytest.fixture
def image_bars_palette(test_data_dir):
    return PIL.Image.open(test_data_dir.joinpath('bars_palette.png'))


@pytest.fixture
def image_bars_palette_opaque(test_data_dir):
    return PIL.Image.open(test_data_dir.joinpath('bars_palette_opaque.png'))
