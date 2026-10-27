from pathlib import Path

import cv2
import numpy as np
import pytest

from ingest.encode import ffmpeg_cmd, jpeg_mb, jpeg_rows, measure_mbps


def noise(h, w):
    return np.random.default_rng(0).integers(0, 256, (h, w, 3), dtype=np.uint8)


def test_jpeg_smaller_target_is_smaller():
    img = noise(2000, 4000)                          # 8 MP
    assert jpeg_mb(img, 2.0) < jpeg_mb(img, 8.0)


def test_jpeg_refuses_upscaling():
    with pytest.raises(ValueError):
        jpeg_mb(noise(1080, 1920), 8.0)


def test_jpeg_rows_skips_pictures_smaller_than_the_target(tmp_path):
    cv2.imwrite(str(tmp_path / "big.jpg"), noise(1000, 2000))     # 2 MP
    cv2.imwrite(str(tmp_path / "small.jpg"), noise(854, 480))     # 0,4 MP, như khung cắt từ clip 480×854
    (row,) = jpeg_rows(tmp_path, [2.0], "frames39", "test")
    assert (row["n_images"], row["n_skipped"]) == (1, 1)


def test_ffmpeg_cmd():
    cmd = ffmpeg_cmd(Path("in.MOV"), Path("out.mp4"), "libx265", 28, 15)
    assert cmd[:4] == ["ffmpeg", "-y", "-i", "in.MOV"] and cmd[-1] == "out.mp4"
    for flag, val in (("-c:v", "libx265"), ("-crf", "28"), ("-r", "15")):
        assert cmd[cmd.index(flag) + 1] == val
    assert "-an" in cmd


def test_measure_mbps(tmp_path):
    path = tmp_path / "v.avi"
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 48))
    for _ in range(20):
        vw.write(noise(48, 64))
    vw.release()
    assert measure_mbps(path) == pytest.approx(path.stat().st_size * 8 / 2.0 / 1e6, rel=0.01)
