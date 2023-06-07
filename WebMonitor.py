# Python modules.
import multiprocessing
import json

# FastAPI modules.
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

# Uvicorn modules.
import uvicorn

# Own Modules
import database


web_monitor = FastAPI()
templates = Jinja2Templates(directory="templates")


@web_monitor.get("/")
async def root(request: Request):
    bots = database.fetch_all_bots()

    images_url = dict()
    for bot in bots:
        local_ip = bot['local_ip']
        images_url[local_ip] = f'{local_ip}:8000/client'

    return templates.TemplateResponse("home.html", {"request": request, "bots": bots, "images_url": images_url})


@web_monitor.post("/add")
async def add(request: Request):
    form_data = await request.form()
    name = form_data['name']
    ip = form_data['ip']
    database.insert_bot(name, ip, 0, "Unknown")
    return RedirectResponse("/", 303)


@web_monitor.get("/delete/{name}")
async def delete(request: Request, name: str):
    database.delete_bot(name)
    return RedirectResponse("/", 303)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    uvicorn.run(
        "WebMonitor:web_monitor",
        host="0.0.0.0",
        port=8082,
        reload=True,
        log_level="debug"
    )
