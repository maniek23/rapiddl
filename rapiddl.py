#!/usr/bin/env python
# -*- coding: utf-8 -*-
build = 200903011956

import urllib2
import httplib
import socket
import optparse
import sys
import os.path
from re import findall
from time import time, sleep, gmtime
from random import randint
from locale import getdefaultlocale

# Wersja
version = '1.0.0b'

# Kilka wyjątków używanych do obsługi pobierania
class IncorrectUrlError:
	pass
	
class DownloadError:
	pass

class SlotInUseException:
	pass
	
class LimitReachedException:
	def __init__(self, time_to_wait):
		self.time_to_wait = time_to_wait
		
class ForceWaitException:
	def __init__(self, time_to_wait):
		self.time_to_wait = time_to_wait
		
class BindableHTTPConnection(httplib.HTTPConnection):
	def __init__(self, host, port=None, strict=None, bind_to=None):
		httplib.HTTPConnection.__init__(self, host, port, strict)
		self.bind_to = bind_to
		
	def connect(self):
		"""Connect to the host and port specified in __init__."""
		msg = "getaddrinfo returns an empty list"
		for res in socket.getaddrinfo(self.host, self.port, 0,
									  socket.SOCK_STREAM):
			af, socktype, proto, canonname, sa = res
			try:
				self.sock = socket.socket(af, socktype, proto)
				if self.bind_to != None and len(self.bind_to) == 2:
					self.sock.bind(self.bind_to)
				if self.debuglevel > 0:
					print "connect: (%s, %s)" % (self.host, self.port)
				self.sock.connect(sa)
			except socket.error, msg:
				if self.debuglevel > 0:
					print 'connect fail:', (self.host, self.port)
				if self.sock:
					self.sock.close()
				self.sock = None
				continue
			break
		if not self.sock:
			raise socket.error, msg
			
class BindableHTTPHandler(urllib2.HTTPHandler):
	static = {}
	def __init__(self, debuglevel=0):
		urllib2.AbstractHTTPHandler.__init__(self, debuglevel)
		self.static['bind_to'] = None
		
	def http_open(self, req):
		return self.do_open(BindableHTTPConnection, req)
		
	def do_open(self, http_class, req):
		host = req.get_host()
		if not host:
			raise URLError('no host given')

		h = http_class(host, bind_to=self.static['bind_to']) # will parse host:port
		h.set_debuglevel(self._debuglevel)

		headers = dict(req.headers)
		headers.update(req.unredirected_hdrs)
		
		headers["Connection"] = "close"
		headers = dict(
			(name.title(), val) for name, val in headers.items())
		try:
			h.request(req.get_method(), req.get_selector(), req.data, headers)
			r = h.getresponse()
		except socket.error, err: # XXX what error?
			raise URLError(err)
		
		r.recv = r.read
		fp = socket._fileobject(r, close=True)

		resp = urllib2.addinfourl(fp, r.msg, req.get_full_url())
		resp.code = r.status
		resp.msg = r.reason
		return resp
		
	@staticmethod
	def BindTo(ip='0.0.0.0', port=0):
		BindableHTTPHandler.static['bind_to'] = (ip, int(port))

	http_request = urllib2.AbstractHTTPHandler.do_request_
		
class OutputManager:
	color = {'normal': 'm',
			'lnormal': '1m',
			'black': '30m',
			'lblack': '1;30m',
			'red': '31m',
			'lred': '1;31m',
			'green': '32m',
			'lgreen': '1;32m',
			'yellow': '33m',
			'lyellow': '1;33m',
			'blue': '34m',
			'lblue': '1;34m',
			'purple': '35m',
			'lpurple': '1;35m',
			'cyan': '36m',
			'lcyan': '1;36m',
			'grey': '37m',
			'lgrey': '1;37m' }
			
	bgcolor = { 'normal': '50m',
			'black': '40m',
			'red': '41m',
			'green': '42m',
			'yellow': '43m',
			'blue': '44m',
			'purple': '45m',
			'cyan': '46m',
			'grey': '47m' }
			
	def __init__(self):
		self.quiet = False
		self.nocolor = False
		self.indent_str = "   "
		self.buf = ""
		self.last_type = 0
		
	def QuickMsg(self, msg, important=False, indent_level=0, color='normal', bgcolor='normal'):
		if self.quiet and not important:
			return
			
		sys.stdout.write((self.indent_str * indent_level) + self.Colorize(msg, color, bgcolor))
		sys.stdout.flush()
		
	def QuickMsgLine(self, msg, important=False, indent_level=0, color='normal', bgcolor='normal'):
		if self.quiet and not important:
			return
			
		self.QuickMsg(msg, important, indent_level, color, bgcolor)
		self.NewLine()
		
	def WriteCountdown(self, time, important=False, indent_level=0):
		if self.quiet and not important:
			sleep(time)
			return
		
		seconds = range(1, int(time) + 1)
		seconds.reverse()
		for second in seconds:
			self.WriteNoRepeat(1, indent_level=indent_level, clear_buf=False)
			self.QuickMsg(str(second) + '      ', color='lgreen')
			sleep(1)
		self.WriteNoRepeat(1, indent_level=indent_level, clear_buf=True)
		self.QuickMsg(str(0), color='lgreen')
		
	def BuildMsg(self, msg, important=False, space=" ", color='normal', bgcolor='normal'):
		if self.quiet and not important:
			return
			
		self.buf += self.Colorize(msg, color, bgcolor) + space
		
	def WriteMsg(self, indent_level=0, clear_buf=True):
		if self.buf == "":
			return
			
		sys.stdout.write((self.indent_str * indent_level) + self.buf)
		sys.stdout.flush()
		if clear_buf:
			self.buf = ""
			
	def WriteMsgLine(self, indent_level=0, clear_buf=True):
		if self.buf == "":
			return
			
		self.WriteMsg(indent_level, clear_buf)
		self.NewLine()
			
	def WriteNoRepeat(self, type, indent_level=0, clear_buf=True):
		if self.buf == "":
			return
			
		if type is self.last_type:
			self.Return()
		else:
			self.NewLine()
		
		self.last_type = type
		self.WriteMsg(indent_level, clear_buf)
		
	def ClearBuf(self):
		self.buf = ""
		
	def Return(self):
		sys.stdout.write('\r')
		
	def NewLine(self):
		sys.stdout.write('\n')
		
	def Colorize(self, text, color='normal', bgcolor='normal'):
		if self.nocolor:
			return text
		
		if color in self.color.keys():
			color = self.color[color]
		elif color in self.color.values():
			pass
		else:
			color = self.color['normal']
			
		if bgcolor in self.bgcolor.keys():
			bgcolor = self.bgcolor[bgcolor]
		elif bgcolor in self.bgcolor.values():
			pass
		else:
			bgcolor = self.bgcolor['normal']
			
		new_text = "\033[%s" % color
		if bgcolor is not self.bgcolor['normal']:
			new_text += "\033[%s" % bgcolor
		new_text += "%s\033[0m" % text
			
		return new_text
			
