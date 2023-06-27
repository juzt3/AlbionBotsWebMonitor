# Python modules.
import asyncio
import datetime
import pandas as pd
from pydantic import BaseModel
import numerize.numerize
# FastAPI modules.
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi_frame_stream import FrameStreamer

# Uvicorn modules.
import uvicorn

# Own Modules
import database
import data_tratment

web_monitor = FastAPI()
web_monitor.mount("/styles", StaticFiles(directory="styles"), name="styles")
templates = Jinja2Templates(directory="templates")
fs = FrameStreamer()


@web_monitor.get("/")
async def root(request: Request):
    bots = database.fetch_all_bots()
    images_url = dict()
    for bot in bots:
        local_ip = bot['local_ip']
        images_url[local_ip] = f'{local_ip}:8000/client'

    header = {"Cache-Control": "no-cache, no-store, must-revalidate",
              "Pragma": "no-cache",
              "Expires": "0"
              }

    return templates.TemplateResponse(
        "home.html",
        {"request": request, "bots": bots, "images_url": images_url},
        headers=header
    )


@web_monitor.get("/bot_details/{bot_name}")
async def bot_details(request: Request, bot_name: str):
    details = database.fetch_bot_details(bot_name)
    current_year = datetime.datetime.now().year
    transactions = database.fetch_transactions_by_year(bot_name, current_year)
    total_this_year, avg = data_tratment.calculate_total_per_month(transactions)
    clp_avg = avg / 1000000 * 450

    last_month_silver = list(total_this_year.values())[-1]
    date_now = datetime.datetime.now()
    first_entry_day = pd.to_datetime(
        database.fetch_transactions_by_month(bot_name, date_now.year, date_now.month).iloc[0].date
    ).day

    try:
        avg_this_month = last_month_silver / (datetime.datetime.now().day - first_entry_day)
    except ZeroDivisionError:
        avg_this_month = 0

    # Numerize
    avg = numerize.numerize.numerize(avg)
    avg_this_month = numerize.numerize.numerize(avg_this_month)

    return templates.TemplateResponse("bot_details.html", {
        "request": request,
        "details": details,
        "total_this_year": total_this_year,
        "avg_year": avg,
        "clp_avg_year": clp_avg,
        "avg_this_month": avg_this_month
    })


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


@web_monitor.put("/login_bot/{name}/{local_ip}/{temp}/{gathering_map}")
async def login_bot(name: str, local_ip: str, temp: int, gathering_map: str):
    bot_id = database.get_bot_id(name)
    if bot_id:
        database.update_bot(name, local_ip, temp, gathering_map)
    else:
        database.insert_bot(name, local_ip, temp, gathering_map)


class InputImg(BaseModel):
    img_base64str: str


@web_monitor.post("/send_frame_from_string/{stream_id}")
async def send_frame_from_string(stream_id: str, d: InputImg):
    await fs.send_frame(stream_id, d.img_base64str)


@web_monitor.get("/video_feed/{stream_id}")
async def video_feed(stream_id: str):
    return fs.get_stream(stream_id, freq=15)


@web_monitor.post("/add_transaction/{bot_name}/{quantity}")
async def add_transaction(bot_name: str, quantity: int):
    database.insert_transaction(quantity, bot_name)


async def base64_mix_generator(fps=15):
    bots_names = database.fetch_bots_name()
    while True:
        mix = ''
        for bot in bots_names:
            stream_id = bot['name']
            base64_frame = fs._get_image(stream_id)
            if base64_frame is not None:
                mix += f"{stream_id}:{base64_frame}\n"
        yield mix
        await asyncio.sleep(1/fps)


@web_monitor.get("/base64_stream")
async def base64_stream():
    return StreamingResponse(base64_mix_generator(), media_type="text/plain", status_code=206)


if __name__ == "__main__":
    uvicorn.run(
        "WebMonitor:web_monitor",
        host="0.0.0.0",
        port=8084,
        log_level="debug"
    )
