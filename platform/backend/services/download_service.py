import io

import zipfile

from typing import List, Union, Dict, Any


class DownloadService:
    @staticmethod
    def create_zip_archive(generated_files: List[Union[Dict[str, Any], Any]]) -> bytes:
        """
        Creates an in-memory ZIP archive from a list of generated files.
        Each file can be a dictionary with keys 'name' and 'content',
        or an object with 'name' and 'content' attributes.
        Returns the raw bytes of the zip file.
        """
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file in generated_files:
                if isinstance(file, dict):
                    name = file.get("name", "unknown")
                    content = file.get("content", "")
                else:
                    name = getattr(file, "name", "unknown")
                    content = getattr(file, "content", "")
                if not name:
                    name = "unknown"
                if content is None:
                    content = ""
                zip_file.writestr(name, content)
        return zip_buffer.getvalue()
