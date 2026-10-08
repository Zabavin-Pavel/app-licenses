import os
import sys
import json
import random
import hashlib
import subprocess
import urllib.request
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Any

class Security:
    @staticmethod
    def calculate_checksum(*args) -> str:
        payload = "".join(str(arg) for arg in args)
        return hashlib.sha256(payload.encode()).hexdigest()

    @staticmethod
    def verify_integrity(state_dict: dict, expected_hash: str) -> bool:
        current_hash = Security.calculate_checksum(
            state_dict.get('hwid'), state_dict.get('user'),
            state_dict.get('level'), state_dict.get('seed')
        )
        return current_hash == expected_hash

    @staticmethod
    def generate_hwid() -> str:
        """Бесшумная генерация HWID на основе железа Windows (без мигания окон консоли)"""
        identifiers = []
        startupinfo = None
        
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE

        for cmd in ["wmic cpu get processorid", "wmic baseboard get serialnumber", "wmic diskdrive get serialnumber"]:
            try:
                output = subprocess.check_output(cmd, shell=True, startupinfo=startupinfo)
                lines = output.decode().split('\n')
                if len(lines) > 1 and lines[1].strip():
                    identifiers.append(lines[1].strip())
            except:
                pass
                
        combined = '-'.join(identifiers)
        return hashlib.sha256(combined.encode()).hexdigest()


