import sqlite3
import base64
import time
import cv2
import numpy as np
import imutils
from typing import Union, Any, Mapping
from fastapi import UploadFile, File, BackgroundTasks
from starlette.responses import StreamingResponse
import asyncio

SQLLITE_CONN_STR = "file:framestreamerdb1?mode=memory&cache=shared"


class FrameStreamer:
    """The FrameStreamer class allows you to send frames and visualize them as a stream"""

    def __init__(self):
        self.conn = sqlite3.connect(SQLLITE_CONN_STR, uri=True)
        self._initialize_db()

    def _initialize_db(self):
        with self.conn:
            self.conn.execute('''CREATE TABLE IF NOT EXISTS images (
                                    id TEXT PRIMARY KEY,
                                    image TEXT
                                )''')

    def _get_image(self, img_id: str) -> Union[str, None]:
        """Get an image from the SQLite DB.

        Args:
            img_id (str): ID (primary key) of the image to be retrieved in the DB

        Returns:
            Union[str, None]: Image (in base64) or None if not found
        """
        try:
            with sqlite3.connect(SQLLITE_CONN_STR, uri=True) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT image FROM images WHERE id = ?", (img_id,))
                row = cursor.fetchone()
                return row[0] if row else None
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None

    async def _store_image_str(self, img_id: str, img_str_b64: str) -> None:
        """Store an image string (in base64) to the DB.

        Args:
            img_id (str): ID (primary key) of the image.
            img_str_b64 (str): Image string (in base64)
        """
        try:
            with sqlite3.connect(SQLLITE_CONN_STR, uri=True) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO images (id, image) VALUES (?, ?)", (img_id, img_str_b64))
                conn.commit()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    async def _image_file_to_base64(self, file: UploadFile = File(...)) -> str:
        """Convert a loaded image to Base64

        Args:
            file (UploadFile, optional): Image file to be converted.

        Returns:
            str: Image converted (in Base64)
        """
        image_file = await file.read()
        return base64.b64encode(image_file).decode("utf-8")

    async def send_frame(self, stream_id: str, frame: Union[str, UploadFile, bytes]) -> None:
        """Send a frame to be streamed.

        Args:
            stream_id (str): ID (primary key) of the frame
            frame (Union[str, UploadFile, bytes]): Frame (image) to be streamed.
        """
        if isinstance(frame, str):
            await self._store_image_str(stream_id, frame)
        elif isinstance(frame, UploadFile):
            img_str = await self._image_file_to_base64(frame)
            await self._store_image_str(stream_id, img_str)
        elif isinstance(frame, bytes):
            img_str = base64.b64encode(frame).decode("utf-8")
            await self._store_image_str(stream_id, img_str)

    def _readb64(self, encoded_img: str) -> Any:
        """Decode an image (in base64) to an OpenCV image

        Args:
            encoded_img (str): Image (in base64)

        Returns:
            Any: Image decoded from OpenCV
        """
        if encoded_img is None:
            return None
        nparr = np.frombuffer(base64.b64decode(encoded_img), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img

    def _start_stream(self, img_id: str, freq: int = 30):
        """Continuous loop to stream the frame from SQLite to HTML image/jpeg format

        Args:
            img_id (str): ID (primary key) of the image in the DB
            freq (int, optional): Loop frequency. Defaults to 30.

        Yields:
            bytes: HTML containing the bytes to plot the stream
        """
        sleep_duration = 1.0 / freq

        while True:
            time.sleep(sleep_duration)
            try:
                frame = self._readb64(self._get_image(img_id))
                if frame is None:
                    continue
                frame = imutils.resize(frame, width=680)
                (flag, encodedImage) = cv2.imencode(".jpg", frame)
                if not flag:
                    continue
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')
            except Exception as e:
                print(f"Error during streaming: {e}")
                continue

    def get_stream(self, stream_id: str, freq: int = 30, status_code: int = 206,
                   headers: Union[Mapping[str, str], None] = None,
                   background: Union[BackgroundTasks, None] = None) -> StreamingResponse:
        """Get a stream of frames

        Args:
            stream_id (str): ID (primary key) of the stream to be retrieved
            freq (int, optional): Frequency of the continuous loop retrieval (in Hz). Defaults to 30.
            status_code (int, optional): HTTP response status code. Defaults to 206.
            headers (Union[Mapping[str, str], None], optional): HTTP headers. Defaults to None.
            background (Union[BackgroundTasks, None], optional): FastAPI background. Defaults to None.

        Returns:
            StreamingResponse: FastAPI StreamingResponse
        """
        return StreamingResponse(self._start_stream(stream_id, freq),
                                 media_type="multipart/x-mixed-replace;boundary=frame",
                                 status_code=status_code,
                                 headers=headers,
                                 background=background)

    async def base64_mix_generator(self, bots_names, fps=15):
        sleep_duration = 1.0 / fps
        while True:
            await asyncio.sleep(sleep_duration)
            mix = ''
            for bot in bots_names:
                stream_id = bot['name']
                try:
                    # Obtiene la imagen en base64
                    base64_frame = self._get_image(stream_id)

                    # Decodifica la imagen
                    frame = self._readb64(base64_frame)
                except (ValueError, cv2.error) as e:
                    print(f"Error procesando la imagen de {stream_id}: {e}")
                    continue

                if frame is None:
                    continue

                # Redimensiona y codifica la imagen
                output_frame = imutils.resize(frame, width=680)
                if output_frame is None:
                    continue

                flag, encodedImage = cv2.imencode(".jpg", output_frame)
                if not flag:
                    continue

                mix += f"{stream_id}:{base64_frame}\n"

            # Elimina el último '\n'
            mix = mix.rstrip('\n')
            yield mix
