import os

def search_files(directory, search_str):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py') or file.endswith('.json'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        for line_no, line in enumerate(f, 1):
                            if search_str in line:
                                print(f"{path}:{line_no}: {line.strip()}")
                except Exception:
                    pass

if __name__ == "__main__":
    search_files(".", "too_long")
    print("---")
    search_files(".", "500")
