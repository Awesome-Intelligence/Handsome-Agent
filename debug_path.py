from pathlib import Path

file_path = '/etc/passwd'
normalized = Path(file_path)
print(f'normalized: {normalized}')
print(f'str(normalized): {str(normalized)}')
print(f'startswith slash: {str(normalized).startswith("/")}')
print(f'is_absolute(): {normalized.is_absolute()}')
print(f'parts: {normalized.parts}')
