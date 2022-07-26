"""
Manage Django back-end database operations
"""
import platform


class DjangoConnector:
    def __init__(self):
        self.url = self._get_database_url()



    @staticmethod
    def _get_database_url():
        if platform.system() == 'Windows':
            return "http://127.0.0.1:8000/api"
        else:
            return "http://127.0.0.1:3273/api"
