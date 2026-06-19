# LinkGuard

Lightweight desktop app to batch-scan URLs and detect link rot.

## Setup
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python src/main.py
```

## Build Executable
```bash
pyinstaller LinkGuard.spec
```

Outputs: `dist/LinkGuard.exe` (Windows) or `dist/LinkGuard.app` (macOS).