class AppHub:
    REPO_OWNER = "Zabavin-Pavel"
    REPO_NAME = "app-licenses"
    BRANCH = "main"
    DEBUG = True  # Единый флаг отладки софта

    # Зашифрованный токен. PyArmor намертво закроет его внутри .exe
    _SECRET = b'=3.2/8\x05*;.\x05kk\x18\x1e\x17\x15\x11\x1f\x13j\x0b\x18\x02.,/ 4\x0b9m)\x0530-\t\x08\x1f\x03\x19=\x0b\r7\x10\x00c\x0b=\x1140,\x1f574.,\x1b\x03\x0f)\x10.\x12,1on ,>\x17\x14m\x1c\x10\x03\x02\x14\x18hk#\x1917\x1b\x08i'

    def __init__(self, app_name: str, current_version: str, local_mode: bool = True):
        self.app_name = app_name
        self.current_version = current_version
        self.local_mode = local_mode
        self.timeout = 10
        self.tz_moscow = timezone(timedelta(hours=3))  # Время +3 МСК для логов

        # Корректное определение папки логов для обычного запуска и для собранного PyInstaller .exe
        self.log_dir = Path(sys.argv[0]).resolve().parent if hasattr(sys, '_MEIPASS') else Path(__file__).resolve().parent
        if self.log_dir.name == "app_licenses":
            self.log_dir = self.log_dir.parent

        # Защита состояния памяти (Anti-cheat/Anti-tamper)
        self._seed = random.randint(100000, 999999)
        self._state = {'hwid': Security.generate_hwid(), 'user': None, 'level': 'UNAUTHORIZED', 'seed': self._seed}
        self._state_hash = Security.calculate_checksum(self._state['hwid'], None, 'UNAUTHORIZED', self._seed)

        self._licenses, self._user_data = None, None

        if self.DEBUG:
            print(f"🔧 [DEBUG] Модуль готов. HWID: {self._state['hwid']} | Режим: {'ЛОКАЛЬНЫЙ' if local_mode else 'СЕТЬ'}")

    def _get_token(self) -> str:
        return "".join(chr(b ^ 0x5A) for b in AppHub._SECRET).strip()

    def _sync_hash(self):
        self._state_hash = Security.calculate_checksum(
            self._state['hwid'], self._state['user'], self._state['level'], self._state['seed']
        )

    def _append_local_log(self, filename: str, log_message: str):
        try:
            with open(self.log_dir / filename, "a", encoding="utf-8") as f:
                f.write(log_message if log_message.endswith('\n') else log_message + "\n")
        except Exception as e:
            if self.DEBUG: print(f"❌ Ошибка записи локального лога: {e}")

    def log_event(self, message: str, level: str = "INFO"):
        user_label = self._state['user'] or "Unknown"
        timestamp_msk = datetime.now(self.tz_moscow).strftime("%Y-%m-%d %H:%M:%S MSK")
        timestamp_file = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        # 1. Текст самого лога
        log_line = f"[{timestamp_msk}] [{level}] [User: {user_label}] [HWID: {self._state['hwid']}] -> {message}"
        
        # Сначала пишем локально на ПК (для надежности)
        self._append_local_log("connections.log", log_line)
        if self.DEBUG: print(f"🧠 [LOG {level}] {message}")

        # Если включен локальный режим разработки — в сеть ничего не шлем
        if self.local_mode:
            return

        # 2. ОТПРАВКА НА СЕРВЕР (GITHUB API)
        def upload_worker():
            import base64
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            
            # Формируем уникальное имя файла для каждого события, чтобы избежать конфликтов
            filename = f"logs/{timestamp_file}_{user_label}_{self._state['hwid'][:8]}.log"
            
            domain = "://github.com"
            path = f"/repos/{self.REPO_OWNER}/{self.REPO_NAME}/contents/{filename}"
            url = f"https://{domain}{path}"
            
            # GitHub API требует передавать текст файла в кодировке Base64
            encoded_content = base64.b64encode(log_line.encode('utf-8')).decode('utf-8')
            
            payload = {
                "message": f"Log action from {user_label} ({level})",
                "content": encoded_content,
                "branch": self.BRANCH
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Authorization': f'Bearer {self._get_token()}',
                'Content-Type': 'application/json'
            }
            
            try:
                req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='PUT')
                with opener.open(req, timeout=10) as resp:
                    if self.DEBUG: print(f"☁️ Лог успешно отправлен на GitHub: {filename}")
            except Exception as e:
                if self.DEBUG: print(f"⚠️ Не удалось отправить лог на сервер: {e}")

        # Запускаем отправку в фоновом потоке, чтобы интерфейс программы не зависал во время сетевого запроса
        threading.Thread(target=upload_worker, daemon=True).start()

    def _download_file(self, filename: str) -> Optional[str]:
        """Изолированный сетевой запрос к API GitHub в обход системных прокси ОС"""
        # Пустой ProxyHandler({}) полностью игнорирует некорректные и мертвые прокси в Windows
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        
        domain = "api.github.com"
        path = f"/repos/{self.REPO_OWNER}/{self.REPO_NAME}/contents/{filename}"
        url = f"https://{domain}{path}?ref={self.BRANCH}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Authorization': f'Bearer {self._get_token()}',
            'Accept': 'application/vnd.github.v3.raw'
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            with opener.open(req, timeout=self.timeout) as resp:
                return resp.read().decode('utf-8')
        except Exception as e:
            if self.DEBUG: print(f"❌ Ошибка загрузки {filename} из GitHub: {e}")
            return None

    def fetch_json(self, filename: str) -> Optional[dict]:
        if self.local_mode:
            p = self.log_dir / filename
            if p.exists():
                try: return json.loads(p.read_text(encoding='utf-8'))
                except: pass
            return None

        content = self._download_file(filename)
        if content:
            try: return json.loads(content)
            except: pass
        return None

    def download_js_script(self, script_name: str) -> Optional[str]:
        if not Security.verify_integrity(self._state, self._state_hash) or self._state['level'] in ['UNAUTHORIZED', 'ERROR']:
            sys.exit("[Security Alert] Critical Violation")
        return self._download_file(script_name)

    def check_license(self) -> Optional[str]:
        if not Security.verify_integrity(self._state, self._state_hash):
            sys.exit("[Security Alert] Memory Tampering")

        self._licenses = self.fetch_json("licenses.json")
        if not self._licenses:
            self.log_event("Не удалось получить базу лицензий", "ALERT")
            return None

        min_ver = self._licenses.get('min_version')
        if min_ver and int(self.current_version) < int(min_ver):
            self.log_event(f"Отказ: Версия софта устарела (Текущая: {self.current_version}, Мин: {min_ver})", "INFO")
            return None

        found_user = next((u for u, info in self._licenses.get('users', {}).items() if (info if isinstance(info, str) else info.get('hwid')) == self._state['hwid']), None)
        if not found_user:
            self.log_event("Новый запрос доступа (HWID отсутствует в базе)", "INFO")
            try:
                import subprocess
                subprocess.Popen('clip', stdin=subprocess.PIPE, shell=True).communicate(self._state['hwid'].encode('utf-8'))
            except: pass
            return None

        apps = self._licenses.get('apps', {})
        if self.app_name not in apps or found_user not in apps[self.app_name]:
            self.log_event(f"Нет прав на приложение {self.app_name}", "INFO")
            return None

        user_data = apps[self.app_name][found_user]
        self._user_data = user_data

        if user_data.get('active') is not True:
            expires = user_data.get('expires')
            current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if not expires or current_date > expires:
                self.log_event("Лицензия заблокирована или истекла временным лимитом", "INFO")
                return None

        level = user_data.get('level', 'TRY')
        self._state.update({'user': found_user, 'level': level})
        self._sync_hash()

        self.log_event(f"Успешный вход в систему. Уровень прав: {level}", "SUCCESS")
        return level

    def get(self, param_name: str, fallback: bool = True) -> Any:
        if not Security.verify_integrity(self._state, self._state_hash):
            sys.exit("[Security Alert] Memory Tampering Detected!")
        if self._state['level'] == 'UNAUTHORIZED':
            return None
        if self._user_data and param_name in self._user_data:
            return self._user_data[param_name]
        return None
