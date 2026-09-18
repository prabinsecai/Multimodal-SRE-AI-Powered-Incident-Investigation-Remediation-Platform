from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
out = root.parent / "multimodal-sre.zip"
exclude = {".env", ".git", "node_modules", ".venv", "__pycache__", ".pytest_cache", ".next"}

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in root.rglob("*"):
        if not path.is_file() or any(excluded in exclude for excluded in path.parts):
            continue
        archive.write(path, Path(root.name) / path.relative_to(root))

print(out)
