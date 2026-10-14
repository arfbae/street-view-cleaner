from io import BytesIO
from pathlib import Path
from tempfile import SpooledTemporaryFile
from PIL import Image

ALLOWED_FORMATS={"PNG","JPEG","WEBP"}

def read_stream(stream, max_bytes: int, chunk_size: int=1024*1024) -> bytes:
    """Read bounded upload data with automatic temporary-buffer cleanup."""
    total=0
    with SpooledTemporaryFile(max_size=8*1024*1024, mode="w+b") as temp:
        while True:
            chunk=stream.read(chunk_size)
            if not chunk: break
            total += len(chunk)
            if total > max_bytes: raise ValueError("file_too_large")
            temp.write(chunk)
        temp.seek(0)
        return temp.read()

def load_image(data: bytes) -> Image.Image:
    with BytesIO(data) as stream:
        image=Image.open(stream)
        image.load()
        if image.format not in ALLOWED_FORMATS: raise ValueError("unsupported_image_format")
        return image.convert("RGB")

def encode_png(image: Image.Image) -> bytes:
    with BytesIO() as out:
        image.save(out, format="PNG", optimize=True)
        return out.getvalue()

def save_bytes(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_name(path.name+".tmp")
    try:
        tmp.write_bytes(data); tmp.replace(path)
    finally:
        if tmp.exists(): tmp.unlink(missing_ok=True)