output = OutputManager()
		
class DownloadTask:
	"""
	Klasa odpowiedzialna za przechowywanie informacji o pobieranym pliku
	"""
	
	def __init__(self, url):
		self.main_url = url
		self.server_url = ""
		self.direct_url = ""
		self.size = 0
		self.name = url[url.rindex('/') + 1:]
		
	def new_block_size(self, before, after, bytes):
		new_min = max(bytes / 2.0, 1.0)
		new_max = max(bytes * 2.0, 1.0)
		dif = after - before
		if dif < 0.0001:
			return int(new_max)
		rate = bytes / dif
		if rate > new_max:
			return int(new_max)
		if rate < new_min:
			return int(new_min)
		return int(rate)
		
	def GetServerUrl(self):
		"""
		Pobiera dokładny link do pliku, lub informuje się o błednym linku
		"""
		
		handler = urlopen(self.main_url)
		data = handler.read()
		
		if data.find('The file could not be found.  Please check the download link.') > -1:
			raise IncorrectUrlError
			return

		res = findall('<form id="ff" action="(.+)" method="post">', data)
		
		if len(res) == 0:
			raise SlotInUseException
		else:
			self.server_url = res[0]

	def GetDirectUrl(self):
		"""
		Pobiera link do pobierania, ewentualnie zwraca czas jaki należy w przyblizeniu odczekać
		"""
		
		handler = urlopen(self.server_url, "dl.start=Free")
		data = handler.read()
		if data.find('is already downloading a file') > -1:
			raise SlotInUseException
			return None
		elif data.find('Currently a lot of users are downloading files.') > -1:
			time_to_wait = int(findall('check again within the next (\d+?) minutes if downloading', data)[0])
			raise ForceWaitException, time_to_wait
			return None
		elif data.find('You have reached the download limit for free-users. Would you like more?') > -1:
			time_to_wait = int(findall('Or try again in about (\d+?) minutes', data)[0])
			raise LimitReachedException, time_to_wait
			return None
			
		self.direct_url = findall('<form name="dlf" action="(.+)" method="post">', data)[0]
		return (findall("var c=(\d+)", data)[0])
		
	def Download(self, out):
		"""
		Pobiera plik, zapisując go do pliku w zmiennej <out>
		"""
		
		block_size = options['start_block_size']
		handler = urlopen(self.direct_url)
		count = 0.0
		size = float(handler.info()['content-length'])
		self.size = size
		time_start = time()
		time_after = time()
		speed_list = [1] * options['speed_list_len']
		times_empty = 0

		while True:
			time_before = time()
			data = handler.read(block_size)
			time_after = time()
			
			block_size = self.new_block_size(time_before, time_after, block_size)
			
			if data == "":
				times_empty += 1
			else:
				times_empty = 0
				
			if times_empty > 3:
				break
				
			# Może się zdarzyć się ktoś wejdzie nam w kolejke
			if count == 0.0 and data.find('is already downloading a file') > -1:
				raise SlotInUseException
				return
			
			count += len(data)
			
			if (time_after - time_start) != 0:
				speed_current = count / (time_after - time_start)
			else:
				speed_current = block_size
			
			speed_avg = 0
			
			for x in range(len(speed_list) - 1):
				speed_list[x] = speed_list[x + 1]
				
			speed_list[len(speed_list) - 1] = speed_current
			
			for x in speed_list:
				speed_avg += x
			
			speed_avg /= len(speed_list)
			
			output.BuildMsg("%d%%   %.1f/%.1f MB   %d KB/s   ETA: %s      " % (round((count/size)*100), (count/(1024**2)), (size/(1024**2)), round(speed_avg/1024), TimeString(((time_after - time_start) / count) * (size - count))), color='lnormal')
			output.WriteNoRepeat(5, indent_level=1)
			out.write(data)
		out.close()
		output.BuildMsg("%d%%   %.1f MB   %d KB/s   %s      " % (round((count/size)*100), (size/(1024**2)), round((count / (time_after - time_start))/1024), TimeString(time_after - time_start)), color='lnormal', bgcolor='green')
		output.WriteNoRepeat(5, indent_level=1)
		if int(count) != size:
			raise DownloadError
			
