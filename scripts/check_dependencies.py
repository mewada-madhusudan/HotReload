from src.utils import check_dependencies, install_dependencies


def main():
    missing = check_dependencies()
    if missing:
        print("Missing dependencies:")
        for package in missing:
            print(f"  {package}")

        print("\nAttempting to install...")
        if install_dependencies(missing):
            print("Successfully installed dependencies")
        else:
            print("Failed to install dependencies")
    else:
        print("All dependencies are satisfied")


if __name__ == "__main__":
    main()