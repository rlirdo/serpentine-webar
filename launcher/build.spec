# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 規格檔：onefile、無主控台視窗，遊戲網頁完整打包在 exe 內的 web/ 之下。
# 用法（repo 根目錄）：
#   python -m PyInstaller --noconfirm --clean --distpath launcher/dist --workpath launcher/build launcher/build.spec
# 產出 launcher/dist/SerpentineWebAR.exe，再改名為「墨玉晶格修復任務WebAR.exe」（避免 PyInstaller 處理中文檔名）。
from pathlib import Path

from PIL import Image

HERE = Path(SPECPATH).resolve()
ROOT = HERE.parent
BUILD = HERE / "build"
BUILD.mkdir(exist_ok=True)

# assets/icon.png → icon.ico（多尺寸）
ICO = BUILD / "icon.ico"
Image.open(ROOT / "assets" / "icon.png").convert("RGBA").save(
    ICO, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (192, 192)])

# 要打包的網站檔案（不含 tools/、launcher 原始碼、.git）
datas = [(str(HERE / "launcher.html"), "web")]
for name in ("index.html", "ar.html", "play.html", "card.html", "teacher.html"):
    datas.append((str(ROOT / name), "web"))
for d in ("css", "js", "assets", "vendor"):
    for p in (ROOT / d).rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts:
            datas.append((str(p), str(Path("web") / p.parent.relative_to(ROOT))))

a = Analysis(
    [str(HERE / "launcher.py")],
    pathex=[str(HERE)],
    datas=datas,
    hiddenimports=[],
    excludes=["numpy", "PIL", "matplotlib", "pandas", "scipy", "cv2", "fitz", "docx", "win32com", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SerpentineWebAR",
    icon=str(ICO),
    console=False,
    debug=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    version=None,
)