def TimeString(time):
	tt = gmtime(time)
	
	time_string = ""
	if tt[5] != 0:
		time_string = "%ss%s" % (tt[5], time_string)
	if tt[4] != 0:
		time_string = "%sm%s" % (tt[4], time_string)
	if tt[3] != 0:
		time_string = "%sh%s" % (tt[3], time_string)
		
	return time_string

def LoadConfig(path):
	path = os.path.expanduser(path)
	if not os.path.exists(path):
		WriteDefaultConfig(path)
		return
	try:
		# Wczytujemy config,i zmieniamy typy danych na takie jakie wymagane są dla poszcególnych ustawień
		f = open(path)
		data = f.read()
		config_options = findall('(.+?)\=(.*?)', data)
		for name, value in config_options:
			if options.has_key(name):
				if type(options[name]) is type(bool()):
					options[name] = bool(value)
				elif type(options[name]) is type(int()):
					options[name] = int(value)
				elif type(options[name]) is type(float()):
					options[name] = float(value)
				else:
					options[name] = str(value)
		f.close()
		
	# Gdy coś pójdzie nie tak, uciekamy ;)
	except:
		return
		
def WriteDefaultConfig(path):
	if not os.path.isdir(os.path.expanduser(options['rapiddl_dir'])):
		os.mkdir(os.path.expanduser(options['rapiddl_dir']))
	path = os.path.expanduser(path)
	try:
		f = open(path, 'w')
		for key, value in options.items():
			# Jezeli typ danych to BOOL zmieniamy go na INT
			if type(value) is type(bool()):
				print >> f, "%s=%s" % (key, int(value))
			else:
				print >> f, "%s=%s" % (key, value)
		
		f.close()
	except:
		return
		
def LoadFinishedDownloads(path):
	path = os.path.expanduser(path)
	if not os.path.exists(path):
		return
	
	f = open(path)
	ml = findall('(.+?) (\d+?)', f.read())
	f.close()
	
	for key, value in ml:
		finished_downloads[key] = value
		
def AddFinishedDownload(path, url, size):
	if not os.path.isdir(os.path.expanduser(options['rapiddl_dir'])):
		os.mkdir(os.path.expanduser(options['rapiddl_dir']))
	path = os.path.expanduser(path)
		
	if url in finished_downloads:
		return
		
	f = open(path, 'a')
	print >> f, "%s %d" % (url, size)
	f.close()
	
def LoadUrlsList(path):
	path = os.path.expanduser(path)
	if not os.path.exists(path):
		return []
		
	f = open(path)
	continue_list = f.read().split()
	f.close()
	
	while '' in continue_list:
		continue_list.remove('')
		
	continue_list = filter(lambda x: x.startswith('http'), continue_list)
		
	return continue_list
	
def SaveUrlsList(path, list):
	if not os.path.isdir(os.path.expanduser(options['rapiddl_dir'])):
		os.mkdir(os.path.expanduser(options['rapiddl_dir']))
	path = os.path.expanduser(path)
		
	f = open(path, 'w')
	for line in list:
		print >> f, line
	f.close()
		
def Update():
	h = urlopen(update_url)
	data = h.read(66)
	new_build = int(data[(data.index('build =') + len('build =')):])
	if new_build > build:
		output.QuickMsgLine(lang['m_new_version'], color='lnormal')
		try:
			f = open(sys.argv[0], 'w')
			output.QuickMsgLine(lang['m_updating'])
			data += h.read()
			f.write(data)
			f.close()
			output.QuickMsgLine(lang['m_updated'])
			sys.exit()
		except IOError:
			output.QuickMsgLine(lang['m_cannot_update'], color='red')
			return
	else:
		output.QuickMsgLine(lang['m_up_to_date'])
		
def SwitchAddress():
	wait = False
	if address_list:
		address_list.append(address_list[0])
		next_address = address_list.pop(0)
		if next_address == None:
			wait = True
			address_list.append(address_list[0])
			next_address = address_list.pop(0)
		BindableHTTPHandler.BindTo(*next_address)
	else:
		wait = True
	
	return wait

