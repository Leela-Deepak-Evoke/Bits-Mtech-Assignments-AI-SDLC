"""``python -m todo.interfaces.api`` starts the server."""

from todo.interfaces.api.app import serve

if __name__ == "__main__":
    serve()
