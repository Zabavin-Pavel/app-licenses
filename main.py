import time
import sys
from app_hub import AppHub, Security

# Инициализируем и проверяем лицензию один раз при старте
hub = AppHub("joystick", current_version="14", local_mode=False)
level = hub.check_license()

if not level:
    print("Доступ отклонен.")
    sys.exit()

print(f"Успешный запуск! Ваш уровень: {level}")

# --- ОСНОВНОЙ ЦИКЛ ВАШЕЙ ПРОГРАММЫ ---
while True:
    # ЛОКАЛЬНАЯ ПЕРЕПРОВЕРКА ЦЕЛОСТНОСТИ (без интернета)
    # Если реверсер изменил память, integrity вернет False, и скрипт уничтожится
    if not Security.verify_integrity(hub._state, hub._state_hash) or hub._state['level'] == 'UNAUTHORIZED':
        hub.log_event("Обнаружен патчинг памяти в рантайме! Завершение процесса.", "ALERT")
        sys.exit("[Security Alert] Memory Tampering Detected!")

    # КРИТИЧЕСКИЙ ФУНКЦИОНАЛ СОФТА
    print("Робот работает, лицензия в порядке...")
    
    # Пример локальной проверки уровня прав прямо из защищенной памяти
    if hub._state['level'] == 'DEV':
        pass # Выполняем функции для разработчиков
        
    time.sleep(5) # Имитация работы
