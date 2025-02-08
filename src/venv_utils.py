import subprocess
import sys
import venv
from pathlib import Path

from src.utils import check_dependencies


def create_venv(base_dir):
    """Create a virtual environment in the project directory"""
    venv_path = Path(base_dir) / ".venv"
    if not venv_path.exists():
        print(f"Creating virtual environment at {venv_path}...")
        venv.create(venv_path, with_pip=True)
    return venv_path


def get_venv_python(venv_path):
    """Get the Python executable path from the virtual environment"""
    if sys.platform == "win32":
        python_path = venv_path / "Scripts" / "python.exe"
    else:
        python_path = venv_path / "bin" / "python"
    return python_path


def is_venv_active():
    """Check if we're running in a virtual environment"""
    return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)


def setup_environment(project_dir):
    """Set up and activate virtual environment if needed"""
    venv_path = Path(project_dir) / ".venv"

    # If we're already in the correct venv, no need to do anything
    if is_venv_active() and Path(sys.prefix) == venv_path:
        return True

    if not venv_path.exists():
        venv_path = create_venv(project_dir)

    python_path = get_venv_python(venv_path)
    if not python_path.exists():
        print(f"Error: Virtual environment Python not found at {python_path}")
        return False

    return str(python_path)


def install_dependencies_in_venv(python_path, packages):
    """Install dependencies in the virtual environment"""
    try:
        subprocess.check_call([str(python_path), "-m", "pip", "install"] + packages)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        return False


def run_in_venv(python_path, script_path, *args):
    """Run a Python script in the virtual environment"""
    try:
        cmd = [str(python_path), str(script_path)] + list(args)
        subprocess.check_call(cmd)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running script: {e}")
        return False


def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <path_to_ui_file.py>")
        sys.exit(1)

    ui_file = Path(sys.argv[1])
    if not ui_file.exists():
        print(f"Error: UI file '{ui_file}' not found")
        sys.exit(1)

    project_dir = ui_file.parent
    python_path = setup_environment(project_dir)

    if not python_path:
        print("Failed to set up virtual environment")
        sys.exit(1)

    # Check and install dependencies
    missing_packages = check_dependencies()

    if missing_packages:
        print("Installing missing dependencies in virtual environment...")
        if not install_dependencies_in_venv(python_path, missing_packages):
            print("Failed to install dependencies")
            sys.exit(1)

    # Run the hot reload script in the virtual environment
    if not run_in_venv(python_path, ui_file):
        print("Failed to start UI")
        sys.exit(1)


if __name__ == "__main__":
    main()
