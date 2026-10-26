"""
setup_env.py — Hardware-aware environment bootstrapper and dependency installer for LM-Arena.

Uses only Python standard library modules at startup so it can execute inside a brand-new
virtual environment before any third-party packages are installed.
"""

import glob
import hashlib
import importlib.util
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REQUIREMENTS_FILE = BASE_DIR / "requirements.txt"
ENV_FILE = BASE_DIR / ".env"
ENV_EXAMPLE_FILE = BASE_DIR / ".env.example"
STAMP_FILE = Path(sys.prefix) / ".arena_install_stamp"
CUSTOM_NODES_DIR = BASE_DIR / "core" / "comfy_engine" / "custom_nodes"

# ComfyUI custom node packs required by FaceDetailer workflows
CUSTOM_NODE_PACKS = {
    "ComfyUI-Impact-Pack": "429d0159ad429e64d2b3916e6e7be9c22d025c3c",
    "ComfyUI-Impact-Subpack": "50c7b71a6a224734cc9b21963c6d1926816a97f1",
}

REQUIRED_IMPORT_SPECS = (
    "flask",
    "dotenv",
    "sentence_transformers",
    "kokoro_onnx",
    "soundfile",
    "bs4",
    "requests",
    "httpx",
    "primp",
    "PIL",
    "numpy",
    "OpenSSL",
    "cryptography",
    "psutil",
    "markdownify",
    "pypdf",
    "docx",
    "openpyxl",
    "ddgs",
    "musicbrainzngs",
    "webview",
    "faster_whisper",
    "torch",
    "torchvision",
    "torchaudio",
    "transformers",
    "diffusers",
    "safetensors",
    "accelerate",
    "einops",
    "torchsde",
    "scipy",
    "kornia",
    "aiohttp",
    "yaml",
    "tqdm",
    "ultralytics",
    "segment_anything",
    "skimage",
    "cv2",
    "piexif",
    "dill",
    "matplotlib",
)


def detect_gpu_vendor() -> str:
    """Detects GPU vendor ('nvidia', 'amd', 'intel', 'apple', or 'cpu')."""
    if sys.platform == "darwin":
        return "apple"

    if os.name == "nt":
        try:
            out = subprocess.check_output(
                'powershell -NoProfile -Command "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"',
                shell=True,
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=5.0,
            ).lower()
            if "nvidia" in out:
                return "nvidia"
            if "amd" in out or "radeon" in out:
                return "amd"
            if "intel" in out or "arc" in out:
                return "intel"
        except Exception:
            pass

    try:
        subprocess.check_output(["nvidia-smi"], stderr=subprocess.DEVNULL, timeout=3.0)
        return "nvidia"
    except Exception:
        pass

    return "cpu"


def ensure_directories_and_env() -> None:
    """Creates required runtime directories and seeds .env from .env.example if missing."""
    required_dirs = [
        BASE_DIR / "models" / "llm",
        BASE_DIR / "models" / "checkpoints",
        BASE_DIR / "models" / "loras",
        BASE_DIR / "models" / "vae",
        BASE_DIR / "models" / "ultralytics" / "bbox",
        BASE_DIR / "logs",
        BASE_DIR / "certs",
        BASE_DIR / "core" / "followers",
        BASE_DIR / "core" / "lorebooks",
        BASE_DIR / "variables" / "saves",
    ]
    for d in required_dirs:
        d.mkdir(parents=True, exist_ok=True)

    if not ENV_FILE.exists() and ENV_EXAMPLE_FILE.exists():
        shutil.copy(ENV_EXAMPLE_FILE, ENV_FILE)
        print("[Setup] Created default .env configuration from .env.example")


def compute_req_digest() -> str:
    """Computes a short SHA-256 digest of requirements.txt."""
    req_bytes = REQUIREMENTS_FILE.read_bytes() if REQUIREMENTS_FILE.exists() else b""
    return hashlib.sha256(req_bytes).hexdigest()[:16]


def compute_stamp(gpu_vendor: str) -> str:
    """Computes a fingerprint of requirements.txt, Python version, and GPU vendor."""
    digest = compute_req_digest()
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    return f"py={py_ver}|gpu={gpu_vendor}|req={digest}"


def core_imports_healthy() -> bool:
    """Fast metadata check (<2ms) that critical runtime packages are installed."""
    return all(importlib.util.find_spec(mod) is not None for mod in REQUIRED_IMPORT_SPECS)


def is_stamp_valid() -> bool:
    """Checks if the existing install stamp matches current Python version and requirements.txt."""
    if not STAMP_FILE.exists():
        return False
    try:
        stamp = STAMP_FILE.read_text(encoding="utf-8").strip()
        py_ver = f"py={sys.version_info.major}.{sys.version_info.minor}"
        req_part = f"req={compute_req_digest()}"
        return py_ver in stamp and req_part in stamp and core_imports_healthy()
    except Exception:
        return False


