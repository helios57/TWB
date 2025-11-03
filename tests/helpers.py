import os

def get_mock_data(file_name):
    """
    Reads a mock data file from the tests/mock_data directory.
    """
    path = os.path.join(os.path.dirname(__file__), 'mock_data', file_name)
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()