def main():
	parser = optparse.OptionParser(usage="%prog <rapidshare urls> [options]", version="%%prog %s" % version)
	parser.add_option("-d", "--dir", dest="download_dir", metavar=lang['hm_download_dir'], help=lang['h_download_dir'], default=options["download_dir"])
	parser.add_option("-i", "--input", dest="input", metavar=lang['hm_input'], help=lang['h_input'], default=options["input"])
	parser.add_option("-o", "--output", dest="output_format", metavar=lang['hm_output_format'], help=lang['h_output_format'], default=options["output_format"])
	parser.add_option("-C", "--continue", dest="continue", action="store_true", help=lang['h_continue'], default=options["continue"])
	parser.add_option("-1", "--oneshot", dest="loop", action="store_false", help=lang['h_loop'], default=options["loop"])
	parser.add_option("-t", "--tries", dest="tries_limit", metavar=lang['hm_tries_limit'], help=lang['h_tries_limit'], default=options["tries_limit"], type="int")
	parser.add_option("-T", "--timelimit", dest="time_limit", metavar=lang['hm_time_limit'], help=lang['h_time_limit'], default=options["time_limit"], type="int")
	parser.add_option("-b", "--bind-to", dest="bind_to", metavar=lang['hm_bind_to'], help=lang['h_bind_to'], default=options["bind_to"])
	parser.add_option("-w", "--interval", dest="loop_interval", metavar=lang['hm_loop_interval'], help=lang['h_loop_interval'], default=options["loop_interval"], type="int")
	parser.add_option("-W", "--prepare-interval", dest="prepare_interval", metavar=lang['hm_prepare_interval'], help=lang['h_prepare_interval'], default=options["prepare_interval"], type="int")
	parser.add_option("-l", "--list", dest="list", action="store_true", help=lang['h_list'], default=options["list"])
	parser.add_option("-L", "--list-only", dest="list_only", action="store_true", help=lang['h_list_only'], default=options["list_only"])
	parser.add_option("-v", "--check", dest="check_url_only", action="store_true", help=lang['h_check_url_only'], default=options["check_url_only"])
	parser.add_option("-p", "--pretend", dest="get_url_only", action="store_true", help=lang['h_get_url_only'], default=options["get_url_only"])
	parser.add_option("-a", "--test", dest="check_availability_only", action="store_true", help=lang['h_check_availability_only'], default=options["check_availability_only"])
	parser.add_option("-O", "--overwrite", dest="overwrite", action="store_true", help=lang['h_overwrite'], default=options["overwrite"])
	parser.add_option("-f", "--force", dest="force_downloaded", action="store_true", help=lang['h_force_downloaded'], default=options["force_downloaded"])
	parser.add_option("-F", "--force-force", dest="force_existing", action="store_true", help=lang['h_force_existing'], default=options["force_existing"])
	parser.add_option("-q", "--quiet", dest="quiet_mode", action="store_true", help=lang['h_quiet_mode'], default=options["quiet_mode"])
	parser.add_option("-s", "--start-from", dest="start_from_url", metavar=lang['hm_start_from_url'], help=lang['h_start_from_url'], default=options["start_from_url"], type="int")
	parser.add_option("-I", "--ignore", dest="ignore_invalid_url_error", action="store_true", help=lang['h_ignore_invalid_url_error'], default=options["ignore_invalid_url_error"])
	parser.add_option("-c", "--config", dest="config_path", metavar=lang['hm_config_path'], help=lang['h_config_path'], default=options["config_path"])
	parser.add_option("-u", "--update", dest="update", action="store_true", help=lang['h_update'], default=options["update"])
	parser.add_option("-S", "--support-author", dest="support_author_mode", action="store_true", help=lang['h_support_author_mode'], default=options["support_author_mode"])
	(parser_options, args) = parser.parse_args()
	
	LoadConfig(getattr(parser_options, 'config_path'))
	
	for k in options:
		if hasattr(parser_options, k):
			options[k] = getattr(parser_options, k)
		
	urls = []
	download_list = []
	
	if options['continue']:
		urls.extend(LoadUrlsList(options['continue_path']))
	if options['input'] == '-':
		for line in sys.stdin:
			urls.append(line.strip())
	elif len(options['input']) > 0:
		urls.extend(LoadUrlsList(options['input']))
	urls.extend(args)
	
	if options['update']:
		Update()
		
	if options['quiet_mode']:
		output.quiet = True
	if options['nocolor']:
		output.nocolor = True
	
	for arg in urls:
		if len(arg.strip().split()) > 1:
			for sub_arg in arg.strip().split():
				download_list.append(sub_arg)
		else:
			download_list.append(arg)
	
	if options['check_availability_only'] or options['support_author_mode']:
		download_list += [support_author_url]
		
	if options['start_from_url'] > 1 and len(download_list) >= options['start_from_url']:
		download_list = download_list[options['start_from_url']-1:]
	elif options['start_from_url'] > 1:
		download_list = []
	
	if len(download_list) == 0:
		sys.exit('\n' + lang['m_no_urls'])
		
	# Parsujemy Liste IP
	address_list.extend(map(lambda x: x.split(':'), options['bind_to'].split(',')))
	if address_list:
		address_list.append(None)
		SwitchAddress()
		
	# Spradzamy czy katalog docelowy istnieje,
	# jeśli nie ustalamy katalog docelowy na aktualny folder
	if options['download_dir'] is not "" and not os.path.isdir(options['download_dir']):
		options['download_dir'] = ""
	elif options['download_dir'] is not "" and not options['download_dir'].endswith('/'):
		options['download_dir'] += '/'
		
	# Jeżeli została użyta opcja formatowania nazwy plików
	# sprawdzamy czy "%d" jest w nazwie, inaczej go dodajemy
	if options['output_format'] is not "" and "%d" not in options['output_format'] and len(download_list) > 1:
		options['output_format'] += "-%d"
		
	for x in download_list:
		if x in download_list:
			while download_list.count(x) > 1:
				download_list.remove(x)
				
	if not options['check_url_only'] and not options['get_url_only'] and not options['check_availability_only']:
		LoadFinishedDownloads(options['finished_path'])
		SaveUrlsList(options['continue_path'], download_list)
		
	urls_count = len(download_list)
	
	if options['list'] or options['list_only']:
		for index, url in enumerate(download_list):
			output.QuickMsgLine('%d. %s' % (index + 1, url))
		if options['list_only']:
			sys.exit()
		
	for index, url in enumerate(download_list[:]):
		start_download = True
		dt = DownloadTask(url)
		
		if not options['check_url_only'] and not options['get_url_only'] and not options['check_availability_only']:
			# Formatowanie nazwy pliku
			if options['output_format'] is "":
				name = dt.name
			elif "%d" in options['output_format']:
				name = options['output_format'] % index
			else:
				name = options['output_format']
				
			name = options['download_dir'] + name
			
		output.QuickMsgLine("(%d/%d) %s:" % (index + 1, urls_count, url), color='lnormal')
		if not options['check_url_only'] and not options['get_url_only'] and not options['check_availability_only']:
			output.QuickMsgLine('==> %s' % name, color='lnormal')
			
			# W celu uniknięcia niepotrzebnych pobierań sprawdzamy, czy plik nie został już wcześniej pobrany
			if url in finished_downloads and not (options['force_downloaded'] or options['force_existing']):
				output.QuickMsgLine(lang['m_file_downloaded_before'] % options['finished_path'], indent_level=1, color='yellow')
				del download_list[0]
				SaveUrlsList(options['continue_path'], download_list)
				continue
			elif url in finished_downloads and not options['force_existing'] and os.path.isfile(name) and os.path.getsize(name) == finished_downloads[url]:
				output.QuickMsgLine(lang['m_file_exists'] % options['finished_path'], indent_level=1, color='yellow')
				del download_list[0]
				SaveUrlsList(options['continue_path'], download_list)
				continue
			
			# Jeżeli nie ma opcji nadpisania pliku, zmieniamy nazwe pobieranego pliku, dodając na końcu kolejne cyfry (a'la wget)
			if not options['overwrite']:
				num = 1
				new_name = name
				while os.path.isfile(new_name) and os.path.getsize(name) > 0:
					new_name = "%s.%d" % (name, num)
					num += 1
				name = new_name
				
			# Zamiast pobierać plik bezspośrednio do wskazanego pliku, posłużymy się buforem, dodając '.part' do nazwy pliku
			temp_name = name + '.part'
		
		# Ustalamy limity czasu i ilości prób pobierań
		if options['tries_limit'] > 0:
			tries_limit = options['tries_limit']
		else:
			tries_limit = 0
		if options['time_limit'] > 0:
			time_limit = time() + options['time_limit'] * 60
		else:
			time_limit = 0
		
		current_try = 0
		if not options['check_url_only'] and not options['get_url_only'] and not options['check_availability_only']:
			out_file = open(temp_name, 'w')
		while options['loop'] or start_download:
			start_download = False
			
			# Sprawdzamy limity czasu i ilości prób pobierań
			if tries_limit is not 0 and current_try > tries_limit:
				output.NewLine()
				output.QuickMsgLine(lang['m_tries_limit_exceeded'], important=True, color='lred')
				sys.exit(1)
			elif time_limit is not 0 and time() > time_limit:
				output.NewLine()
				output.QuickMsgLine(lang['m_time_limit_exceeded'], important=True, color='lred')
				sys.exit(1)
			
			current_try += 1
			try:
				if not options['check_url_only'] and options['loop']:
					output.BuildMsg(lang['m_try'] % current_try)
				dt.GetServerUrl()
				if options['check_url_only']:
					output.QuickMsgLine(lang['m_correct_url'], indent_level=1, color='lgreen')
					break
				wait = dt.GetDirectUrl()
				if options['get_url_only']:
					output.QuickMsgLine('%s' % dt.direct_url, important=True, color='lnormal', bgcolor='green')
					break
				if options['check_availability_only']:
					output.BuildMsg(lang['m_download_possible'], important=True, color='lgreen')
					output.WriteNoRepeat(6, indent_level=1)
					break
				output.BuildMsg(lang['m_waiting_for_download'], color='green')
				output.WriteCountdown(wait, indent_level=1)
				dt.Download(out_file)
				output.NewLine()
				output.QuickMsgLine(lang['m_download_finished'], indent_level=1, color='lgreen')
				os.rename(temp_name, name)
				output.NewLine()
				
				AddFinishedDownload(options['finished_path'], url, dt.size)
				del download_list[0]
				SaveUrlsList(options['continue_path'], download_list)
				break
				
			except IncorrectUrlError:
				output.BuildMsg(lang['m_incorrect_url'], color='lred')
				output.WriteNoRepeat(2, indent_level=1)
				if options['ingore_invalid_url_error']:
					break
				else:
					sys.exit('\n')
			
			except SlotInUseException:
				output.BuildMsg(lang['m_slot_in_use'], color='red')
				output.WriteNoRepeat(3, indent_level=1)
				if not SwitchAddress():
					sleep(1)
				else:
					sleep(options['loop_interval'])
				
			except LimitReachedException, e:
				output.BuildMsg(lang['m_limit_reached'] % e.time_to_wait, color='yellow')
				output.WriteNoRepeat(4, indent_level=1)
				if not SwitchAddress():
					sleep(1)
				elif e.time_to_wait <= options['preparation_time']:
					sleep(options['prepare_interval'])
				else:
					sleep(options['loop_interval'])
				
			except ForceWaitException, e:
				output.BuildMsg(lang['m_forced_wait'] % e.time_to_wait, color='cyan')
				output.WriteCountdown(e.time_to_wait * 60, indent_level=1)
				
