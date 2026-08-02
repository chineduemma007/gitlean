import sys
from backend.main import run_server

def main():
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port=port)

if __name__ == "__main__":
    main()
