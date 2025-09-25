# Python modules.
import datetime
import pandas as pd
import numerize.numerize
# FastAPI modules.
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from typing import Optional

# Own Modules
import database
import data_tratment
from streamer import FrameStreamer
from schemas.login import LoginSchema
from schemas.image import InputImgSchema

web_monitor = FastAPI()
web_monitor.mount("/styles", StaticFiles(directory="styles"), name="styles")
web_monitor.mount("/js", StaticFiles(directory="js"), name="js")
web_monitor.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
fs = FrameStreamer()


@web_monitor.get("/")
async def frontend(request: Request):
    bots = await database.fetch_all_bots()
    bots = sorted(bots, key=lambda x: x['name'])
    images_url = dict()
    for bot in bots:
        local_ip = bot['local_ip']
        images_url[local_ip] = f'{local_ip}:8082/client'

    header = {"Cache-Control": "no-cache, no-store, must-revalidate",
              "Pragma": "no-cache",
              "Expires": "0"
              }

    return templates.TemplateResponse(
        "home.html",
        {"request": request, "bots": bots, "images_url": images_url},
        headers=header
    )


@web_monitor.get("/bot_details/")
@web_monitor.get("/bot_details/{bot_name}")
async def bot_details(request: Request, bot_name: Optional[str] = None):
    # Si bot_name es None, obtendremos los detalles de todos los bots
    details = await database.fetch_bot_details(bot_name) if bot_name else {}

    current_year = datetime.datetime.now().year
    # Si bot_name es None, devolverá las transacciones de todos los bots
    transactions = await database.fetch_transactions_by_year(current_year, bot_name)

    total_this_year, avg = data_tratment.calculate_total_per_month(transactions)
    clp_avg = round(avg / 1000000 * 450)

    if len(list(total_this_year.values())) > 0:
        last_month_silver = list(total_this_year.values())[-1]
        date_now = datetime.datetime.now()
        # Mismo comportamiento para las transacciones del mes
        data_this_month = await database.fetch_transactions_by_month(
            date_now.year, date_now.month, bot_name, group_by_day=True
        )
        first_entry_day = pd.to_datetime(data_this_month.iloc[0].date).day

        try:
            avg_this_month = last_month_silver / (datetime.datetime.now().day - first_entry_day)
        except ZeroDivisionError:
            avg_this_month = 0
    else:
        avg_this_month = 0
        data_this_month = pd.DataFrame()

    # Numerize
    avg = numerize.numerize.numerize(avg)
    avg_this_month = numerize.numerize.numerize(avg_this_month)

    template = "bot_details.html" if bot_name else "dashboard.html"

    return templates.TemplateResponse(template, {
        "request": request,
        "details": details,
        "total_this_year": total_this_year,
        "avg_year": avg,
        "clp_avg_year": clp_avg,
        "avg_this_month": avg_this_month,
        "data_this_month": data_this_month
    })


@web_monitor.put("/update_temp/{bot_name}/{new_temp}")
async def update_temp(bot_name: str, new_temp: int):
    await database.update_temp(bot_name, new_temp)


@web_monitor.post("/add")
async def add(request: Request):
    form_data = await request.form()
    name = form_data['name']
    ip = form_data['ip']
    await database.insert_bot(name, ip, 0, "Unknown")
    return RedirectResponse("/", 303)


@web_monitor.post("/delete/{name}")
async def delete(name: str):
    await database.delete_bot(name)
    return RedirectResponse("/", 303)


@web_monitor.put("/login_bot/{name}")
async def login_bot(name: str, details: LoginSchema):
    bot_id = await database.get_bot_id(name)
    if bot_id is not None:
        await database.update_bot(name, details.ip, details.temp, details.gathering_map)
    else:
        await database.insert_bot(name, details.ip, 0, details.gathering_map)
        await database.insert_transaction(0, name)


@web_monitor.post("/send_frame_from_string/{stream_id}")
async def send_frame_from_string(stream_id: str, d: InputImgSchema):
    await fs.send_frame(stream_id, d.img_base64str)


@web_monitor.post("/add_transaction/{bot_name}/{quantity}")
async def add_transaction(bot_name: str, quantity: int):
    await database.insert_transaction(quantity, bot_name)


@web_monitor.get("/video_feed/{stream_id}")
def video_feed(stream_id: str):
    return fs.get_stream(stream_id, freq=5)


@web_monitor.get("/base64_stream")
async def base64_stream():
    return StreamingResponse(fs.base64_mix_generator(await database.fetch_bots_name(), fps=5), media_type="multipart/x-mixed-replace;boundary=frame", status_code=206)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(web_monitor, host='0.0.0.0', port=8082)
