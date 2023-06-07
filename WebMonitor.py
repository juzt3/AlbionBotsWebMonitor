# Python modules.
import multiprocessing
import json

# FastAPI modules.
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

# Uvicorn modules.
import uvicorn


web_monitor = FastAPI()
templates = Jinja2Templates(directory="templates")
direcciones_guardadas = None
imagenes_url = dict()

try:
    with open("bots_ips.json", "r") as file:
        direcciones_guardadas = json.load(file)
    file.close()
except FileNotFoundError:
    direcciones_guardadas = dict()


@web_monitor.get("/")
async def root(request: Request):
    direcciones = json.dumps(direcciones_guardadas)
    direcciones_json = json.loads(direcciones)

    for name, ip in direcciones_guardadas.items():
        imagenes_url[ip] = f'{ip}:8000/client'

    return templates.TemplateResponse("home.html", {"request": request, "bots": direcciones_json, "images_url": imagenes_url})


@web_monitor.post("/add")
async def add(request: Request):
    form_data = await request.form()
    name = form_data['name']
    ip = form_data['ip']
    direcciones_guardadas[name] = ip
    with open("bots_ips.json", "w") as outfile:
        json.dump(direcciones_guardadas, outfile)
    outfile.close()
    return RedirectResponse("/", 303)


@web_monitor.get("/delete/{name}")
async def delete(request: Request, name: str):
    del direcciones_guardadas[name]
    with open("bots_ips.json", "w") as outfile:
        json.dump(direcciones_guardadas, outfile)
    outfile.close()
    return RedirectResponse("/", 303)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    uvicorn.run(
        "WebMonitor:web_monitor",
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level="debug"
    )
