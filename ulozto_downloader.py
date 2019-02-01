#!/usr/bin/python3
"""Uloz.to quick multiple sessions downloader.

It is neede to install these two packages (names of debian packages, for other systems they may be different):
	python3-tk
	python3-pil.imagetk
"""

import requests
import re
import os
import sys
import tkinter as tk
from PIL import Image, ImageTk
from io import BytesIO
import urllib
import multiprocessing
import time
from datetime import timedelta

# url = "https://ulozto.cz/!8dn7k2NIvIDI/james-bond-007-c-5-zijes-jenom-dvakrat-cz-1920x816-mkv"
url = "https://uloz.to/!D27N8zDWwA94/simpsonovi-s29e14-1080p-cz-sasovy-strachy-mkv"


def load_page(url):
	"""Open the Uloz.to page of the download and return cookies, parsed filename and parsed form data."""
	r = requests.get(url)

	try:
		form_data = {}
		# <input type="hidden" name="sign_a" id="frm-download-freeDownloadTab-freeDownloadForm-sign_a" value="85179a2a2b28fbe512b757cad9b9446a">
		p = re.compile('<input [^>]* name="sign_a" [^>]* value="([^>]*)">', re.IGNORECASE)
		form_data['sign_a'] = p.findall(r.text)[0]

		# <input type="hidden" name="adi" id="frm-download-freeDownloadTab-freeDownloadForm-adi" value="-2">
		p = re.compile('<input [^>]* name="adi" [^>]* value="([^>]*)">', re.IGNORECASE)
		form_data['adi'] = p.findall(r.text)[0]

		p = re.compile('<title>(.*) \| Ulož.to</title>')
		filename = p.findall(r.text)[0]

		return r.cookies, filename, form_data
	except:
		print("Cannot parse Uloz.to page to get download informations")
		sys.exit(1)


def get_new_captcha(url, cookies, form_data):
	"""Get CAPTCHA url and form parameters from page."""
	r = requests.post(url=url, data={
		"_do": "download-freeDownloadTab-freeDownloadForm-submit",
		"sign_a": form_data['sign_a'],
		'adi': form_data['adi'],
	}, headers={
		"X-Requested-With": "XMLHttpRequest"
	}, cookies=cookies)
	return r.json()


def get_captcha_user_input(img_url):
	"""Display captcha from given URL and ask user for input in GUI window."""
	master = tk.Tk()
	master.focus_force()
	master.title("Opiš kód z obrázku")
	master.geometry("300x140")  # use width x height + x_offset + y_offset (no spaces!)

	def disable_event():
		pass

	master.protocol("WM_DELETE_WINDOW", disable_event)

	u = urllib.request.urlopen(img_url)
	raw_data = u.read()
	u.close()

	im = Image.open(BytesIO(raw_data))
	photo = ImageTk.PhotoImage(im)
	label = tk.Label(image=photo)
	label.image = photo
	label.pack()

	entry = tk.Entry(master)
	entry.pack()
	entry.bind('<Return>', lambda event: master.quit())
	entry.focus()

	tk.Button(master, text='Send', command=master.quit).pack()

	master.mainloop()  # Wait for user input
	value = entry.get()
	master.destroy()
	return value


def post_captcha_response(url, cookies, captcha_data, captcha_value):
	"""Do POST request with CAPTCHA solution."""
	nfv = captcha_data['new_form_values']
	data = {
		'_do': 'download-freeDownloadTab-freeDownloadForm-submit',
		'_token_': nfv['_token_'],
		'adi': nfv['adi'],
		'captcha_type': captcha_data['version'],
		'captcha_value': captcha_value,
		'cid': nfv['cid'],
		'hash': nfv['xapca_hash'],
		'salt': nfv['xapca_salt'],
		'sign': nfv['sign'],
		'sign_a': nfv['sign_a'],
		'timestamp': nfv['xapca_timestamp'],
		'ts': nfv['ts']
	}
	r = requests.post(url, data=data, headers={
		"X-Requested-With": "XMLHttpRequest",
	}, cookies=cookies)
	return r.json()


