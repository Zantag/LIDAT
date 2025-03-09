import os
import glob
import requests
import sys
import time
import re

# Конфигурация по подразбиране
DEFAULT_LIBRE_URL = "http://localhost:5000/translate"
DEFAULT_DEEPL_KEY = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
OUTPUT_FOLDER = "bg"  # Папка за преведените файлове (по подразбиране)

# Избор на преводач
print("Изберете услуга за превод:")
print("1. LibreTranslate")
print("2. DeepL")
choice = input("Въведете 1 или 2: ").strip()

if choice == "1":
    API_TYPE = "libre"
    api_url = input(f"Въведете адрес на LibreTranslate сървъра (по подразбиране {DEFAULT_LIBRE_URL}): ").strip() or DEFAULT_LIBRE_URL
    api_key = None
elif choice == "2":
    API_TYPE = "deepl"
    api_key = input(f"Въведете DeepL API ключ (по подразбиране {DEFAULT_DEEPL_KEY}): ").strip() or DEFAULT_DEEPL_KEY
    api_url = "https://api-free.deepl.com/v2/translate"
else:
    print("Невалиден избор. Изход...")
    sys.exit(1)

# Питаме къде да запишем преведените файлове
output_choice = input(f"Искате ли да запишете преведените файлове в нова папка '{OUTPUT_FOLDER}' (по подразбиране)? (y/n): ").strip().lower()

if output_choice != 'y':
    OUTPUT_FOLDER = ""  # Ако отговорът е 'n', записваме в същата директория като оригиналните файлове

# Създаване на папката, ако не съществува (по подразбиране)
if OUTPUT_FOLDER and not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

def translate_text(text, retries=5):
    """
    Превежда подадения текст чрез избраната услуга.
    """
    if API_TYPE == "libre":
        payload = {
            "q": text,
            "source": "en",
            "target": "bg",
            "format": "text"
        }
        headers = {}
    else:  # DeepL
        payload = {
            "text": [text],
            "source_lang": "EN",
            "target_lang": "BG"
        }
        headers = {"Authorization": f"DeepL-Auth-Key {api_key}"}
    
    for attempt in range(retries):
        try:
            response = requests.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("translatedText", text) if API_TYPE == "libre" else data["translations"][0]["text"]
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                wait_time = (attempt + 1) * 2
                print(f"\n429 Too Many Requests. Изчакване {wait_time} секунди...")
                time.sleep(wait_time)
            else:
                print(f"\nГрешка при превода на текст: {e}")
                break
        except Exception as e:
            print(f"\nГрешка при превода на текст: {e}")
            break
    return text

def is_translatable_line(line):
    """
    Проверява дали дадения ред съдържа текст за превод.
    """
    stripped = line.strip()
    return bool(stripped and not stripped.isdigit() and "-->" not in stripped)

def process_file(filename):
    print(f"\nОбработва се файл: {filename}")
    
    # Проверка дали файлът вече е .bg.srt
    if filename.endswith(".bg.srt"):
        print(f"Пропускане на файл {filename} (вече е преведен).")
        return
    
    # Проверка дали вече съществува преведен файл
    base_name = os.path.basename(filename)
    base_name = re.sub(r"\.\w{2}\.srt$|\.srt$", "", base_name) + ".bg.srt"
    
    # Определяме пътя на директорията, в която ще се запише преведеният файл
    source_folder = os.path.dirname(filename)
    target_folder = os.path.join(OUTPUT_FOLDER, os.path.relpath(source_folder, start=os.getcwd()))
    
    # Проверяваме дали целевата папка съществува и ако не, я създаваме
    os.makedirs(target_folder, exist_ok=True)

    output_filename = os.path.join(target_folder, base_name)
    
    # Ако вече има създаден преведен файл, пропускаме го
    if os.path.exists(output_filename):
        print(f"Файлът {output_filename} вече съществува. Пропускане на обработката.")
        return

    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()

    total_lines = len(lines)
    new_lines = []

    for idx, line in enumerate(lines):
        new_lines.append(translate_text(line.strip()) + "\n" if is_translatable_line(line) else line)
        progress = (idx + 1) / total_lines * 100
        sys.stdout.write(f"\r{filename} - {progress:.2f}%")
        sys.stdout.flush()

    # Записваме преведения файл
    with open(output_filename, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"\nГотово: {filename} е преведен и запазен като {output_filename}\n")

def main():
    srt_files = glob.glob("**/*.srt", recursive=True)
    if not srt_files:
        print("Няма намерени .srt файлове в текущата директория и нейните подпапки.")
        return
    for srt_file in srt_files:
        process_file(srt_file)

if __name__ == "__main__":
    main()
