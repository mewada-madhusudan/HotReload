import sys
import importlib
import subprocess


def check_dependencies():
    required_packages = {
        'PyQt6': 'PyQt6>=6.0.0',
        'watchdog': 'watchdog>=2.1.0'
    }

    missing_packages = []

    for package, requirement in required_packages.items():
        try:
            importlib.import_module(package)
        except ImportError:
            missing_packages.append(requirement)

    return missing_packages


def install_dependencies(packages):
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + packages)
        return True
    except subprocess.CalledProcessError:
        return False