import pytest

from bobinestyle.scale import screen_scale


@pytest.mark.parametrize(
    ("size", "k"),
    [
        ((1920, 1080), 1.0),
        ((1920, 800), 1.0),  # scope: same text size as 16:9
        ((1440, 1080), 1.0),  # 4:3 pillarboxed
        ((1280, 720), 2 / 3),
        ((3840, 2160), 2.0),
        ((1024, 576), 1024 / 1920),  # anamorphic PAL DVD, display size
    ],
)
def test_screen_scale(size: tuple[int, int], k: float):
    assert screen_scale(*size) == pytest.approx(k)
