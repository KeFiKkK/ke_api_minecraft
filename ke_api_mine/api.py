import requests

class KeApiMinecraft:
    def __init__(self, api_url="http://95.181.213.101:8000", auth_server="http://127.0.0.1:5000"):
        self.api_url = api_url
        self.auth_server = auth_server

    def get_versions(self):
        """Получает список версий Minecraft."""
        response = requests.get(f"{self.api_url}/versions")
        if response.status_code == 200:
            return response.json().get("versions", [])
        return []

    def get_download_url(self, version_id):
        """Получает URL JSON-манифеста версии."""
        response = requests.get(f"{self.api_url}/download/{version_id}")
        if response.status_code == 200:
            return response.json().get("url")
        return None

    def get_auth_url(self):
        """Возвращает URL локального сервера для аутентификации."""
        return self.auth_server
