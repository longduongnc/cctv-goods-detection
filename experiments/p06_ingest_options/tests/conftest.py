def pytest_configure(config):
    config.addinivalue_line("markers", "remote: needs long's machine (ffmpeg, models, clips); deselect with -m 'not remote'")
