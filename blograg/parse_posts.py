import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

import psutil
from docling.datamodel.base_models import DocumentStream
from docling.document_converter import DocumentConverter
from rich import print
from tqdm import tqdm

BLOG_POSTS = "major.io/content/posts/"
OUTPUT_DIR = "output/"

num_docs = 0
ok_docs = 0
filenames = list(Path(BLOG_POSTS).glob("**/*.md"))


def process_file(filename: Path) -> bool:
    raw_file = filename.read_text(encoding="utf-8")
    content = raw_file.strip("-").split("---\n", 1)[1].strip()

    stream = DocumentStream(name="myfile.md", stream=BytesIO(content.encode()))

    converter = DocumentConverter()
    result = converter.convert(stream, raises_on_error=False)
    if result.status == "success":
        doc = result.document
        output_path = os.path.join(
            OUTPUT_DIR,
            filename.parent.name,
            filename.with_suffix(".json").name,
        )

        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        doc.save_as_json(output_path)
        return True
    return False


try:
    max_workers = psutil.cpu_count(logical=False) or 1
except ImportError:
    max_workers = os.cpu_count() or 1

with ProcessPoolExecutor(max_workers=max_workers) as executor:
    futures = {
        executor.submit(process_file, filename): filename for filename in filenames
    }
    for f in tqdm(
        as_completed(futures), total=len(filenames), desc="Converting documents"
    ):
        num_docs += 1
        if f.result():
            ok_docs += 1

print(f"Successfully converted {ok_docs} out of {num_docs} documents")