# Inicjacja urllib
urllib2.install_opener(urllib2.build_opener(urllib2.HTTPCookieProcessor()))
urllib2.install_opener(urllib2.build_opener(BindableHTTPHandler()))
urlopen = urllib2.urlopen

support_author_url = "http://rapidshare.com/files/127043295/thanks.zip"
update_url = "http://maniek23.comyr.com/rapiddl/rapiddl.py"

# Domyślne ustawienia

options = {'start_block_size': 1024*10,
		'output_format': "",
		'input': "",
		'download_dir': "",
		'quiet_mode': False,
		'nocolor': False,
		'loop': True,
		'loop_interval': 60,
		'prepare_interval': 5,
		'preparation_time': 2,
		'start_from_url': 1,
		'continue': False,
		'tries_limit': 0,
		'time_limit': 0,
		'bind_to': "",
		'list': False,
		'list_only': False,
		'get_url_only': False,
		'check_url_only': False,
		'check_availability_only': False,
		'support_author_mode': False,
		'speed_list_len': 25,
		'force_downloaded': False,
		'force_existing': False,
		'overwrite': False,
		'ignore_invalid_url_error': False,
		'update': False,
		'rapiddl_dir': '~/.rapiddl/',
		'config_path': '~/.rapiddl/config',
		'finished_path': '~/.rapiddl/finished',
		'continue_path': '~/.rapiddl/continue'}

