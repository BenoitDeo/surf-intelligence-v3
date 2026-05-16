import json

from dotenv import load_dotenv

from engine.router import get_best_spot


if __name__ == "__main__":
    load_dotenv()
    print(json.dumps(get_best_spot(), indent=2))
