import argparse
import sys
import signal
from os import path
from uldlib import downloader, captcha, __version__, __path__
from uldlib.const import DEFAULT_CONN_TIMEOUT


def run():
    parser = argparse.ArgumentParser(
        description='Download file from Uloz.to using multiple parallel downloads.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('url', metavar='URL', type=str,
                        help="URL from Uloz.to (tip: enter in 'quotes' because the URL contains ! sign)")
    parser.add_argument('--parts', metavar='N', type=int, default=10,
                        help='Number of parts that will be downloaded in parallel')
    parser.add_argument('--output', metavar='DIRECTORY',
                        type=str, default="./", help='Target directory')
    parser.add_argument('--auto-captcha', default=False, action="store_true",
                        help='Try to solve captchas automatically using TensorFlow')
    parser.add_argument('--conn-timeout', metavar='SEC', default=DEFAULT_CONN_TIMEOUT, type=int,
                        help='Set connection timeout for TOR sessions in seconds')
    parser.add_argument('--version', action='version', version=__version__)

    args = parser.parse_args()

    if args.auto_captcha:
        model_path = path.join(__path__[0], "model.tflite")
        model_download_url = "https://github.com/JanPalasek/ulozto-captcha-breaker/releases/download/v2.2/model.tflite"
        captcha_solve_fnc = captcha.AutoReadCaptcha(
            model_path, model_download_url)
    else:
        captcha_solve_fnc = captcha.tkinter_user_prompt

    d = downloader.Downloader(captcha_solve_fnc)

    # Register sigint handler
    def sigint_handler(sig, frame):
        d.terminate()
        print('Program terminated.')
        sys.exit(1)

    signal.signal(signal.SIGINT, sigint_handler)

    d.download(args.url, args.parts, args.output, args.conn_timeout)
    d.terminate()
