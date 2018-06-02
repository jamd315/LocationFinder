#!/usr/bin/python3
import requests
import pytesseract
import discord
import asyncio
import cv2
import numpy as np
import os
import uuid
import re
import urllib.parse
import cfg

client = discord.Client()
dp = 1.5

def binarize_array(numpy_array, threshold=220):
	"""Binarize a numpy array."""
	for i in range(len(numpy_array)):
		for j in range(len(numpy_array[0])):
			if numpy_array[i][j] > threshold:
				numpy_array[i][j] = 255
			else:
				numpy_array[i][j] = 0
	return numpy_array


@client.event
async def on_ready():
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)
	print('------')

@client.event
async def on_message(message):
	if message.author.name == client.user.name:
		pass # Stop replying to itself
	elif message.attachments:
		tmp = await client.send_message(message.channel, "Image detected, attempting to locate gym...")
		try: # TODO function-ize this and make it async friendly
			id = str(uuid.uuid4())
			url = message.attachments[0]["url"]
			response = requests.get(url)
			arr = np.asarray(bytearray(response.content))
			img = cv2.imdecode(arr, -1)
			img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
			img = img[50:int(img.shape[0]/6), ::]
			c_search = img[::, 0:int(img.shape[1]/3)]
			custom_dp = False
			if "!dp=" in message.content:
				custom_dp = float(re.findall(r"(?<=\!dp\=)[0-9\.]+", message.content)[0])
				await client.send_message(message.channel, "Using custom dp of {} for accumulator array".format(custom_dp))
			circles = cv2.HoughCircles(c_search, cv2.HOUGH_GRADIENT, custom_dp or dp, 10000, minRadius=30, maxRadius=120)  # TODO vary accumulator to try and get better circle loc
			x, y, r = circles[0][0]
			height, width = img.shape
			font_h = 100
			y1 = int(y-font_h/2)
			y2 = int(y+font_h/2)
			x1 = int(x+r+10)
			x2 = int(width)
			text_img = img.copy()
			text_img = text_img[y1:y2, x1:x2]
			text_img = binarize_array(text_img)
			msg = pytesseract.image_to_string(text_img)
			await client.edit_message(tmp, "https://www.google.com/maps/dir/?api=1&destination="+urllib.parse.quote(msg))
			if "!debug" in message.content:
				circle_disp = img.copy()
				for (x, y, r) in np.round(circles[0, :]).astype("int"):
					cv2.circle(circle_disp, (x, y), r, (255, 255, 255), 4)
				cv2.imwrite("circle_"+id+".jpg", circle_disp)
				await client.send_file(message.channel, "circle_"+id+".jpg")
				cv2.imwrite("text_"+id+".jpg", text_img)
				await client.send_file(message.channel, "text_"+id+".jpg")
		except cv2.error:
			await client.edit_message(tmp, "Error when detecting circles")
		except Exception as e:
			raise e
		finally:
			if "!debug" not in message.content:
				await asyncio.sleep(5)
				#await client.delete_message(tmp)

client.run(cfg.botkey)
