def encrypt_string(text: str, key: int) -> bytes:
    """Шифрует строку методом XOR с использованием числового ключа"""
    return bytes([ord(char) ^ key for char in text])

def main():
    # 1. Вставьте ваш GitHub токен сюда в явном виде:
    GITHUB_TOKEN = "ghp_your_actual_github_token_here"
    
    # Ключ шифрования (должен совпадать с логикой в app_hub.py)
    XOR_KEY = 0x5A 

    print("=" * 70)
    print(f"🔑 Ключ шифрования (XOR_KEY): {hex(XOR_KEY)}")
    print("=" * 70)
    print("Сгенерированные байты для вставки в переменную _SECRET внутри app_hub.py:")
    print("=" * 70)

    clean_value = GITHUB_TOKEN.strip()
    if clean_value and not clean_value.startswith("ghp_your_actual"):
        # Шифруем токен
        encrypted_bytes = encrypt_string(clean_value, XOR_KEY)
        
        # Выводим строку в готовом для копирования виде
        print(f"_SECRET = {encrypted_bytes}")
        print("=" * 70)
        print("✅ Скопируйте строку выше и замените ей значение _SECRET в вашем app_hub.py.")
    else:
        print("❌ Сначала укажите ваш реальный токен в переменной GITHUB_TOKEN внутри этого скрипта!")
        print("=" * 70)

if __name__ == "__main__":
    main()
