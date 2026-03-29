import os
from datetime import datetime
from pathlib import Path
from typing import List

class FileManager:
    """Handles file operations and tracking of recent files."""
    
    SUPPORTED_TYPES = {
        "Auto Detect": "*.*",
        "Word Documents": "*.docx",
        "PowerPoint": "*.pptx",
        "Excel": "*.xlsx *.xls",
        "PDF": "*.pdf",
        "EPUB": "*.epub",
        "HTML": "*.html *.htm",
        "Text": "*.txt *.md *.csv *.json *.xml",
        "Images": "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp",
        "Archives": "*.zip",
        "All Files": "*.*"
    }

    @staticmethod
    def path_matches_accepted_extensions(filepath: str, accepted_extensions: list[str]) -> bool:
        """Whether ``filepath`` matches the drop-widget style filter (same as legacy isAcceptedFile logic).

        ``accepted_extensions`` entries may contain space-separated globs, e.g. ``\"*.xlsx *.xls\"``.
        If ``*.*`` appears as a whole entry, all files match.
        """
        if not accepted_extensions:
            return False
        if any(ext == "*.*" for ext in accepted_extensions):
            return True
        lower_path = filepath.lower()
        suffixes: list[str] = []
        for entry in accepted_extensions:
            for token in entry.split():
                t = token.strip().lower()
                if not t:
                    continue
                if t == "*.*":
                    return True
                if t.startswith("*."):
                    suffixes.append(t[1:])
        if not suffixes:
            return False
        return any(lower_path.endswith(suf) for suf in suffixes)

    @staticmethod
    def list_flat_files_in_directory(directory: str, accepted_extensions: list[str]) -> list[str]:
        """List files directly inside ``directory`` (non-recursive). Subfolders are ignored."""
        root = Path(directory)
        if not root.is_dir():
            return []
        out: list[str] = []
        try:
            entries = list(root.iterdir())
        except OSError:
            return []
        for child in entries:
            try:
                if not child.is_file():
                    continue
            except OSError:
                continue
            path_str = str(child)
            if FileManager.path_matches_accepted_extensions(path_str, accepted_extensions):
                out.append(path_str)
        out.sort(key=lambda p: p.lower())
        return out

    @staticmethod
    def get_backup_dir() -> str:
        """Get the backup directory path, creating it if it doesn't exist."""
        backup_dir = os.path.join(os.path.expanduser("~"), ".markitdown", "backups")
        os.makedirs(backup_dir, exist_ok=True)
        return backup_dir

    @staticmethod
    def create_backup_filename() -> str:
        """Generate a timestamped backup filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"autosave_{timestamp}.md"

    @staticmethod
    def save_markdown_file(filepath: str, content: str) -> None:
        """Save markdown content to a file."""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    @staticmethod
    def update_recent_list(filepath: str, recent_list: List[str], max_items: int = 10) -> List[str]:
        """Update a list of recent files."""
        if filepath in recent_list:
            recent_list.remove(filepath)
        recent_list.insert(0, filepath)
        return recent_list[:max_items]