# Słownik pobranych plików
# { link: rozmiar }
finished_downloads = {}
address_list = []

# Języki

lang = {}

# Angielski

lang['en_EN'] = {}

lang['en_EN']['h_output_format'] = "Saves file at pointed path, if downloading more than one file '%d' is replaced by current file number,'-' means standard output".decode('UTF-8')
lang['en_EN']['hm_output_format'] = "FILE".decode('UTF-8')
lang['en_EN']['h_input'] = "Get urls from pointed file,'-' means standard input".decode('UTF-8')
lang['en_EN']['hm_input'] = "FILE".decode('UTF-8')
lang['en_EN']['h_download_dir'] = "Directory where files will be saved".decode('UTF-8')
lang['en_EN']['hm_download_dir'] = "DIR".decode('UTF-8')
lang['en_EN']['h_loop'] = "Turns off loop mode, tries to download only once".decode('UTF-8')
lang['en_EN']['h_tries_limit'] = "Download tries limit, after exceed download is turned off".decode('UTF-8')
lang['en_EN']['hm_tries_limit'] = "COUNT".decode('UTF-8')
lang['en_EN']['h_time_limit'] = "Download time limit, after exceed download is turned off".decode('UTF-8')
lang['en_EN']['hm_time_limit'] = "MINUTES".decode('UTF-8')
lang['en_EN']['h_bind_to'] = "Bind to specified IP (and port), split more IPs with commas, IPs will be switched every time download fails".decode('UTF-8')
lang['en_EN']['hm_bind_to'] = "IP[:PORT],IP[:PORT]...".decode('UTF-8')
lang['en_EN']['h_loop_interval'] = "Interval beetween download tries".decode('UTF-8')
lang['en_EN']['hm_loop_interval'] = "SECONDS".decode('UTF-8')
lang['en_EN']['h_prepare_interval'] = "Interval betwwen download tries, when download time is close".decode('UTF-8')
lang['en_EN']['hm_prepare_interval'] = "SECONDS".decode('UTF-8')
lang['en_EN']['h_list'] = "Print urls list, and download".decode('UTF-8')
lang['en_EN']['h_list_only'] = "Print urls list and do NOT download".decode('UTF-8')
lang['en_EN']['h_check_url_only'] = "Check urls correctness only".decode('UTF-8')
lang['en_EN']['h_continue'] = "Continue download form last session".decode('UTF-8')
lang['en_EN']['h_start_from_url'] = "Start download from specified link number".decode('UTF-8')
lang['en_EN']['hm_start_from_url'] = "NUMBER".decode('UTF-8')
lang['en_EN']['h_get_url_only'] = "Print direct download url, do not download".decode('UTF-8')
lang['en_EN']['h_force_downloaded'] = "Force download of files which were downloaded before".decode('UTF-8')
lang['en_EN']['h_force_existing'] = "Force download of files which were downloaded before and still exists".decode('UTF-8')
lang['en_EN']['h_overwrite'] = "Force overwrite of existing files".decode('UTF-8')
lang['en_EN']['h_check_availability_only'] = "Check download availability only, do not download".decode('UTF-8')
lang['en_EN']['h_quiet_mode'] = "Quiet mode".decode('UTF-8')
lang['en_EN']['h_ignore_invalid_url_error'] = "Ignore invalid urls, and continue download of next files".decode('UTF-8')
lang['en_EN']['h_config_path'] = "Load config from specified file".decode('UTF-8')
lang['en_EN']['h_nocolor'] = "Turn off color using".decode('UTF-8')
lang['en_EN']['hm_config_path'] = "FILE".decode('UTF-8')
lang['en_EN']['h_update'] = "Update script to newest version".decode('UTF-8')
lang['en_EN']['h_support_author_mode'] = "Support author by downloading his rapidshare-url".decode('UTF-8')
lang['en_EN']['m_no_urls'] = "No url to download"
lang['en_EN']['m_file_downloaded_before'] = "This file was downloaded before, so download is skipped, if you want to force download use -f / --force option or remove url from file %s"
lang['en_EN']['m_file_exists'] = "This file was downloaded before, so download is skipped, if you want to force download use -F / --force-force option or remove url from file %s"
lang['en_EN']['m_tries_limit_exceeded'] = "Tries limit exceeded"
lang['en_EN']['m_time_limit_exceeded'] = "Time limit exceeded"
lang['en_EN']['m_try'] = "Try %d:"
lang['en_EN']['m_correct_url'] = "Url is correct"
lang['en_EN']['m_download_possible'] = "Download is possible"
lang['en_EN']['m_waiting_for_download'] = "Waiting for download:"
lang['en_EN']['m_download_finished'] = "Download finished"
lang['en_EN']['m_incorrect_url'] = "Incorrect url"
lang['en_EN']['m_slot_in_use'] = "Slot for your IP is currently in use"
lang['en_EN']['m_limit_reached'] = "Download exceeded, you need to wait about %d minutes"
lang['en_EN']['m_forced_wait'] = "Forced waiting %d minutes"
lang['en_EN']['m_interrupt'] = "Download interrupted"
lang['en_EN']['m_new_version'] = "New version is available"
lang['en_EN']['m_up_to_date'] = "Your version is up to date"
lang['en_EN']['m_updating'] = "Updating..."
lang['en_EN']['m_updated'] = "Updated succesfully"
lang['en_EN']['m_cannot_update'] = "You haven't permission to perform update, run update as root"

