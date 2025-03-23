# ke_api_mine.py
import os
import json
import requests
import subprocess
import hashlib
import zipfile

class KeApiMinecraft:
    def __init__(self, api_url="http://95.181.213.101:8000", auth_server="http://127.0.0.1:5000"):
        self.api_url = api_url
        self.auth_server = auth_server
        self.minecraft_dir = os.path.join(os.getenv("APPDATA"), ".minecraft")
        self.versions_dir = os.path.join(self.minecraft_dir, "versions")

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

    def download_version(self, version_id):
        url = self.get_download_url(version_id)
        if not url:
            print(f"Ошибка: Не удалось получить URL для версии {version_id}")
            return False
        
        version_folder = os.path.join(self.versions_dir, version_id)
        os.makedirs(version_folder, exist_ok=True)
        json_path = os.path.join(version_folder, f"{version_id}.json")
        jar_path = os.path.join(version_folder, f"{version_id}.jar")
        
        # Скачивание JSON
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Ошибка загрузки JSON для {version_id}: {response.status_code}")
            return False
        
        with open(json_path, "wb") as f:
            f.write(response.content)
        print(f"Скачан JSON: {json_path}")

        # Чтение JSON для получения URL JAR
        with open(json_path, "r", encoding="utf-8") as f:
            version_data = json.load(f)
        
        client_download = version_data.get("downloads", {}).get("client", {})
        if not client_download:
            print(f"Ошибка: Нет данных о JAR-файле в JSON для {version_id}")
            return False
        
        jar_url = client_download.get("url")
        expected_sha1 = client_download.get("sha1")
        
        if not jar_url:
            print(f"Ошибка: URL для JAR-файла не найден в JSON для {version_id}")
            return False
        
        # Скачивание JAR
        if self._download_file(jar_url, jar_path):
            if expected_sha1 and not self._check_sha1(jar_path, expected_sha1):
                print(f"Удаляю {jar_path} из-за ошибки SHA1")
                os.remove(jar_path)
                return False
            return True
        return False

    def download_natives(self, version_id):
        version_folder = os.path.join(self.versions_dir, version_id)
        json_path = os.path.join(version_folder, f"{version_id}.json")
    
        if not os.path.exists(json_path):
            print(f"Ошибка: JSON-файл версии {version_id} не найден!")
            return False
    
        # Чтение JSON-файла версии
        with open(json_path, "r", encoding="utf-8") as file:
            version_data = json.load(file)
    
        libraries = version_data.get("libraries", [])
        if not libraries:
            print(f"Ошибка: Нет данных о библиотеках для версии {version_id}")
            return False
    
        # Путь для сохранения natives
        natives_path = os.path.join(version_folder, "natives")
        os.makedirs(natives_path, exist_ok=True)
    
        natives_found = False
        for library in libraries:
            name = library.get("name", "Unnamed")
            downloads = library.get("downloads", {})

            # Вариант 1: Новые версии (:natives-windows в имени)
            if ":natives-windows" in name:
                artifact = downloads.get("artifact", {})
                if not artifact:
                    print(f"У библиотеки {name} нет 'artifact' в 'downloads'")
                    continue
                
                url = artifact.get("url")
                filename = artifact["path"].split("/")[-1]
                temp_filepath = os.path.join(version_folder, filename)
                expected_sha1 = artifact.get("sha1")

                print(f"Найден natives-windows (new style): {filename} ({url})")
                natives_found = True
                if self._download_file(url, temp_filepath):
                    if expected_sha1 and self._check_sha1(temp_filepath, expected_sha1):
                        self._extract_natives(temp_filepath, natives_path)
                    else:
                        print(f"Удаляю {temp_filepath} из-за ошибки SHA1")
                        os.remove(temp_filepath)

            # Вариант 2: Старые версии (classifiers)
            classifiers = downloads.get("classifiers", {})
            if "natives-windows" in classifiers:
                natives_info = classifiers["natives-windows"]
                url = natives_info.get("url")
                filename = natives_info["path"].split("/")[-1]
                temp_filepath = os.path.join(version_folder, filename)
                expected_sha1 = natives_info.get("sha1")

                print(f"Найден natives-windows (old style): {filename} ({url})")
                natives_found = True
                if self._download_file(url, temp_filepath):
                    if expected_sha1 and self._check_sha1(temp_filepath, expected_sha1):
                        self._extract_natives(temp_filepath, natives_path)
                    else:
                        print(f"Удаляю {temp_filepath} из-за ошибки SHA1")
                        os.remove(temp_filepath)

        if not natives_found:
            print(f"Нативные библиотеки для Windows не найдены в версии {version_id}")
            return False
        return True

    def _download_file(self, url, filepath):
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"Скачан файл: {filepath}")
            return True
        else:
            print(f"Ошибка при скачивании {url}: {response.status_code}")
            return False

    def _check_sha1(self, filepath, expected_sha1):
        sha1 = hashlib.sha1()
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                sha1.update(chunk)
        calculated_sha1 = sha1.hexdigest()
        if calculated_sha1 == expected_sha1:
            print(f"SHA1 проверен для {filepath}: {calculated_sha1}")
            return True
        else:
            print(f"SHA1 не совпадает для {filepath}: ожидаемый {expected_sha1}, рассчитанный {calculated_sha1}")
            return False

    def _extract_natives(self, jar_path, natives_dir):
        print(f"Распаковываю {jar_path} в {natives_dir}")
        try:
            with zipfile.ZipFile(jar_path, "r") as jar:
                dll_found = False
                for file_info in jar.infolist():
                    if file_info.filename.endswith(".dll"):
                        dll_found = True
                        filename = os.path.basename(file_info.filename)
                        with open(os.path.join(natives_dir, filename), "wb") as f:
                            f.write(jar.read(file_info))
                        print(f"Извлечён файл: {os.path.join(natives_dir, filename)}")
                if not dll_found:
                    print(f"В {jar_path} не найдено .dll файлов")
            os.remove(jar_path)
            print(f"Удалён временный файл: {jar_path}")
        except Exception as e:
            print(f"Ошибка при распаковке {jar_path}: {e}")

    def launch_minecraft(self, version_id, username="Player", ram=2048):
        version_folder = os.path.join(self.versions_dir, version_id)
        json_path = os.path.join(version_folder, f"{version_id}.json")
        jar_path = os.path.join(version_folder, f"{version_id}.jar")
    
        # Проверяем наличие файлов
        if not os.path.exists(json_path) or not os.path.exists(jar_path):
            print(f"❌ Файлы версии {version_id} не найдены. Скачиваем...")
            if not self.download_version(version_id):
                print("❌ Ошибка загрузки версии.")
                return

        # Загружаем JSON, чтобы получить аргументы запуска
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        natives_path = os.path.join(version_folder, "natives")
        if not os.path.exists(natives_path):
            print(f"❌ Папка natives не найдена для версии {version_id}. Скачиваем...")
            if not self.download_natives(version_id):
                print(f"❌ Ошибка загрузки natives для версии {version_id}.")
                return

        main_class = "net.minecraft.client.main.Main"
        args = [
            "java",
            f"-Xmx{ram}M",
            f"-Djava.library.path={natives_path}",
            "-cp",
            jar_path,
            main_class,
            "--username", username,
            "--version", version_id,
            "--gameDir", self.minecraft_dir,
            "--assetsDir", os.path.join(self.minecraft_dir, "assets"),
            "--assetIndex", data["assetIndex"]["id"],
            "--uuid", "0",  # Можно заменить на настоящий UUID
            "--accessToken", "token",
            "--userType", "legacy",
            "--versionType", "release",
            "--authServer", self.auth_server
        ]

        print("Запуск Minecraft с локальной аутентификацией...")
        subprocess.run(args)
