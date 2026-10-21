import sys
from src.ui import launch_app
from src.cli import run_cli

def main():
    if len(sys.argv) > 1 and sys.argv[1].lower() in ["--cli", "-c"]:
        # Remove --cli from argv and run CLI
        sys.argv.pop(1)
        run_cli()
    else:
        launch_app()

if __name__ == "__main__":
    main()
