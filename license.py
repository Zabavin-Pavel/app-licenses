"""
Модуль лицензирования для Python приложений
"""

import json
import hashlib
import platform
import subprocess
import urllib.request
from datetime import datetime
from typing import Optional


# URL к файлу с лицензиями на GitHub
GITHUB_LICENSE_URL = "https://raw.githubusercontent.com/Zabavin-Pavel/app-licenses/refs/heads/main/licenses.json"


class LicenseManager:
    """
    Менеджер лицензий с проверкой через GitHub
    
    JSON структура:
    {
        "users": {
            "Pavel": "hwid123...",
            "Evgen": "hwid456..."
        },
        "apps": {
            "joystick": {
                "Pavel": {
                    "level": "PRO",
                    "expires": "2025-12-31",
                    "active": true
                }
            }
        }
    }
    """
    
    def __init__(self, app_name: str, timeout: int = 10):
        self.app_name = app_name
        self.timeout = timeout
        # self.hwid = self._generate_hwid()
        self.hwid = '24e00839c478ec63017f05a0453532ba000d3d8f50767befee1eb934ab14caff'
        
    def _generate_hwid(self) -> str:
        """Генерация уникального HWID на основе железа"""
        identifiers = []
        
        # CPU ID
        try:
            if platform.system() == "Windows":
                output = subprocess.check_output("wmic cpu get processorid", shell=True)
                cpu_id = output.decode().split('\n')[1].strip()
                identifiers.append(cpu_id)
            elif platform.system() == "Linux":
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if 'Serial' in line:
                            identifiers.append(line.split(':')[1].strip())
                            break
        except:
            pass
            
        # Motherboard serial
        try:
            if platform.system() == "Windows":
                output = subprocess.check_output("wmic baseboard get serialnumber", shell=True)
                mb_serial = output.decode().split('\n')[1].strip()
                identifiers.append(mb_serial)
        except:
            pass
            
        # Disk serial
        try:
            if platform.system() == "Windows":
                output = subprocess.check_output("wmic diskdrive get serialnumber", shell=True)
                disk_serial = output.decode().split('\n')[1].strip()
                identifiers.append(disk_serial)
        except:
            pass
            
        # MAC address
        try:
            import uuid
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                           for elements in range(0,2*6,2)][::-1])
            identifiers.append(mac)
        except:
            pass
        
        # Fallback
        if not identifiers:
            identifiers.append(platform.node())
        
        combined = '-'.join(identifiers)
        hwid = hashlib.sha256(combined.encode()).hexdigest()
        # hwid = '3e65a8012f215154375353baae6467641689362e77a691ca73668fc9c8968a42'
        
        return hwid
    
    def _get_current_date_online(self) -> Optional[str]:
        """Получение текущей даты с сервера"""
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
            
            # Запасной вариант - GitHub
            req = urllib.request.Request(GITHUB_LICENSE_URL)
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                date_header = response.headers.get('Date')
                if date_header:
                    from email.utils import parsedate
                    parsed = parsedate(date_header)
                    if parsed:
                        return f"{parsed[0]:04d}-{parsed[1]:02d}-{parsed[2]:02d}"
            
            return None
            
        except Exception as e:
            print(f"Ошибка получения даты с сервера: {e}")
            return None
    
    def _fetch_licenses(self) -> Optional[dict]:
        """Загрузка JSON с лицензиями из GitHub"""
        try:
            req = urllib.request.Request(
                GITHUB_LICENSE_URL,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode())
                return data
        except Exception as e:
            print(f"Ошибка подключения к серверу лицензий: {e}")
            return None
    
    def _copy_hwid_to_clipboard(self):
        """Копирование HWID в буфер обмена"""
        try:
            if platform.system() == "Windows":
                # Используем clip.exe для Windows
                process = subprocess.Popen(
                    'clip',
                    stdin=subprocess.PIPE,
                    shell=True
                )
                process.communicate(self.hwid.encode('utf-8'))
                print(f"✅ HWID скопирован в буфер обмена")
                print(f"   {self.hwid}")
            else:
                # Для Linux/Mac - просто выводим
                print(f"📋 Ваш HWID (скопируйте вручную):")
                print(f"   {self.hwid}")
        except Exception as e:
            print(f"❌ Ошибка копирования в буфер: {e}")
            print(f"📋 Ваш HWID (скопируйте вручную):")
            print(f"   {self.hwid}")
    
    def check_license(self) -> Optional[str]:
        """
        Проверка лицензии
        
        Returns:
            str: Уровень доступа при успехе
            None: Отказ в доступе
        """
        licenses_data = self._fetch_licenses()
        
        if licenses_data is None:
            print("❌ Отказ: не удалось подключиться к серверу лицензий")
            self._copy_hwid_to_clipboard()
            return None
        
        if 'users' not in licenses_data or 'apps' not in licenses_data:
            print(f"❌ Отказ: неверная структура базы лицензий")
            self._copy_hwid_to_clipboard()
            return None
        
        users = licenses_data['users']
        apps = licenses_data['apps']
        
        # Ищем пользователя по HWID
        user_name = None
        for name, hwid in users.items():
            if hwid == self.hwid:
                user_name = name
                break
        
        if user_name is None:
            print(f"❌ Отказ: HWID не найден в базе")
            self._copy_hwid_to_clipboard()
            return None
        
        # Проверяем приложение
        if self.app_name not in apps:
            print(f"❌ Отказ: приложение '{self.app_name}' не найдено")
            return None
        
        app_users = apps[self.app_name]
        
        if user_name not in app_users:
            print(f"❌ Отказ: у '{user_name}' нет доступа к '{self.app_name}'")
            return None
        
        license_info = app_users[user_name]
        
        # Проверка active
        if license_info.get('active') is True:
            level = license_info.get('level', 'TRY')
            print(f"✅ Доступ: {user_name} | {level} | Постоянная")
            return level
        
        # Проверка expires
        expires = license_info.get('expires')
        
        if not expires:
            print(f"❌ Отказ: дата окончания не указана")
            return None
        
        current_date = self._get_current_date_online()
        
        if current_date is None:
            print("❌ Отказ: не удалось проверить дату")
            return None
        
        try:
            expires_dt = datetime.strptime(expires, "%Y-%m-%d")
            current_dt = datetime.strptime(current_date, "%Y-%m-%d")
            
            if current_dt > expires_dt:
                print(f"❌ Отказ: лицензия истекла {expires}")
                return None
            
            level = license_info.get('level', 'TRY')
            days_left = (expires_dt - current_dt).days
            print(f"✅ Доступ: {user_name} | {level} | Осталось дней: {days_left}")
            return level
            
        except ValueError as e:
            print(f"❌ Отказ: неверный формат даты")
            return None
    
    def get_hwid(self) -> str:
        """Получить текущий HWID"""
        return self.hwid


if __name__ == '__main__':
    print("=" * 50)
    print("ТЕСТ МОДУЛЯ ЛИЦЕНЗИРОВАНИЯ")
    print("=" * 50)
    
    manager = LicenseManager("joystick")
    
    print(f"\nВаш HWID: {manager.get_hwid()}")
    print("\nПроверка лицензии...")
    
    level = manager.check_license()
    
    if level:
        print(f"\n🎉 Успех! Уровень: {level}")
    else:
        print("\n⛔ Доступ запрещен")