# -*- mode: python ; coding: utf-8 -*-
#
# AirTouch PyInstaller build.  From the project root (with the venv active):
#
#     python -m PyInstaller --noconfirm --clean AirTouch.spec
#
# Output: dist/AirTouch/AirTouch.exe (+ _internal/). Zip the dist/AirTouch
# folder to distribute it.
#
# The libraries below ship many files AirTouch never uses (video codecs,
# face/pose models, Qt Quick, test suites...). They are filtered out at the
# end of the Analysis step, which cuts roughly 120 MB from the folder.
import re

from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []
for package in ('mediapipe', 'cv2', 'matplotlib'):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

# MediaPipe's own unit tests are not needed at runtime.
hiddenimports = [name for name in hiddenimports if not name.endswith('_test')]


a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'jax', 'jaxlib', 'scipy', 'pandas', 'sklearn',
        # pyautogui only uses these for its optional MouseInfo/message-box
        # tools, and imports them inside try/except.
        'tkinter', '_tkinter', 'mouseinfo', 'pymsgbox',
        # MediaPipe audio / LLM tooling, imported only by unused tasks.
        'sounddevice', 'sentencepiece',
        'matplotlib.tests', 'mpl_toolkits.mplot3d.tests',
        'PySide6.QtWebEngine', 'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets', 'PySide6.QtPdf', 'PySide6.QtQml',
        'PySide6.QtQuick', 'PySide6.QtQuickWidgets', 'PySide6.QtVirtualKeyboard',
        'PySide6.Qt3DCore', 'PySide6.QtMultimedia', 'PySide6.QtCharts',
    ],
    noarchive=False,
    optimize=0,
)

# ---------------------------------------------------------------------------
# Drop files AirTouch never loads.
# ---------------------------------------------------------------------------
UNUSED_FILES = re.compile(
    r'('
    # OpenCV: ffmpeg is only for video files/streams (the webcam uses
    # Windows' own camera APIs); haarcascades are face-detection data.
    r'cv2/opencv_videoio_ffmpeg'
    r'|cv2/data/'
    # Qt: software-OpenGL fallback, translations, and Qt Quick/QML/PDF/
    # virtual keyboard, which a plain widgets app never loads.
    r'|PySide6/opengl32sw\.dll'
    r'|PySide6/translations/'
    r'|PySide6/Qt6(Quick|Qml|Pdf|VirtualKeyboard)[^/]*\.dll'
    r'|PySide6/qml/'
    r'|PySide6/plugins/imageformats/qpdf\.dll'
    r'|PySide6/plugins/platforminputcontexts/'
    # MediaPipe: keep only the hand models (hand_landmark, palm_detection).
    r'|mediapipe/modules/(?!hand_landmark/|palm_detection/)'
    # Pillow's AVIF plugin; matplotlib sample data and test images.
    r'|PIL/_avif'
    r'|matplotlib/mpl-data/sample_data/'
    r'|matplotlib/tests/'
    # Tcl/Tk data, in case tkinter is pulled in some other way.
    r'|_tcl_data/|_tk_data/|tcl8/'
    r'|_sounddevice_data/'
    r')',
    re.IGNORECASE,
)


def keep(entry):
    dest = entry[0].replace('\\', '/')
    return not UNUSED_FILES.search(dest)


a.datas = [entry for entry in a.datas if keep(entry)]
a.binaries = [entry for entry in a.binaries if keep(entry)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AirTouch',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX compression often breaks Qt/OpenCV DLLs and triggers antivirus
    # false positives, so it stays off.
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='AirTouch',
)
