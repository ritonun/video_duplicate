# cli.py

import typer

app = typer.Typer()


@app.command()
def run():
    print("ez video-duplicate")
