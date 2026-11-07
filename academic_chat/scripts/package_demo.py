"""Build a source ZIP with an example configuration and no Gmail-blocked file types."""
import os
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT.parent / 'PNU_Assistant_Windows.zip'
FILES = ('.dockerignore', '.gitignore', 'compose.yaml', 'Dockerfile',
         'IMPLEMENTATION_REQUIREMENTS.md', 'pyproject.toml', 'uv.lock', 'datagrip_examples.sql')
DIRECTORIES = ('app', 'data/sources', 'docs', 'frontend', 'postman', 'scripts', 'static', 'tests')
EXCLUDED_DIRS = {'__pycache__', 'node_modules', 'dist', '.pytest_cache', '.venv', '.git'}
# Gmail inspects file extensions inside archives as well as at the top level.
BLOCKED = set('.ade .adp .apk .appx .appxbundle .bat .cab .chm .cmd .com .cpl .diagcab .diagcfg .diagpkg .dll .dmg .ex .ex_ .exe .hta .img .ins .iso .isp .jar .jnlp .js .jse .lib .lnk .mde .mjs .msc .msi .msix .msixbundle .msp .mst .nsh .pif .ps1 .scr .sct .shb .sys .vb .vbe .vbs .vhd .vxd .wsc .wsf .wsh .xll'.split())
CONVERT_TO_TS = {
    'frontend/vite.config.js': 'frontend/vite.config.ts',
    'frontend/src/main.js': 'frontend/src/main.ts',
    'frontend/src/api.js': 'frontend/src/api.ts',
    'frontend/src/markdown.js': 'frontend/src/markdown.ts',
    'frontend/src/App.test.js': 'frontend/src/App.test.ts',
}


def main():
    contents = {}
    paths = [ROOT / name for name in FILES]
    for directory in DIRECTORIES:
        for base, dirs, names in os.walk(ROOT / directory):
            dirs[:] = [name for name in dirs if name not in EXCLUDED_DIRS]
            paths.extend(Path(base) / name for name in names if Path(name).suffix not in {'.pyc', '.pyo'})
    for path in sorted(set(paths)):
        if not path.is_file():
            raise FileNotFoundError(path)
        relative = path.relative_to(ROOT).as_posix()
        if relative in {'static/app.js', 'scripts/package_demo.py',
                        'scripts/start_demo.ps1', 'scripts/stop_demo.ps1'}:
            continue
        if relative in CONVERT_TO_TS:
            contents[CONVERT_TO_TS[relative]] = path.read_bytes()
            continue
        if path.suffix.lower() in BLOCKED:
            raise ValueError(f'Unhandled Gmail-blocked file: {relative}')
        if relative == 'frontend/index.html':
            text = path.read_text(encoding='utf-8').replace('/src/main.js', '/src/main.ts')
            contents[relative] = text.encode('utf-8')
        elif relative == 'static/index.html':
            # Preserve the legacy static fallback without distributing a separate JS file.
            html = path.read_text(encoding='utf-8')
            script = (ROOT / 'static/app.js').read_text(encoding='utf-8')
            marker = '<script src="/static/app.js" defer></script>'
            if marker not in html or '</script' in script.lower():
                raise ValueError('Legacy static script cannot be safely embedded')
            contents[relative] = html.replace(marker, '<script defer>\n' + script + '\n</script>').encode('utf-8')
        else:
            contents[relative] = path.read_bytes()

    example = (ROOT / '.env.example').read_text(encoding='utf-8')
    contents['.env.example'] = example.encode('utf-8')
    contents['.env'] = example.replace('PICKLE_API_KEY=', 'PICKLE_API_KEY=YOUR_PICKLE_API_KEY', 1).encode('utf-8')
    contents['README.md'] = (ROOT / 'README_EMAIL.md').read_bytes()
    if any(Path(name).suffix.lower() in BLOCKED for name in contents):
        raise ValueError('Blocked file type found in the email package')
    with ZipFile(OUTPUT, 'w', ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in sorted(contents.items()):
            archive.writestr('academic_chat/' + name, data)
    print(f'Created {OUTPUT} ({OUTPUT.stat().st_size:,} bytes). .env contains only an example key.')


if __name__ == '__main__':
    main()
