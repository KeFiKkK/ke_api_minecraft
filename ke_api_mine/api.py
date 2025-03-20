import requests
import os


class KeApiMinecraft:
    def __init__(self, api_url="http://95.181.213.101:8000", auth_server="http://127.0.0.1:5000"):
        self.api_url = api_url
        self.auth_server = auth_server

    def get_versions(self):
        response = requests.get(f"{self.api_url}/versions")
        if response.status_code == 200:
            return response.json().get("versions", [])
        return []

    def get_download_url(self, version_id):
        response = requests.get(f"{self.api_url}/download/{version_id}")
        if response.status_code == 200:
            return response.json().get("url")
        return None

    def get_auth_url(self):
        return self.auth_server

    def download_version(self, version_id):
        url = self.get_download_url(version_id)
        if not url:
            print(f"Ошибка: не найден URL для версии {version_id}")
            return False
        
        version_folder = os.path.join(self.versions_dir, version_id)
        os.makedirs(version_folder, exist_ok=True)
        json_path = os.path.join(version_folder, f"{version_id}.json")

        response = requests.get(url)
        if response.status_code == 200:
            with open(json_path, "wb") as f:
                f.write(response.content)
            print(f"Версия {version_id} успешно загружена.")
            return True

        print(f"Ошибка загрузки версии {version_id}: {response.status_code}")
        return False
