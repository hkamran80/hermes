"""
Project Hermes
Contributors:
  :: H. Kamran [@hkamran80] (author)
Version: 0.0.1
Last Updated: 2019-02-06, @hkamran80
"""

from __future__ import absolute_import
import chromepass
import ffpass
import sys
import os

def scan_browsers():
	if sys.platform == u"darwin":
		installed_browsers = []
		supported_browsers = [u"Google Chrome", u"Firefox"]

		for b in supported_browsers:
			if os.path.isdir(u"/Applications/{}.app".format(b)):
				installed_browsers.append(b)

		return installed_browsers

def googlechrome_export(export_location):
	pwds = chromepass.main()
	export = chromepass.output_csv(pwds, _print=False)

	if export_location:
		for f in os.listdir(os.getcwdu()):
			if u"chrome" in f and u".csv" in f:
				os.rename(f, export_location + u"/" + f)

	return 1

def firefox_export(export_location):
	locdir = ffpass.guessDir()
	export = ffpass.main_export(locdir)

	if export_location:
		for f in os.listdir(os.getcwdu()):
			if u"firefox" in f and u".csv" in f:
				os.rename(f, export_location + u"/" + f)

sb = scan_browsers()

export_location = u"exported"
if os.path.isdir(export_location):
	pass
else:
	os.mkdir(export_location)

print (u"Installed Browsers: \033[95m{}\x1B[0m".format(u", ".join(sb)))
for b in sb:
	print (u"\x1B[96mExtracting passwords from: {}\x1B[0m".format(b))
	if b == u"Google Chrome":
		googlechrome_export(export_location)

		print u"\033[92mGoogle Chrome passwords exported!\x1B[0m"
	elif b == u"Firefox":
		firefox_export(export_location)

		print u"\033[92mFirefox passwords exported!\x1B[0m"