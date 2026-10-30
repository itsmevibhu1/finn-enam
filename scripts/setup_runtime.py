"""Install a checksum-verified portable Node 22 runtime into ignored .tools/."""
from pathlib import Path
from urllib.request import urlopen
import hashlib
import io
import tarfile

root = Path(__file__).resolve().parents[1] / '.tools'
base = 'https://nodejs.org/dist/latest-v22.x/'
checksums = urlopen(base + 'SHASUMS256.txt', timeout=30).read().decode()
checksum, name = next(line.split() for line in checksums.splitlines() if line.endswith('-linux-x64.tar.xz'))
content = urlopen(base + name, timeout=120).read()
if hashlib.sha256(content).hexdigest() != checksum:
    raise SystemExit('Runtime checksum mismatch')
root.mkdir(exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(content), mode='r:xz') as archive:
    archive.extractall(root, filter='data')
print(root / name.removesuffix('.tar.xz') / 'bin/node')
