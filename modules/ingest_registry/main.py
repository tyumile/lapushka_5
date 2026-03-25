from app.bootstrap import create_server


def main() -> None:
    server = create_server()
    server.serve_forever()


if __name__ == "__main__":
    main()
