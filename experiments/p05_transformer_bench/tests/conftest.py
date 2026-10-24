def pytest_configure(config):
    config.addinivalue_line("markers", "gpu: loads a model and runs it (on CUDA when there is one); deselect with -m 'not gpu'")
