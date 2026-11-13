"""Safe local file inventory. This service exposes metadata only, not arbitrary file execution."""
import hashlib, os
from pathlib import Path

FILE_ROOT=Path(os.getenv("JROCAI_FILE_ROOT","data/files")).resolve()
class FileStorage:
    def __init__(self,root=FILE_ROOT): self.root=Path(root).resolve()
    def _safe(self,relative_path):
        lexical=self.root/relative_path
        if lexical.is_symlink(): raise ValueError("Symbolic links are not accepted")
        candidate=lexical.resolve()
        try: candidate.relative_to(self.root)
        except ValueError: raise ValueError("File path escapes the managed storage directory")
        return candidate
    def list(self,relative_directory="",limit=200):
        self.root.mkdir(parents=True,exist_ok=True)
        directory=self._safe(relative_directory or ".")
        if not directory.exists(): return []
        if not directory.is_dir(): raise ValueError("Requested path is not a directory")
        entries=[]
        for item in sorted(directory.iterdir(),key=lambda path:path.name.lower()):
            if item.is_symlink(): continue
            resolved=self._safe(str(item.relative_to(self.root)))
            stat=resolved.stat()
            entries.append({"name":resolved.name,"path":str(resolved.relative_to(self.root)),"kind":"directory" if resolved.is_dir() else "file","size_bytes":0 if resolved.is_dir() else stat.st_size,"modified_at":stat.st_mtime})
            if len(entries)>=max(1,min(limit,500)): break
        return entries
    def metadata(self,relative_path):
        path=self._safe(relative_path)
        if not path.exists() or not path.is_file(): return None
        digest=hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b""): digest.update(chunk)
        stat=path.stat()
        return {"name":path.name,"path":str(path.relative_to(self.root)),"size_bytes":stat.st_size,"modified_at":stat.st_mtime,"sha256":digest.hexdigest()}
storage=FileStorage()