# Polski

lang['pl_PL'] = lang['en_EN']

lang['pl_PL']['h_output_format'] = "Zapisuje plik pod wskazaną nazwa, jeżeli pobierasz wiecej niż jeden plik '%d' oznacza numer aktualnego pliku,'-' oznacza starnadardowe wyjście".decode('UTF-8')
lang['pl_PL']['hm_output_format'] = "PLIK".decode('UTF-8')
lang['pl_PL']['h_input'] = "Pobiera linki z podanego pliku,'-' oznacza starnadardowe wejście".decode('UTF-8')
lang['pl_PL']['hm_input'] = "PLIK".decode('UTF-8')
lang['pl_PL']['h_download_dir'] = "Katalog gdzie zapisane zostaną pobierane pliki".decode('UTF-8')
lang['pl_PL']['hm_download_dir'] = "KATALOG".decode('UTF-8')
lang['pl_PL']['h_loop'] = "Wyłącza tryb pętli, próbuje pobrać plik tylko 1 raz".decode('UTF-8')
lang['pl_PL']['h_tries_limit'] = "Limit ilości prób pobierania, po którym pobieranie zostanie zaniechane".decode('UTF-8')
lang['pl_PL']['hm_tries_limit'] = "ILOŚĆ".decode('UTF-8')
lang['pl_PL']['h_time_limit'] = "Limit czasu w minutach, po którym pobieranie zostanie zaniechane".decode('UTF-8')
lang['pl_PL']['hm_time_limit'] = "MINUTY".decode('UTF-8')
lang['pl_PL']['h_bind_to'] = "Używa podanego IP (i portu), oddzielaj kolejne adresy przecinkiem, adresy beda zmienione po każdej nieudanej próbie pobierania".decode('UTF-8')
lang['pl_PL']['hm_bind_to'] = "IP[:PORT],IP[:PORT]...".decode('UTF-8')
lang['pl_PL']['h_loop_interval'] = "Odstęp czasu między kolejnymi próbami pobierań".decode('UTF-8')
lang['pl_PL']['hm_loop_interval'] = "SEKUNDY".decode('UTF-8')
lang['pl_PL']['h_prepare_interval'] = "Odstęp czasu między kolejnymi próbami pobierań, kiedy kończy się czas oczekiwania".decode('UTF-8')
lang['pl_PL']['hm_prepare_interval'] = "SEKUNDY".decode('UTF-8')
lang['pl_PL']['h_list'] = "Wypisuje listę linków, a następnie rozpocznij pobieranie".decode('UTF-8')
lang['pl_PL']['h_list_only'] = "Wypisuje listę linków, jednak nie rozpoczyna pobierania".decode('UTF-8')
lang['pl_PL']['h_check_url_only'] = "Sprawdź czy linki są poprawne, nie pobieraj".decode('UTF-8')
lang['pl_PL']['h_continue'] = "Kontynuuj pobieranie z poprzedniej sesji programu".decode('UTF-8')
lang['pl_PL']['h_start_from_url'] = "Rozpocznij pobieranie od linka z podanym numerem".decode('UTF-8')
lang['pl_PL']['hm_start_from_url'] = "NUMER".decode('UTF-8')
lang['pl_PL']['h_get_url_only'] = "Wypisz bezpośrednie linki pobierania, nie pobieraj".decode('UTF-8')
lang['pl_PL']['h_force_downloaded'] = "Wymuś pobieranie plików które zostały zapamiętane jako pobrane".decode('UTF-8')
lang['pl_PL']['h_force_existing'] = "Wymuś pobieranie plików które zostały zapamiętane jako pobrane oraz istnieją".decode('UTF-8')
lang['pl_PL']['h_overwrite'] = "Wymuś nadpisywanie istniejących plików".decode('UTF-8')
lang['pl_PL']['h_check_availability_only'] = "Sprawdź dostępność pobierania, nic nie pobieraj".decode('UTF-8')
lang['pl_PL']['h_quiet_mode'] = "Tryb cichy".decode('UTF-8')
lang['pl_PL']['h_ignore_invalid_url_error'] = "Ignoruj błędne linki, przechodź do nastepnych linków w kolejce".decode('UTF-8')
lang['pl_PL']['h_config_path'] = "Wczytaj podany plik konfiguracyjny".decode('UTF-8')
lang['pl_PL']['hm_config_path'] = "PLIK".decode('UTF-8')
lang['pl_PL']['h_nocolor'] = "Wyłącz kolory".decode('UTF-8')
lang['pl_PL']['h_update'] = "Pobierz najnowszą wersje skryptu".decode('UTF-8')
lang['pl_PL']['h_support_author_mode'] = "Wspomóż autora skryptu pobierając jego plik".decode('UTF-8')
lang['pl_PL']['m_no_urls'] = "Brak linków do pobrania"
lang['pl_PL']['m_file_downloaded_before'] = "Ten plik został już pobrany wcześniej, więc pobieranie zostało pominięte, jeśli chcesz wymusić pobieranie użyj opcji -f / --force lub usuń link z pliku %s"
lang['pl_PL']['m_file_exists'] = "Ten plik został już pobrany wcześniej, więc pobieranie zostało pominięte, jeśli chcesz wymusić pobieranie użyj opcji -F / --force-force lub usuń link z pliku %s"
lang['pl_PL']['m_tries_limit_exceeded'] = "Przekroczono limit ilości prób pobierania"
lang['pl_PL']['m_time_limit_exceeded'] = "Przekroczono limit czasu prób pobierania"
lang['pl_PL']['m_try'] = "Próba %d:"
lang['pl_PL']['m_correct_url'] = "Link jest poprawny"
lang['pl_PL']['m_download_possible'] = "Pobieranie jest możliwe"
lang['pl_PL']['m_waiting_for_download'] = "Oczekiwanie na pobieranie:"
lang['pl_PL']['m_download_finished'] = "Zakończono pobieranie pliku"
lang['pl_PL']['m_incorrect_url'] = "Niepoprawny url"
lang['pl_PL']['m_slot_in_use'] = "Slot dla twojego IP jest zajęty"
lang['pl_PL']['m_limit_reached'] = "Osiągnieto limit pobierania, musisz poczekać około %d minut"
lang['pl_PL']['m_forced_wait'] = "Wymuszono czekanie %d minut"
lang['pl_PL']['m_interrupt'] = "Pobieranie przerwane"
lang['pl_PL']['m_new_version'] = "Dostępna jest nowa wersja programu"
lang['pl_PL']['m_up_to_date'] = "Posiadasz najnowszą wersje programu"
lang['pl_PL']['m_updating'] = "Trwa aktualizacja..."
lang['pl_PL']['m_updated'] = "Aktualizacja zakończona sukcesem"
lang['pl_PL']['m_cannot_update'] = "Nie posiadasz uprawnień aby dokonać aktualizacji, uruchom aktualizacje jako administrator"

locale_lang = getdefaultlocale()
if locale_lang in lang.keys():
	lang = lang[locale_lang]
else:
	lang = lang['en_EN']
	
########################################################################
########################################################################
########################################################################
	
if __name__ == "__main__":
	try:
		main()
	except KeyboardInterrupt:
		sys.exit("\r\n" + lang['m_interrupt'])

# EOF
