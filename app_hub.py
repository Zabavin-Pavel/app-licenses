"""
Универсальный менеджер конфигураций и лицензий через GitHub
Поддерживает версионирование, серверные конфиги и пользовательские параметры
"""

import json
import sys
import hashlib
import subprocess
import urllib.request
from typing import Optional, Any


class AppHub:
    """
    Менеджер приложения с проверкой лицензий и загрузкой конфигов с GitHub
    
    Структура файлов на GitHub:
    - licenses.json: пользователи, лицензии, min_version
    - global.json: общие параметры для всех серверов
    - {server}.json: параметры конкретного сервера (alure.json, dekan.json, ...)
    
    Приоритет поиска параметров:
    1. Пользовательский параметр (в apps.joystick.Pavel.param)
    2. Серверный конфиг (alure.json)
    3. Глобальный конфиг (global.json)
    4. None (если не найдено)
    """
    
    BASE_URL = "https://raw.githubusercontent.com/Zabavin-Pavel/app-licenses/refs/heads/main"
    
    def __init__(self, app_name: str, current_version: str, timeout: int = 10):
        """
        Args:
            app_name: название приложения (например, "joystick")
            current_version: текущая версия приложения (например, "5")
            timeout: таймаут HTTP запросов
        """
        self.app_name = app_name
        self.current_version = current_version
        self.timeout = timeout
        self.hwid = self._generate_hwid()
        
        # Кешированные данные
        self._licenses = None
        self._global_config = None
        self._server_config = None
        self._user_name = None
        self._user_data = None
        self._server_name = None
    
    def _generate_hwid(self) -> str:
        """Генерация уникального HWID на основе железа"""
        identifiers = []
        
        # CPU ID
        try:
            output = subprocess.check_output("wmic cpu get processorid", shell=True)
            cpu_id = output.decode().split('\n')[1].strip()
            identifiers.append(cpu_id)
        except:
            pass
            
        # Motherboard serial
        try:
            output = subprocess.check_output("wmic baseboard get serialnumber", shell=True)
            mb_serial = output.decode().split('\n')[1].strip()
            identifiers.append(mb_serial)
        except:
            pass
            
        # Disk serial
        try:
            output = subprocess.check_output("wmic diskdrive get serialnumber", shell=True)
            disk_serial = output.decode().split('\n')[1].strip()
            identifiers.append(disk_serial)
        except:
            pass
            
        # MAC address
        # try:
        #     import uuid
        #     mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
        #                 for elements in range(0,2*6,2)][::-1])
        #     identifiers.append(mac)
        # except:
        #     pass
        
        combined = '-'.join(identifiers)
        hwid = hashlib.sha256(combined.encode()).hexdigest()
        
        return hwid
    
    def _fetch_json(self, filename: str) -> Optional[dict]:
        """
        Загрузка JSON файла с автоопределением источника
        
        Режимы:
        - Разработка (не .exe) → пробуем локальный файл, затем GitHub
        - Production (.exe) → только GitHub
        """
        is_packaged = hasattr(sys, '_MEIPASS')
        
        # Режим разработки - пробуем локальный файл
        if not is_packaged:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.loads(f.read())
            except FileNotFoundError:
                pass  # Fallback на GitHub
            except Exception as e:
                print(f"❌ Ошибка чтения локального {filename}: {e}")
        
        # Production или fallback - загрузка с GitHub
        try:
            url = f"{self.BASE_URL}/{filename}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode())
                return data
        except Exception as e:
            print(f"❌ Ошибка загрузки {filename}: {e}")
            return None
    
    def _load_licenses(self) -> bool:
        """Загрузка файла лицензий"""
        if self._licenses is not None:
            return True
        
        self._licenses = self._fetch_json("licenses.json")
        if self._licenses is None:
            return False
        
        # Проверка структуры
        if 'users' not in self._licenses or 'apps' not in self._licenses:
            print("❌ Ошибка: неверная структура licenses.json")
            self._licenses = None
            return False
        
        return True
    
    def _load_global_config(self) -> bool:
        """Загрузка глобального конфига"""
        if self._global_config is not None:
            return True
        
        self._global_config = self._fetch_json("global.json")
        return self._global_config is not None
    
    def _load_server_config(self, server_name: str) -> bool:
        """Загрузка серверного конфига"""
        if self._server_config is not None and self._server_name == server_name:
            return True
        
        self._server_config = self._fetch_json(f"{server_name}.json")
        self._server_name = server_name
        return self._server_config is not None
    
    def _find_user(self) -> Optional[str]:
        """Поиск пользователя по HWID"""
        if not self._load_licenses():
            return None
        
        users = self._licenses['users']
        
        for user_name, user_info in users.items():
            # Поддержка старого формата (users.Pavel = hwid) и нового (users.Pavel.hwid = hwid)
            if isinstance(user_info, str):
                hwid = user_info
            elif isinstance(user_info, dict):
                hwid = user_info.get('hwid')
            else:
                continue
            
            if hwid == self.hwid:
                return user_name
        
        return None
    
    def _copy_hwid_to_clipboard(self):
        """Копирование HWID в буфер обмена"""
        try:
            process = subprocess.Popen(
                'clip',
                stdin=subprocess.PIPE,
                shell=True
            )
            process.communicate(self.hwid.encode('utf-8'))
            print(f"✅ HWID скопирован в буфер обмена")
            print(f"   {self.hwid}")
        except Exception as e:
            print(f"❌ Ошибка копирования в буфер: {e}")
            print(f"📋 Ваш HWID (скопируйте вручную):")
            print(f"   {self.hwid}")
    
    def _get_current_date_online(self) -> Optional[str]:
        """Получение текущей даты с онлайн сервера"""
        try:
            servers = [
                'http://worldtimeapi.org/api/timezone/Etc/UTC',
                'http://worldclockapi.com/api/json/utc/now',
            ]
            
            for server in servers:
                try:
                    req = urllib.request.Request(server)
                    with urllib.request.urlopen(req, timeout=5) as response:
                        data = json.loads(response.read().decode())
                        
                        if 'datetime' in data:
                            return data['datetime'].split('T')[0]
                        
                        if 'currentDateTime' in data:
                            return data['currentDateTime'].split('T')[0]
                except:
                    continue
            
            # Запасной вариант - GitHub headers
            try:
                req = urllib.request.Request(f"{self.BASE_URL}/licenses.json")
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    date_header = response.headers.get('Date')
                    if date_header:
                        from email.utils import parsedate
                        parsed = parsedate(date_header)
                        if parsed:
                            return f"{parsed[0]:04d}-{parsed[1]:02d}-{parsed[2]:02d}"
            except:
                pass
            
            return None
            
        except Exception as e:
            print(f"Ошибка получения даты с сервера: {e}")
            return None
    
    def check_license(self) -> Optional[str]:
        """
        Проверка лицензии пользователя (включая проверку версии)
        
        Returns:
            str: уровень доступа (DEV, PRO, TRY) при успехе
            None: доступ запрещен (нет лицензии или версия устарела)
        """
        if not self._load_licenses():
            return None
        
        # Проверка версии
        min_version = self._licenses.get('min_version')
        if min_version is not None:
            try:
                current = int(self.current_version)
                minimum = int(min_version)
                
                if current < minimum:
                    print(f"❌ ВЕРСИЯ УСТАРЕЛА: текущая={current}, минимальная={minimum}")
                    return None
            except ValueError:
                print(f"❌ Ошибка: неверный формат версии")
                return None
        
        # Найти пользователя
        user_name = self._find_user()
        if user_name is None:
            print(f"❌ HWID не найден в базе")
            self._copy_hwid_to_clipboard()
            return None
        
        self._user_name = user_name
        
        # Проверить приложение
        apps = self._licenses['apps']
        if self.app_name not in apps:
            print(f"❌ Приложение '{self.app_name}' не найдено")
            return None
        
        app_users = apps[self.app_name]
        if user_name not in app_users:
            print(f"❌ У '{user_name}' нет доступа к '{self.app_name}'")
            return None
        
        user_data = app_users[user_name]
        self._user_data = user_data
        
        # Проверка active
        if user_data.get('active') is True:
            level = user_data.get('level', 'TRY')
            return level
        
        # Проверка expires
        expires = user_data.get('expires')
        if not expires:
            print(f"❌ Лицензия неактивна")
            return None

        # Проверка даты онлайн
        current_date = self._get_current_date_online()

        if current_date is None:
            print("❌ Отказ: не удалось проверить дату")
            return None

        from datetime import datetime
        try:
            expires_dt = datetime.strptime(expires, "%Y-%m-%d")
            current_dt = datetime.strptime(current_date, "%Y-%m-%d")
            
            if current_dt > expires_dt:
                print(f"❌ Лицензия истекла {expires}")
                return None
            
            level = user_data.get('level', 'TRY')
            days_left = (expires_dt - current_dt).days
            print(f"✅ Доступ: {self._user_name} | {level} | Осталось дней: {days_left}")
            return level
            
        except ValueError as e:
            print(f"❌ Отказ: неверный формат даты")
            return None
    
    def get_server(self) -> Optional[str]:
        """
        Получить сервер пользователя
        
        Returns:
            str: название сервера (alure, dekan, ...) или "global" если не указан
            None: ошибка (не вызван check_license)
        """
        if self._user_name is None:
            print("❌ Сначала вызовите check_license()")
            return None
        
        users = self._licenses['users']
        user_info = users[self._user_name]
        
        # Поддержка нового формата (users.Pavel.server)
        if isinstance(user_info, dict):
            server = user_info.get('server')
            if server:
                return server
        
        # Если сервер не указан - используем global
        return "global"
    
    def get(self, param_name: str, fallback: bool = True) -> Any:
        """
        Получить параметр с каскадным поиском
        
        Приоритет:
        1. Пользовательский параметр (apps.joystick.Pavel.param)
        2. Серверный конфиг (alure.json)
        3. Глобальный конфиг (global.json)
        4. None
        
        Args:
            param_name: название параметра
            fallback: использовать fallback на global.json
        
        Returns:
            Значение параметра или None
        """
        # 1. Пользовательский параметр
        if self._user_data is not None:
            if param_name in self._user_data:
                return self._user_data[param_name]
        
        # 2. Серверный конфиг
        server = self.get_server()
        if server:
            if self._load_server_config(server):
                # Ищем в корне
                if param_name in self._server_config:
                    return self._server_config[param_name]
                
                # Ищем в подразделах (offsets, patterns, delays, ...)
                for section in self._server_config.values():
                    if isinstance(section, dict) and param_name in section:
                        return section[param_name]
        
        # 3. Глобальный конфиг
        if fallback and self._load_global_config():
            if param_name in self._global_config:
                return self._global_config[param_name]
            
            # Ищем в подразделах
            for section in self._global_config.values():
                if isinstance(section, dict) and param_name in section:
                    return section[param_name]
        
        # 4. Не найдено
        print(f"❌ Параметр '{param_name}' не найден")
        return None
    
    def get_hwid(self) -> str:
        """Получить текущий HWID"""
        return self.hwid
    
    def debug_all_users(self):
        """Вывести всех пользователей с их уровнями доступа"""
        if not self._load_licenses():
            return
        
        print("=" * 60)
        print(f"ЛИЦЕНЗИИ: {self.app_name}")
        print("=" * 60)
        
        apps = self._licenses.get('apps', {})
        if self.app_name not in apps:
            print(f"Приложение '{self.app_name}' не найдено")
            return
        
        app_users = apps[self.app_name]
        users_info = self._licenses.get('users', {})
        
        for user_name, user_data in app_users.items():
            level = user_data.get('level', 'TRY')
            active = user_data.get('active', False)
            expires = user_data.get('expires', 'N/A')
            
            # Получить сервер
            server = 'N/A'
            if user_name in users_info:
                user_info = users_info[user_name]
                if isinstance(user_info, dict):
                    server = user_info.get('server')
                    if not server:
                        server = 'global'
            
            status = "✅ Активна" if active else f"⏳ До {expires}"
            
            print(f"{user_name:12} | {level:3} | {server:10} | {status}")
        
        print("=" * 60)


if __name__ == '__main__':
    # Создаем экземпляр
    hub = AppHub("joystick", current_version="5")

    # # Вывод всех пользователей
    # hub.debug_all_users()
    
    # Проверка лицензии (включает проверку версии)
    level = hub.check_license()
    
    if level:
        print(f"✅ Доступ разрешен | Уровень: {level}")
        
        # Получение сервера
        server = hub.get_server()
        print(f"✅ Сервер: {server}")
        
        delay = hub.get("delay")
        print(f"delay: {delay}")
        
        patterns = hub.get("patterns")
        print(f"patterns: {patterns}")
        
        offset = hub.get("CHAT_FUNC_OFFSET")
        print(f"CHAT_FUNC_OFFSET: {offset}")
        
    else:
        print("⛔ Доступ запрещен")