import hashlib
from pathlib import Path
import shutil

# Target directory: Defaults to ~/Downloads (adjust if needed)
TARGET_DIR = Path.home() / "Downloads"

# Category-to-extension mapping
CATEGORIES = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
    "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx", ".csv"],
    "Archives": [".zip", ".tar", ".gz", ".7z", ".rar"],
    "Audio": [".mp3", ".wav", ".aac", ".flac"],
    "Video": [".mp4", ".mov", ".mkv", ".avi"],
    "Installers": [".dmg", ".pkg", ".exe", ".msi", ".deb"],
    "Code": [".py", ".js", ".html", ".css", ".json", ".xml", ".sh"],
}

# Invert dictionary for fast extension lookup: {'.pdf': 'Documents', ...}
EXTENSION_MAP = {
    ext.lower(): category
    for category, extensions in CATEGORIES.items()
    for ext in extensions
}

# Directories created by the script that should not be touched
PROTECTED_DIRS = set(CATEGORIES.keys()) | {"_Duplicates", "Others"}


def calculate_sha256(file_path: Path, chunk_size: int = 65536) -> str:
    """Calculates SHA-256 hash in chunks to avoid memory bottlenecks on large files."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_unique_destination(destination_dir: Path, filename: str) -> Path:
    """Ensures moving a file never overwrites an existing file with the same name."""
    base_name = Path(filename).stem
    suffix = Path(filename).suffix
    candidate = destination_dir / filename
    counter = 1

    while candidate.exists():
        candidate = destination_dir / f"{base_name}_{counter}{suffix}"
        counter += 1

    return candidate


def run_janitor(target_folder: Path) -> None:
    if not target_folder.exists() or not target_folder.is_dir():
        print(f"Directory not found: {target_folder}")
        return

    duplicates_dir = target_folder / "_Duplicates"
    seen_hashes: dict[str, Path] = {}

    # Gather items before moving to prevent infinite recursion
    items = [
        item
        for item in target_folder.iterdir()
        if not (item.is_dir() and item.name in PROTECTED_DIRS)
    ]

    moved_counts = {cat: 0 for cat in CATEGORIES}
    moved_counts["Others"] = 0
    duplicate_count = 0

    for item in items:
        # Ignore subdirectories
        if not item.is_file():
            continue

        file_hash = calculate_sha256(item)

        # 1. Duplicate Handling
        if file_hash in seen_hashes:
            duplicates_dir.mkdir(exist_ok=True)
            dest = get_unique_destination(duplicates_dir, item.name)
            shutil.move(str(item), str(dest))
            duplicate_count += 1
            print(
                f"[DUPLICATE] Moved '{item.name}' -> '_Duplicates/' (matches '{seen_hashes[file_hash].name}')"
            )
            continue

        # Record hash of original file
        seen_hashes[file_hash] = item

        # 2. Extension Sorting
        category = EXTENSION_MAP.get(item.suffix.lower(), "Others")
        destination_folder = target_folder / category
        destination_folder.mkdir(exist_ok=True)

        dest = get_unique_destination(destination_folder, item.name)
        shutil.move(str(item), str(dest))
        moved_counts[category] += 1
        print(f"[{category.upper()}] Moved '{item.name}' -> '{category}/'")

    # Summary report
    print("\n" + "=" * 40)
    print(f"Cleanup Complete for: {target_folder}")
    print(f"Total duplicates isolated: {duplicate_count}")
    for cat, count in moved_counts.items():
        if count > 0:
            print(f"- {cat}: {count} files")
    print("=" * 40)


if __name__ == "__main__":
    run_janitor(TARGET_DIR)