def get_download_link(url):
	"""Get download link from given page URL, it calls CAPTCHA related functions."""
	cookies, filename, form_data = load_page(url)
	captcha_data = get_new_captcha(url, cookies, form_data)
	# print(captcha_data)

	while captcha_data['status'] != 'ok':
		# print("Captcha image challenge...")
		captcha_value = get_captcha_user_input("http:" + captcha_data['new_captcha_data']['image'])
		# print("Captcha input from user: {}".format(captcha_value))
		captcha_data = post_captcha_response(url, cookies, captcha_data, captcha_value)

		# if captcha_data['status'] != 'ok':
		# 	print('Wrong captcha, try again')

	# print('URL obtained: {}'.format(captcha_data['url']))
	return captcha_data['url'], filename


def print_line(line, text):
	"""Print one line at specified y coordinate on the console."""
	sys.stdout.write("\033[{};{}H".format(line, 0))
	sys.stdout.write("\033[K")
	sys.stdout.write(text)
	sys.stdout.flush()


def download_part(part):
	"""Download given part of the download - get link, calculate size and begin download."""
	id = part['id']
	print_line(id + 2, "Part {}\tGetting CAPTCHA...".format(id))
	download_url, filename = get_download_link(part['base_url'])
	print_line(id + 2, "Part {}\tCAPTCHA OK, getting size...".format(id))

	head = requests.head(download_url, allow_redirects=True)
	total_size = int(head.headers['Content-Length'])
	part_size = (total_size + (part['total_parts'] - 1)) // part['total_parts']

	part['url'] = head.url
	part['final_filename'] = filename
	part['filename'] = part['target_dir'] + "{}.part{}".format(filename, id)
	part['from'] = part_size * id
	part['to'] = min(part_size * (id + 1), total_size) - 1
	part['size'] = part['to'] - part['from'] + 1

	print_line(id + 2, "Part {}\tStarting download".format(id))

	part['started'] = time.time()
	part['downloaded'] = 0
	part['now_downloaded'] = 0

	# Test if the file isn't downloaded from previous download. If so, try to continue
	if os.path.isfile(part['filename']):
		part['downloaded'] = os.path.getsize(part['filename'])

	# Note the stream=True parameter
	r = requests.get(part['url'], stream=True, headers={"Range": "bytes={}-{}".format(part['from'] + part['downloaded'], part['to'])})
	with open(part['filename'], 'ab') as f:
		for chunk in r.iter_content(chunk_size=1024):
			if chunk:  # filter out keep-alive new chunks
				f.write(chunk)
				part['downloaded'] += len(chunk)
				part['now_downloaded'] += len(chunk)
				elapsed = time.time() - part['started']

				# Print status line
				speed = part['now_downloaded'] / elapsed if elapsed > 0 else 0  # in bytes per second
				remaining = (part['size'] - part['downloaded']) / speed if speed > 0 else 0  # in seconds

				print_line(id + 2, "Part {}\t{}%\t({}/{}MB)\tspeed: {} KB/s\tremaining: {}".format(
					id,
					round(part['downloaded'] / part['size'] * 100, 1),
					round(part['downloaded'] / 1024**2, 2), round(part['size'] / 1024**2, 2),
					round(speed / 1024, 2),
					str(timedelta(seconds=round(remaining))),
				))


def download(url, parts=10):
	"""Download file from Uloz.to using multiple parallel download."""
	global downloads
	os.system('clear')
	print("Starting downloading from url '{}'".format(url))

	downloads = [
		{'id': x, 'total_parts': parts, 'base_url': url, 'target_dir': ''} for x in range(parts)
	]

	pool = multiprocessing.Pool(processes=parts)
	downloads = pool.map(download_part, downloads)

	os.system('clear')
	print("All downloads finished, merging files")

	final_filename = downloads[0]['final_filename']
	with open(final_filename, "wb") as outfile:
		for part in downloads:
			with open(part['filename'], "rb") as infile:
				outfile.write(infile.read())

	for part in downloads:
		os.remove(part['filename'])

	print("All files merged, output file is '{}'".format(final_filename))

download(url)
