"""Quick download script for CC-CEDICT."""
import urllib.request
import os

SOURCES = [
    "https://raw.githubusercontent.com/alexliao/cedict/master/cedict_ts.u8",
    "https://cdn.jsdelivr.net/npm/cc-cedict@1.0.0/cedict_ts.u8"
]

output = "../data/cedict_ts.u8"

print("Downloading CC-CEDICT...")
for url in SOURCES:
    try:
        print(f"Trying: {url}")
        urllib.request.urlretrieve(url, output)
        size_mb = os.path.getsize(output) / (1024*1024)
        if size_mb > 0.1:  # At least 100KB
            print(f"Success! Downloaded {size_mb:.2f} MB")
            exit(0)
    except Exception as e:
        print(f"Failed: {e}")
        continue

print("\nAll sources failed. Please download manually from:")
print("https://www.mdbg.net/chinese/dictionary?page=cedict")
exit(1)

