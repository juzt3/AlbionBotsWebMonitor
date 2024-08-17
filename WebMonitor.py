# Python modules.
import datetime
import pandas as pd
import numerize.numerize
# FastAPI modules.
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

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
def frontend(request: Request):
    bots = database.fetch_all_bots()
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


@web_monitor.get("/bot_details/{bot_name}")
def bot_details(request: Request, bot_name: str):
    details = database.fetch_bot_details(bot_name)
    current_year = datetime.datetime.now().year
    transactions = database.fetch_transactions_by_year(bot_name, current_year)
    total_this_year, avg = data_tratment.calculate_total_per_month(transactions)
    clp_avg = avg / 1000000 * 450

    last_month_silver = list(total_this_year.values())[-1]
    date_now = datetime.datetime.now()
    data_this_month = database.fetch_transactions_by_month(bot_name, date_now.year, date_now.month, group_by_day=True)
    first_entry_day = pd.to_datetime(data_this_month.iloc[0].date).day

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
        "avg_this_month": avg_this_month,
        "data_this_month": data_this_month
    })


@web_monitor.put("/update_temp/{bot_name}/{new_temp}")
def update_temp(bot_name: str, new_temp: int):
    database.update_temp(bot_name, new_temp)


@web_monitor.post("/add")
async def add(request: Request):
    form_data = await request.form()
    name = form_data['name']
    ip = form_data['ip']
    database.insert_bot(name, ip, 0, "Unknown")
    return RedirectResponse("/", 303)


@web_monitor.post("/delete/{name}")
def delete(name: str):
    database.delete_bot(name)
    return RedirectResponse("/", 303)


@web_monitor.put("/login_bot/{name}")
def login_bot(name: str, details: LoginSchema):
    bot_id = database.get_bot_id(name)
    if bot_id is not None:
        database.update_bot(name, details.ip, details.temp, details.gathering_map)
    else:
        database.insert_bot(name, details.ip, 0, details.gathering_map)
        database.insert_transaction(0, name)


@web_monitor.post("/send_frame_from_string/{stream_id}")
async def send_frame_from_string(stream_id: str, d: InputImgSchema):
    await fs.send_frame(stream_id, d.img_base64str)


@web_monitor.post("/add_transaction/{bot_name}/{quantity}")
def add_transaction(bot_name: str, quantity: int):
    database.insert_transaction(quantity, bot_name)


@web_monitor.get("/video_feed/{stream_id}")
def video_feed(stream_id: str):
    return fs.get_stream(stream_id, freq=5)


@web_monitor.get("/base64_stream")
def base64_stream():
    return StreamingResponse(fs.base64_mix_generator(database.fetch_bots_name(), fps=5), media_type="multipart/x-mixed-replace;boundary=frame", status_code=206)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(web_monitor, host='0.0.0.0', port=8082)
