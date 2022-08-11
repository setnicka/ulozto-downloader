#!/usr/bin/env python3

import asyncio
import os
import signal
import urllib.parse
from asyncio import CancelledError
from contextlib import suppress
from multiprocessing import Queue, Process
from os import path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTasks
from starlette.responses import JSONResponse

from uldlib import captcha, const
from uldlib.captcha import AutoReadCaptcha
from uldlib.downloader import Downloader
from uldlib.frontend import NoOpFrontend
from uldlib.segfile import SegFileReader
from uldlib.torrunner import TorRunner

app = FastAPI()

temp_path: str = os.getenv('TEMP_FOLDER', '')
data_folder: str = os.getenv('DATA_FOLDER', '')
download_path: str = os.getenv('DOWNLOAD_FOLDER', '')
default_parts: int = int(os.getenv('PARTS', 10))
auto_delete_downloads: bool = os.getenv('AUTO_DELETE_DOWNLOADS', '0').strip().lower() in ['true', '1', 't', 'y', 'yes']

model_path = path.join(data_folder, const.MODEL_FILENAME)
frontend: NoOpFrontend = NoOpFrontend()
captcha_solve_fnc: AutoReadCaptcha = captcha.AutoReadCaptcha(
    model_path, const.MODEL_DOWNLOAD_URL, frontend)

downloader: Downloader = None
process: Process = None
queue: Queue = None
tor: TorRunner = None
file_data: tuple = None
global_url: str = None


async def generate_stream(request: Request, background_tasks: BackgroundTasks, file_path: str, parts: int):
    download_canceled = False
    try:
        for seg_idx in range(parts):
            reader = SegFileReader(file_path, parts, seg_idx)
            stream_generator = reader.read()
            with suppress(CancelledError):
                async for data in stream_generator:
                    if await request.is_disconnected():
                        download_canceled = True
                        print("Client has closed download connection prematurely...")
                        await stream_generator.aclose()
                        return
                    yield data
    finally:
        if not download_canceled:
            while downloader is not None:
                await asyncio.sleep(0.1)
            background_tasks.add_task(cleanup_stream, file_path)


def downloader_worker(url: str, parts: int, target_dir: str):
    signal.signal(signal.SIGINT, sigint_sub_handler)
    downloader.download(url, parts, target_dir)


def cleanup_stream(file_path: str = None):
    global file_data, global_url
    if file_data is not None:
        file_data = None
    if global_url is not None:
        global_url = None
    if auto_delete_downloads:
        print(f"Cleanup of: {file_path}")
        with suppress(FileNotFoundError):
            os.remove(file_path + const.DOWNPOSTFIX)
            os.remove(file_path + const.CACHEPOSTFIX)
            os.remove(file_path)


def cleanup_download():
    global downloader, process, queue, tor
    if process is not None:
        process.join()
        process = None
    if queue is not None:
        queue.close()
        queue = None
    if tor is not None:
        tor.stop()
        tor = None
    if downloader is not None:
        downloader.terminate()
        downloader = None


@app.get("/initiate", responses={
    200: {"content": {const.MEDIA_TYPE_JSON: {}}, },
    429: {"content": {const.MEDIA_TYPE_JSON: {}}, }
})
async def initiate(background_tasks: BackgroundTasks, url: str, parts: Optional[int] = default_parts):
    global downloader, process, queue, tor, file_data, global_url

    # TODO: What happens when the same url is called twice and parts number changes?
    if global_url is not None and global_url != url:
        return JSONResponse(
            content={"url": f"{url}",
                     "message": "Downloader is busy.. Free download is limited to single download."},
            status_code=429
        )

    if file_data is None:
        global_url = url
        tor = TorRunner(temp_path)
        tor.launch(captcha_solve_fnc.log)
        queue = Queue()
        downloader = Downloader(tor, frontend, captcha_solve_fnc)
        process = Process(target=downloader_worker,
                          args=(url, parts, download_path))
        process.start()

        background_tasks.add_task(cleanup_download)

        file_data = await asyncio.get_event_loop().run_in_executor(None, queue.get)

    file_path = file_data[0]
    filename = file_data[1]
    size = file_data[2]
    parts = file_data[3]

    return JSONResponse(
        content={"url": f"{url}",
                 "filename": f"{filename}",
                 "file_path": f"{file_path}",
                 "size": f"{size}",
                 "parts": f"{parts}",
                 "message": "Downloader has started.."},
        status_code=200
    )


@app.get("/download", responses={
    200: {"content": {const.MEDIA_TYPE_STREAM: {}}, },
    400: {"content": {const.MEDIA_TYPE_JSON: {}}, },
    429: {"content": {const.MEDIA_TYPE_JSON: {}}, }
})
async def download_endpoint(request: Request, background_tasks: BackgroundTasks, url: str):
    global downloader, process, queue

    if file_data is None:
        return JSONResponse(
            content={"url": f"{url}",
                     "message": "Download not initiated."},
            status_code=400
        )
    elif global_url != url:
        return JSONResponse(
            content={"url": f"{url}",
                     "message": "Another download initiated."},
            status_code=429
        )

    file_path = file_data[0]
    filename = file_data[1]
    filename_encoded = urllib.parse.quote_plus(filename)
    size = file_data[2]
    parts = file_data[3]

    return StreamingResponse(
        generate_stream(request, background_tasks, file_path, parts),
        headers={
            "Content-Length": str(size),
            "Content-Disposition": f"attachment; filename=\"{filename_encoded}\"",
        }, media_type=const.MEDIA_TYPE_STREAM)


def sigint_sub_handler(sig, frame):
    downloader.terminate()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
