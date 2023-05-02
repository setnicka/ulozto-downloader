import argparse
import importlib.util
import signal
import os
import sys
from os import path
from uldlib import downloader, captcha, __version__, __path__, const
from uldlib.frontend import ConsoleFrontend, JSONFrontend
from uldlib import utils
from uldlib.torrunner import TorRunner
from uldlib.utils import LogLevel

# TODO Automatic find all types implementing Frontend and put into this dict
available_frontends = {"console": ConsoleFrontend, "JSON": JSONFrontend}


def run():
    parser = argparse.ArgumentParser(
        description='Download file from Uloz.to using multiple parallel downloads.',
        usage=sys.argv[0]+" [options] URL...",
        add_help=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        'urls', metavar='URL', nargs="+", type=str,
        help="URL from Uloz.to (tip: enter in 'quotes' because the URL contains ! sign). Multiple URLs could be specified, they will be downloaded sequentially.")

    g_main = parser.add_argument_group("Main options")
    g_main.add_argument(
        '--parts', metavar='N', type=int, default=20,
        help='Number of parts that will be downloaded in parallel')
    g_main.add_argument(
        '--password', metavar='P', type=str, default="",
        help='Optional password if the file is password-protected')

    g_main.add_argument(
        '--output', metavar='DIRECTORY', type=str, default="./",
        help='Directory or full path including file name where output file will be saved')
    g_main.add_argument(
        '--temp', metavar='DIRECTORY', type=str, default="./",
        help='Directory where temporary files (.ucache, .udown, Tor data directory) will be created')
    g_main.add_argument(
        '-y', '--yes', default=False, action="store_true",
        help='Overwrite files without asking')

    g_log = parser.add_argument_group("Display and logging options")
    g_log.add_argument(
        '--parts-progress', default=False, action='store_true',
        help='Show progress of parts while being downloaded')
    g_log.add_argument(
        '--log', metavar='LOGFILE', type=str, default="",
        help="Enable logging to given file")
    g_log.add_argument(
        '--frontend', type=str, default="console", choices=available_frontends.keys(),
        help="Select frontend: 'console' - text user interface for humans, 'JSON' - output for scripts")

    g_captcha = parser.add_argument_group("CAPTCHA solving related options")
    g_captcha.add_argument(
        '--auto-captcha', default=False, action="store_true",
        help='Try to solve CAPTCHAs automatically using TensorFlow')
    g_captcha.add_argument(
        '--manual-captcha', default=False, action="store_true",
        help='Solve CAPTCHAs by manual input')

    g_tor = parser.add_argument_group("TOR related options")
    g_tor.add_argument(
        '-t', '--enforce-tor', default=False, action="store_true",
        help='Perform all the connections via TOR. If not set, the initial connection to Ulozto is performed directly before TOR is launched')
    g_tor.add_argument(
        '--conn-timeout', metavar='SEC', default=const.DEFAULT_CONN_TIMEOUT, type=int,
        help='Set connection timeout for TOR sessions in seconds')

    g_other = parser.add_argument_group("Other options")
    g_other.add_argument('--version', action='version', version=__version__)
    g_other.add_argument('-h', '--help', action='help', help='Show this help message and exit')

    args = parser.parse_args()

    # Use user chosen frontend
    frontend = available_frontends[args.frontend](show_parts=args.parts_progress, logfile=args.log)

    tfull_available = importlib.util.find_spec('tensorflow') and importlib.util.find_spec('tensorflow.lite')
    tflite_available = importlib.util.find_spec('tflite_runtime')
    tkinter_available = importlib.util.find_spec('tkinter')

    # Autodetection
    if not args.auto_captcha and not args.manual_captcha:
        if tfull_available:
            frontend.main_log("[Autodetect] tensorflow.lite available, using --auto-captcha")
            args.auto_captcha = True
        elif tflite_available:
            frontend.main_log("[Autodetect] tflite_runtime available, using --auto-captcha")
            args.auto_captcha = True
        elif tkinter_available:
            frontend.main_log("[Autodetect] tkinter available, using --manual-captcha")
            args.manual_captcha = True
        else:
            frontend.main_log(
                "[Autodetect] WARNING: No tensorflow.lite or tflite_runtime and no tkinter available, cannot solve CAPTCHA (only direct download available)",
                level=LogLevel.WARNING
            )

    if args.auto_captcha:
        if not (tfull_available or tflite_available):
            frontend.main_log('ERROR: --auto-captcha used but neither tensorflow.lite nor tflite_runtime are available', level=LogLevel.ERROR)
            sys.exit(1)

        model_path = path.join(__path__[0], const.MODEL_FILENAME)
        solver = captcha.AutoReadCaptcha(model_path, const.MODEL_DOWNLOAD_URL, frontend)
    elif args.manual_captcha:
        if not tkinter_available:
            frontend.main_log('ERROR: --manual-captcha used but tkinter not available', level=LogLevel.ERROR)
            sys.exit(1)

        solver = captcha.ManualInput(frontend)
    else:
        solver = captcha.Dummy(frontend)

    # enables ansi escape characters in terminal on Windows
    if os.name == 'nt':
        os.system("")

    from colorama import just_fix_windows_console
    just_fix_windows_console()

    tor = TorRunner(args.temp, frontend.tor_log)
    d = downloader.Downloader(tor, frontend, solver)

    # Register sigint handler
    def sigint_handler(sig, frame):
        if d.terminating:
            return  # Already terminating
        d.terminate()
        tor.stop()
        frontend.main_log('Program terminated.')
        sys.exit(1)

    signal.signal(signal.SIGINT, sigint_handler)

    try:
        for url in args.urls:
            d.download(url, args.parts, args.password, args.output, args.temp, args.yes, args.conn_timeout, args.enforce_tor)
            # do clean only on successful download (no exception)
            d.clean()
    except utils.DownloaderStopped:
        pass
    except utils.DownloaderError as e:
        frontend.main_log(str(e), level=LogLevel.ERROR)
    finally:
        d.terminate()
        tor.stop()
