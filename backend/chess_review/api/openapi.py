import json

from chess_review.api.app import create_app_from_env


def main() -> None:
    print(json.dumps(create_app_from_env().openapi(), indent=2))


if __name__ == "__main__":
    main()