def install_dependencies(force: bool = False) -> None:
    """Installs hardware-matched PyTorch and requirements.txt when needed."""
    if not force and is_stamp_valid():
        print("[Setup] Dependencies verified and up to date.")
        return

    gpu_vendor = detect_gpu_vendor()
    expected_stamp = compute_stamp(gpu_vendor)

    print(f"[Setup] Configuring environment for detected GPU backend: {gpu_vendor.upper()}")
    python_exe = sys.executable

    def run_pip(args: list[str]) -> None:
        cmd = [python_exe, "-m", "pip"] + args
        subprocess.check_call(cmd)

    # Upgrade base packaging tools
    try:
        run_pip(["install", "--upgrade", "pip", "setuptools", "wheel", "-q"])
    except Exception:
        pass

    # Install hardware-matched PyTorch
    if gpu_vendor == "nvidia":
        print("[Setup] Installing PyTorch with CUDA 12.4 acceleration...")
        run_pip([
            "install",
            "torch==2.4.1",
            "torchvision==0.19.1",
            "torchaudio==2.4.1",
            "--index-url",
            "https://download.pytorch.org/whl/cu124",
        ])
    elif gpu_vendor in ("amd", "intel") and os.name == "nt":
        print(f"[Setup] Installing PyTorch with DirectML acceleration for Windows {gpu_vendor.upper()}...")
        run_pip([
            "install",
            "torch==2.4.1",
            "torchvision==0.19.1",
            "torchaudio==2.4.1",
            "torch-directml",
        ])
    else:
        print("[Setup] Installing standard PyTorch build...")
        run_pip([
            "install",
            "torch==2.4.1",
            "torchvision==0.19.1",
            "torchaudio==2.4.1",
        ])

    # Install remaining requirements
    print("[Setup] Installing core application dependencies from requirements.txt...")
    run_pip(["install", "-r", str(REQUIREMENTS_FILE)])

    try:
        STAMP_FILE.write_text(expected_stamp, encoding="utf-8")
    except Exception:
        pass
    print("[Setup] Python dependencies installed successfully.")


def ensure_ssl_certificates() -> None:
    """Generates self-signed SSL certificates in certs/ if USE_HTTPS=true and certs are missing."""
    cert_path = BASE_DIR / "certs" / "cert.pem"
    key_path = BASE_DIR / "certs" / "key.pem"
    if cert_path.exists() and key_path.exists():
        return

    try:
        import datetime
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "LM-Arena Local"),
        ])
        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=3650))
            .sign(key, hashes.SHA256())
        )
        cert_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_bytes(
            key.byte_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
            if hasattr(key, "byte_bytes")
            else key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        print("[Setup] Generated local self-signed HTTPS certificate in certs/cert.pem")
    except Exception as e:
        print(f"[Setup] Note: Could not pre-generate SSL cert ({e})")


def ensure_llama_server_binary() -> None:
    """Ensures the prebuilt llama-server binary matching the host GPU is downloaded and detects a GPU."""
    try:
        from runners import local_server
        gpu_type = local_server.detect_gpu_type()
        gpu_type_file = os.path.join(local_server.LLAMA_BIN_DIR, "installed_gpu_type.txt")
        installed_type = ""
        if os.path.exists(gpu_type_file):
            try:
                with open(gpu_type_file, "r", encoding="utf-8") as f:
                    installed_type = f.read().strip()
            except Exception:
                pass

        if (
            os.path.exists(local_server.SERVER_EXE)
            and installed_type == gpu_type
            and (not hasattr(local_server, "has_gpu_devices") or local_server.has_gpu_devices())
        ):
            return

        print(f"[Setup] Downloading prebuilt llama-server binary for your GPU ({gpu_type})...")
        if hasattr(local_server, "stop_local_server"):
            local_server.stop_local_server()
        if local_server.download_llama_server():
            with open(gpu_type_file, "w", encoding="utf-8") as f:
                f.write(gpu_type)
    except Exception as e:
        print(f"[Setup] Note: llama-server will be downloaded on first model load ({e})")


def ensure_custom_nodes() -> None:
    """Downloads the ComfyUI custom node packs used by ImageWorkflow.json at pinned commits."""
    import io
    import urllib.request
    import zipfile

    for name, sha in CUSTOM_NODE_PACKS.items():
        target = CUSTOM_NODES_DIR / name
        marker = target / ".arena_commit"
        if marker.exists() and marker.read_text(encoding="utf-8").strip() == sha:
            continue

        print(f"[Setup] Installing custom node pack {name} ({sha[:7]})...")
        url = f"https://github.com/ltdrdata/{name}/archive/{sha}.zip"
        with urllib.request.urlopen(url, timeout=60) as resp:
            archive = zipfile.ZipFile(io.BytesIO(resp.read()))

        if target.exists():
            shutil.rmtree(target)
        CUSTOM_NODES_DIR.mkdir(parents=True, exist_ok=True)
        archive.extractall(CUSTOM_NODES_DIR)
        (CUSTOM_NODES_DIR / f"{name}-{sha}").rename(target)
        marker.write_text(sha, encoding="utf-8")


def ensure_detector_models() -> None:
    """Downloads the face detector model used by ImageWorkflow.json's FaceDetailer."""
    import urllib.request

    target = BASE_DIR / "models" / "ultralytics" / "bbox" / "face_yolov8m.pt"
    if target.exists():
        return
    print("[Setup] Downloading face detector model (face_yolov8m.pt)...")
    partial = target.with_suffix(".part")
    urllib.request.urlretrieve("https://huggingface.co/Bingsu/adetailer/resolve/main/face_yolov8m.pt", partial)
    partial.rename(target)


def main() -> int:
    force = "--force" in sys.argv or "--update" in sys.argv
    ensure_directories_and_env()
    install_dependencies(force=force)
    ensure_custom_nodes()
    ensure_detector_models()
    ensure_ssl_certificates()
    ensure_llama_server_binary()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
