import logging
import webview

from contextlib import redirect_stdout
from io import StringIO
from src.server import app

logger = logging.getLogger(__name__)


def run():
    stream = StringIO()
    primary_screen = webview.screens[0]
    width = 340
    height = 480
    padding = 10
    with redirect_stdout(stream):
        webview.create_window(
            "Timelog Commander",
            app,
            on_top=True,
            confirm_close=True,
            width=width,
            height=height,
            frameless=True,
            background_color="#D1D5DB",
            x=primary_screen.width - (width + padding),
            y=primary_screen.height - (height + padding),
        )
        webview.start(debug=True)


if __name__ == "__main__":
    run()
