# Python modules.
import datetime
import multiprocessing

# FastAPI modules.
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

# Uvicorn modules.
import uvicorn

# Own Modules
import database
import data_tratment


web_monitor = FastAPI()
web_monitor.mount("/styles", StaticFiles(directory="styles"), name="styles")
templates = Jinja2Templates(directory="templates")


@web_monitor.get("/")
async def root(request: Request):
    bots = database.fetch_all_bots()

    images_url = dict()
    for bot in bots:
        local_ip = bot['local_ip']
        images_url[local_ip] = f'{local_ip}:8000/client'

    return templates.TemplateResponse("home.html", {"request": request, "bots": bots, "images_url": images_url})


@web_monitor.get("/bot_details/{bot_name}")
async def bot_details(request: Request, bot_name: str):
    details = database.fetch_bot_details(bot_name)
    transactions = database.fetch_all_transactions_from_bot(bot_name)
    avg_this_year = data_tratment.transactions_to_average_per_month(transactions, datetime.datetime.now().year, game_format=False)
    return templates.TemplateResponse("bot_details.html", {"request": request, "details": details, "avg_this_year": avg_this_year})


@web_monitor.put("/update_temp/{bot_name}/{new_temp}")
async def update_temp(bot_name: str, new_temp: int):
    database.update_temp(bot_name, new_temp)


@web_monitor.post("/add")
async def add(request: Request):
    form_data = await request.form()
    name = form_data['name']
    ip = form_data['ip']
    database.insert_bot(name, ip, 0, "Unknown")
    return RedirectResponse("/", 303)


@web_monitor.post("/delete/{name}")
async def delete(request: Request, name: str):
    database.delete_bot(name)
    return RedirectResponse("/", 303)


@web_monitor.post("/add_transaction/{bot_name}/{quantity}")
async def add_transaction(bot_name: str, quantity: int):
    database.insert_transaction(quantity, bot_name)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    uvicorn.run(
        "WebMonitor:web_monitor",
        host="0.0.0.0",
        port=8082,
        reload=True,
        log_level="debug"
    )
