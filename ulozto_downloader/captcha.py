import requests
from PIL import Image
from io import BytesIO


def tkinter_user_prompt(img_url, print_func):
    """Display captcha from given URL and ask user for input in GUI window.

        Arguments:
            img_url (str): URL of the image with CAPTCHA

        Returns:
            str: User answer to the CAPTCHA
    """
    import tkinter as tk
    from PIL import ImageTk

    root = tk.Tk()
    root.focus_force()
    root.title("Opiš kód z obrázku")
    root.geometry("300x140")  # use width x height + x_offset + y_offset (no spaces!)

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

    root.mainloop()  # Wait for user input
    value = entry.get()
    root.destroy()
    return value


class AutoReadCaptcha:
    def __init__(self, model_path, model_url, print_func=print):
        from urllib.request import urlretrieve
        import os

        def reporthook(blocknum, block_size, total_size):
            """
            Credits to jfs from https://stackoverflow.com/questions/13881092/download-progressbar-for-python-3
            """
            readsofar = blocknum * block_size
            if total_size > 0:
                percent = readsofar * 1e2 / total_size
                s = "\r%5.1f%% %*d / %d" % (
                    percent, len(str(total_size)), readsofar, total_size)
                print_func(s, end="")
                if readsofar >= total_size:  # near the end
                    print_func(flush=True)
            else:  # total size is unknown
                print_func("read %d" % (readsofar,), flush=True)

        if not os.path.exists(model_path):
            print_func(f"Downloading model from {model_url}")
            # download into temp model in order to detect incomplete downloads
            model_temp_path = f"{model_path}.tmp"
            urlretrieve(model_url, model_temp_path, reporthook)
            print_func("Downloading of the model finished")

            # rename temp model
            os.rename(model_temp_path, model_path)

        # due to multiprocessing the model model have to be loaded in each
        # process independently
        self.model_content = open(model_path, "rb").read()
        self.print_func = print_func

    def __call__(self, img_url, print_func):
        import tflite_runtime.interpreter as tflite
        import numpy as np

        print_func("Auto solving CAPTCHA")

        interpreter = tflite.Interpreter(model_content=self.model_content)

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
        print_func(f"CAPTCHA auto solved as '{decoded_label}'")
        return decoded_label
