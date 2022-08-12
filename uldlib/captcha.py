from abc import abstractmethod
import threading
import time
from typing import Dict
import requests
from PIL import Image
from io import BytesIO
from uldlib.frontend import Frontend
import importlib.util

from uldlib.utils import LogLevel


class CaptchaSolver():
    frontend: Frontend
    cannot_solve: bool = False

    def __init__(self, frontend: Frontend):
        self.frontend = frontend

    def log(self, msg: str, level: LogLevel = LogLevel.INFO):
        self.frontend.captcha_log(msg, level)

    def stats(self, stats: Dict[str, int]):
        self.frontend.captcha_stats(stats)

    @abstractmethod
    def solve(self, img_url: str, stop_event: threading.Event = None) -> str:
        pass


class Dummy(CaptchaSolver):
    """Dumy solver when tflite_runtime or full tensorflow nor tkinter available."""

    def __init__(self, frontend):
        super().__init__(frontend)
        self.cannot_solve = True

    def solve(self, img_url, stop_event):
        pass


class ManualInput(CaptchaSolver):
    """Display captcha from given URL and ask user for input in GUI window."""

    def __init__(self, frontend):
        super().__init__(frontend)

    def solve(self, img_url: str, stop_event: threading.Event = None) -> str:
        import tkinter as tk
        from PIL import ImageTk

        root = tk.Tk()
        root.focus_force()
        root.title("Opiš kód z obrázku")
        # use width x height + x_offset + y_offset (no spaces!)
        root.geometry("300x140")

        def disable_event():
            pass

        root.protocol("WM_DELETE_WINDOW", disable_event)

        u = requests.get(img_url)
        raw_data = u.content

        im = Image.open(BytesIO(raw_data))
        photo = ImageTk.PhotoImage(im)
        label = tk.Label(image=photo)
        label.image = photo
        label.pack()

        entry = tk.Entry(root)
        entry.pack()
        entry.bind('<Return>', lambda event: root.quit())
        entry.focus()

        tk.Button(root, text='Send', command=root.quit).pack()

        # Closing of the window separated to thread because it can be closed by
        # the user input (done==True) or by the terminating application (stop_event)
        done = False

        def stop_func():
            while True:
                if done or (stop_event and stop_event.is_set()):
                    break
                time.sleep(0.1)
            self.log("Closing tkinter window, wait…")
            root.quit()

        stop_thread = threading.Thread(target=stop_func)
        stop_thread.start()
        root.mainloop()  # Wait for user input

        value = entry.get()
        done = True
        stop_thread.join()
        root.destroy()
        return value


class AutoReadCaptcha(CaptchaSolver):
    def __init__(self, model_path, model_url, frontend):
        super().__init__(frontend)

        tflite_available = importlib.util.find_spec('tflite_runtime')
        fulltf_available = importlib.util.find_spec('tensorflow')

        from urllib.request import urlretrieve
        import os
        if tflite_available:
            import tflite_runtime.interpreter as tflite
        else:
            import tensorflow.lite as tflite

        def reporthook(blocknum, block_size, total_size):
            """
            Credits to jfs from https://stackoverflow.com/questions/13881092/download-progressbar-for-python-3
            """
            readsofar = blocknum * block_size
            if total_size > 0:
                percent = readsofar * 1e2 / total_size
                self.log("Downloading model from %s: %5.1f%% %*d / %d" % (
                    model_url, percent, len(str(total_size)), readsofar, total_size))
            else:  # total size is unknown
                self.log("Downloading model from %s: read %d" % (model_url, readsofar))

        if not os.path.exists(model_path):
            self.log(f"Downloading model from {model_url}")
            # download into temp model in order to detect incomplete downloads
            model_temp_path = f"{model_path}.tmp"
            urlretrieve(model_url, model_temp_path, reporthook)
            self.log("Downloading of the model finished")

            # rename temp model
            os.rename(model_temp_path, model_path)

        model_content = open(model_path, "rb").read()
        self.interpreter = tflite.Interpreter(model_content=model_content)

    def solve(self, img_url, stop_event=None) -> str:
        # stop_event not used, because tflite interpreter is hard to cancel (but is is quick)
        import numpy as np

        interpreter = self.interpreter

        self.log("Auto solving CAPTCHA")

        u = requests.get(img_url)
        raw_data = u.content

        img = Image.open(BytesIO(raw_data))
        img = np.asarray(img)

        # normalize to [0...1]
        img = (img / 255).astype(np.float32)

        # convert to grayscale
        r, g, b = img[:, :, 0], img[:, :, 1], img[:, :, 2]
        input = 0.299 * r + 0.587 * g + 0.114 * b

        # input has nowof  shape (70, 175)
        # we modify dimensions to match model's input
        input = np.expand_dims(input, 0)
        input = np.expand_dims(input, -1)
        # input is now of shape (batch_size, 70, 175, 1)
        # output will have shape (batch_size, 4, 26)

        interpreter.allocate_tensors()
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        interpreter.set_tensor(input_details[0]['index'], input)
        interpreter.invoke()

        # predict and get the output
        output = interpreter.get_tensor(output_details[0]['index'])
        # now get labels
        labels_indices = np.argmax(output, axis=2)

        available_chars = "abcdefghijklmnopqrstuvwxyz"

        def decode(li):
            result = []
            for char in li:
                result.append(available_chars[char])
            return "".join(result)

        decoded_label = [decode(x) for x in labels_indices][0]
        self.log(f"CAPTCHA auto solved as '{decoded_label}'")
        return decoded_label
