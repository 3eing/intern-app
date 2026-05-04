from pathlib import Path
import os
import tempfile
import zipfile
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException
from urllib3.util.retry import Retry


CONTENT_TYPE_SUFFIXES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "image/tiff": ".tif",
    "image/svg+xml": ".svg",
}


def _build_retry_session() -> requests.Session:
    retry = Retry(
        total=4,
        connect=4,
        read=4,
        backoff_factor=1,
        status_forcelist=(408, 429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _guess_suffix(url: str, response: requests.Response, suffix: str | None) -> str:
    if suffix:
        return suffix if suffix.startswith(".") else f".{suffix}"

    content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if content_type in CONTENT_TYPE_SUFFIXES:
        return CONTENT_TYPE_SUFFIXES[content_type]

    url_suffix = Path(urlparse(url).path).suffix.lower()
    if url_suffix:
        return url_suffix

    return ".bin"


def download_file_from_Airtable(url: str, target_dir: Path, suffix: str | None = None) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        with _build_retry_session() as session:
            with session.get(url, stream=True, timeout=(10, 60)) as response:
                response.raise_for_status()
                resolved_suffix = _guess_suffix(url, response, suffix)
                file_descriptor, final_name = tempfile.mkstemp(
                    prefix="template-",
                    suffix=resolved_suffix,
                    dir=target_dir,
                )
                os.close(file_descriptor)

                final_path = Path(final_name)
                partial_path = final_path.with_suffix(final_path.suffix + ".part")

                with partial_path.open("wb") as output_file:
                    for chunk in response.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            output_file.write(chunk)

        if not partial_path.exists() or partial_path.stat().st_size == 0:
            raise ValueError("Le template telecharge est vide")

        if final_path.suffix.lower() == ".docx" and not zipfile.is_zipfile(partial_path):
            raise ValueError("Le template telecharge n'est pas un .docx valide")

        partial_path.replace(final_path)
        return final_path
    except RequestException as exc:
        raise ValueError(f"Echec du telechargement du template: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"Echec d'ecriture du template sur disque: {exc}") from exc
    finally:
        if "partial_path" in locals() and partial_path.exists():
            partial_path.unlink()
