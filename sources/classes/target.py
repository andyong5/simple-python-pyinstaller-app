import os
import requests
from requests import exceptions
from requests.models import HTTPError
import urllib3
import json
import logging
import time
import sys
logging.getLogger('urllib3').propagate = False
urllib3.disable_warnings()

__author__ = 'Andy Nguyen'


class Target:
	def __init__(self, IP, v1_or_v2, user, passwd):
		self.IP = IP
		self.user = user
		self.passwd = passwd
		self.v1_or_v2 = v1_or_v2
		self.base_url = 'https://' + self.IP + '/api/' + self.v1_or_v2
		self.curr_ref = None
		self.failed_lock = False
		self.alarm_severity = {
			3: 'MAJOR',
			4: 'MINOR',
			5: 'NOTIFY'
		}
		self.clock_state = {
			0: 'Warmup',
			1: 'Freerun',
			2: 'Handset',
			3: 'Locking',
			4: 'Locked',
			5: 'Bridging',
			6: 'Holdover',
			7: 'Holdover expired',
			8: 'Recovering',
			9: 'Handset -M',
			10: 'Locked - M',
			11: 'Holdover - M'
		}
		self.api_input_time_src = {
			0: 'GNSS',
			1: 'Slot A J1 Timecode',
			2: 'Slot B J1 Timecode',
			3: 'PTP'
		}
		self.readable_input_time_src = {
			'GNSS': 0,
			'Slot A J1 Timecode': 1,
			'Slot B J1 Timecode': 2,
			'PTP': 3
		}
		self.reference_IDs = {
			0: 'GNSS',
			1: 'Slot A J1 Timecode',
			2: 'Slot B J1 Timecode',
			3: 'PPS Slot A',
			4: 'PPS Slot B',
			5: 'Frequency signal connected to J2 Slot A',
			6: 'Frequency signal connected to J2 Slot B',
			7: 'Frequency signal connected to J1 Slot A',
			8: 'Frequency signal connected to J1 Slot B',
			9: 'Frequency signal connected to J7 Slot A',
			10: 'Frequency signal connected to J7 Slot B',
			11: 'PTP',
			12: 'NTP',
			13: 'Standard',
			14: 'OCXO Oscillator',
			15: 'Rubidium Oscillator',
			16: 'High Performance Rubidium Oscillator'
		}
		self.version = None
		self.oscillator = None
		# When creating a Target object, need to check if server is up
		# self.ping_server()
		# If it is up, start a new session
		self.session = requests.Session()
		self.session.auth = (self.user, self.passwd)
		self.session.post(self.base_url, verify=False)
		# Check to make sure API is working correctly
		self.check_api()

	def ping_server(self):
		"""Pings server to see if it is up.

		Args:
				None

		Returns:
				True or Exit program because K2 is not up

		Raises:
				HTTPError: If there is an error in the request
		"""
		response = os.system('ping -c 1 ' + self.IP)
		if response == 0:
			logging.info("Successfully pinged server")
			# Ensures that api is working correctly
			return True
		else:
			logging.error('Unsuccessful connectin to server')
			sys.exit(1)

	def check_api(self):
		"""Makes a get request to /system/state see if the API is working correctly

		Args:
				None

		Returns:
				True or Exit program because there is an error in API

		Raises:
				HTTPError: If there is an error in the request
		"""
		try:
			url = self.base_url + '/system/inventory'
			response = self.session.get(url, verify=False)
			response.raise_for_status()
			data = json.loads(response.text)
			self.oscillator = data.get('inventory').get('oscillator')
			return True
		except requests.exceptions.HTTPError as e:
			logging.error(e)
			sys.exit(1)

	def get(self, endpoint):
		"""Makes a GET request using the given in self.IP

		Args:
				endpoint: API endpoint string ex: /system/state

		Returns:
				The data for the GET request

		Raises:
				HTTPError: If there is an error in the request
		"""
		try:
			url = self.base_url + endpoint
			response = self.session.get(url, verify=False)
			response.raise_for_status()
			data = json.loads(response.text)
			return data
		except requests.exceptions.HTTPError as e:
			logging.error(e)
			sys.exit(1)

	def post(self, endpoint, data):
		"""Makes a POST request using the given in self.IP

		Args:
				endpoint: API endpoint string ex: /system/state

		Returns:
				The status code if the POST request was successful

		Raises:
				HTTPError: If there is an error in the request
		"""
		try:
			url = self.base_url + endpoint
			response = self.session.post(
				url, data=json.dumps(data), verify=False)
			response.raise_for_status()
			return response.status_code
		except requests.exceptions.HTTPError as e:
			logging.error(e)
			sys.exit(1)

	def put(self, endpoint, data):
		"""Makes a PUT request using the given IP

		Args:
				endpoint: API endpoint string ex: /system/state

		Returns:
				The status code of if the PUT request was successful

		Raises:
				HTTPError: If there is an error in the request
		"""
		try:
			url = self.base_url + endpoint
			response = self.session.put(
				url, data=json.dumps(data), verify=False)
			response.raise_for_status()
			return response.status_code
		except requests.exceptions.HTTPError as e:
			logging.error(e)
			sys.exit(1)

	def delete(self, endpoint):
		"""Makes a DELETE request using the given IP

		Args:
				endpoint: API endpoint string ex: /system/state

		Returns:
				The status code of if the DELETE request was successful

		Raises:
				HTTPError: If there is an error in the request
		"""
		try:
			url = self.base_url + endpoint
			# For some reason the API requires you to pass in a empty {} to the data even though its optional
			response = self.session.delete(
				url, data=json.dumps({}), verify=False)
			response.raise_for_status()
		except requests.exceptions.HTTPError as e:
			logging.error(e)
			sys.exit(1)

	def pretty_print(self, data):
		print(json.dumps(data, indent=4))
	
	def get_image(self, image):
		"""Downloads the authorization and bin file for upgrade

		Args:
				image: Image class that has the data to ssh into the build to download the files
		"""
		image.get_image()

	def upgrade(self, image):
		"""Upgrades the K2 at self.IP to the latest build.The image is then passed to upgrade_poll which will poll until theserver is back up. 

		Args:
				image: Image class that has the data to ssh into the build to download the files

		Returns:
				True
		"""
		image.get_image()
		time.sleep(20)

		files = {('authfile', open(image.auth_name, 'rb')),
				 ('upgradefile', open(image.name, 'rb'))}
		data = {'authfile': image.auth_name, 'upgradefile': image.name}
		endpoint = '/admin/upgrade'
		system_inventory = '/system/inventory'
		system_data = self.get(system_inventory)
		software_version = system_data.get('softwareVer')
		if software_version != image.version:
			logging.info('Different versions. Current version = ' +
						 software_version + '. Software version = ' + image.version)
			try:
				url = self.base_url + endpoint
				response = self.session.post(
					url, files=files, data=data, verify=False)
				response.raise_for_status()
			except requests.exceptions.HTTPError as e:
				logging.error(e)
				sys.exit(1)
			logging.info(
				"Sleeping for 6 minutes to let K2 upgrade and reboot.")
			time.sleep(360)
			os.remove(image.auth_name)
			os.remove(image.name)
			return self.upgrade_poll(image)
		else:
			logging.info('Software versions are the same. No need to update.')
			os.remove(image.auth_name)
			os.remove(image.name)
		return True
		# need to continue polling until system is up.

	def upgrade_poll(self, image):
		"""Polls after upgrading until the K2 is back up by checking /syste/inventory for softwareVer.
		Checks to see if the upgrade is successful by comparing the version on the image and on the K2

		Args:
				image: Image class that has the data to ssh into the build to download the files	

		Return:
				True or False depending if the software version is the same as the image file
		"""
		sleep_count = 0
		endpoint = '/system/inventory'
		url = self.base_url + endpoint
		while True:
			try:
				if sleep_count > 10:  # just choose arbitrary number
					self.version = "Failed to get software version"
					logging.error('Failed to upgrade.')
					return False
				response = self.session.get(url, verify=False)
				response.raise_for_status()
				data = json.loads(response.text)
				self.version = data.get('softwareVer')
				if self.version == image.version:
					return True
				if self.version is not None:
					return False
			except requests.exceptions.HTTPError as e:
				logging.error(
					str(e) + 'Unsuccessful connectin to server. Sleeping still.')
				sleep_count += 1
				time.sleep(60)

	def reboot_poll(self):
		# need to let system reboot for some time before polling
		"""Polls after reboot until the K2 is up.

		Args:
				image: Image class that has the data to ssh into the build to download the files	

		Return:
				True or False depending if the software version is the same as the image file
		"""
		sleep_count = 0
		logging.info('Sleeping for 6 minutes for reboot')
		time.sleep(360)
		endpoint = '/system/state'
		while True:
			try:
				if sleep_count > 10:
					return False
				url = self.base_url + endpoint
				response = self.session.get(url, verify=False)
				response.raise_for_status()
				data = json.loads(response.text)
				curr_state = self.clock_state.get(int(data.get('syncState')))
				logging.info(curr_state)
				if curr_state is not None:
					return True
			except requests.exceptions.ConnectionError:
				logging.info("Server is still down. Sleeping for 5 seconds.")
				sleep_count += 1
				time.sleep(5)

	def lock_poll_for(self, endpoint, ref):
		"""Polls until it is "Locked" to the ref given.

		Args:
				endpoint: API endpoint string ex: /system/state
				ref: Reference that the user wants to lock to ex: GNSS, NTP, or PTP

		Return:
				True or False depending on if K2 is "Locked" to the given ref after 20 minutes
		"""
		sleep_count = 0
		url = self.base_url + endpoint
		while True:
			try:
				logging.info('Sleep count = ' + str(sleep_count))
				response = self.session.get(url, verify=False)
				response.raise_for_status()
				data = json.loads(response.text)
				state = self.clock_state.get(int(data.get('syncState')))
				sys_ref = self.reference_IDs.get(int(data.get('currRef')))
				if sleep_count > 30:
					logging.error('Failed to lock to ' + ref + '.')
					logging.error('Currently locked to ' + sys_ref + '.')
					self.curr_ref = 'FAILED. Timed out before locking.\nCurrently locked to ' + \
						sys_ref + '.\nCurrent sync state = ' + state + '.'
					self.failed_lock = True
					return False
				if state is not None and sys_ref is not None:
					logging.info('state = ' + state)
					logging.info('ref = ' + sys_ref)
					if state == 'Locked' and sys_ref == ref:
						logging.info('Sucessfully locked to ' + sys_ref + '.')
						self.curr_ref = sys_ref
						self.failed_lock = False
						return True
					else:
						logging.info('Sleeping for 60 seconds.')
						sleep_count += 1
						time.sleep(60)
				else:
					logging.info(
						'State or reference has a None type. Check dictionary.')
			except requests.exceptions.ConnectionError:
				time.sleep(30)

	def get_gnss_config_data_for(self, constellations, SBAS):
		"""Disables all other constellations except the given constellation

		Args:
				constellation: set of Constellations ex. {GLONASS}, {GLONASS, GPS, QZSS}, etc. 
				SBAS: enabled or disabled Space Based Augmentation System 

		Return:
				put_data necessary to make the PUT request
		"""
		endpoint = '/gnss'
		data = self.get(endpoint)
		satellites = data.get('constellation').get('satelliteSystem')
		for index, satellite in enumerate(satellites):
			if satellite.get('satConstellation').upper() in constellations:
				satellites[index].update({'state': 'enabled'})
			else:
				satellites[index].update({'state': 'disabled'})

		put_data = {
			'conf': {
				'constellation': {
					'satelliteSystem': satellites,
					'sbas': SBAS
				}
			}
		}
		return put_data

	# Misc functions

	def set_all_input_control_to(self, bool_value):
		"""Sets all the options(eg. PTP, GNSS, etc.) in input control to enabled/disabled.

		Args:
				bool_value: Either True or False 
		"""
		endpoint = '/timing'
		data = self.get(endpoint)
		time_ref = data.get('timeRefPriority')
		freq_ref = data.get('freqRefPriority')
		if self.v1_or_v2 == 'v2':
			# Only need to fix indexes for v2
			for index, input in enumerate(time_ref):
				time_ref[index].update({'enabled': bool_value})
				num = input.get('priority')
				# Need to add 1 to all the priorities because the API bug and the indices are off
				# GET request gives back indices 0 to 3 but API needs 1 to 4 to work

				# don't need to increase priority for 4.X.X/v1
				time_ref[index].update({'priority': num + 1})

			# Need to also do it for the frequency response
			for index, input in enumerate(freq_ref):
				freq_ref[index].update({'enabled': bool_value})
				num = input.get('priority')
				# Need to add 1 to all the priorities because the API bug and the indices are off
				# GET request gives back indices 0 to 3 but API needs 1 to 4 to work
				freq_ref[index].update({'priority': num + 1})

		data.update({'timeRefPriority': time_ref})
		#data.update({'freqRefPriority': freq_ref})
		config = {'timing': data}
		self.put('/timing', config)

	def get_alarm_severity(self, data):
		alarm_state_id = int(data.get('severity'))
		return self.alarm_severity.get(alarm_state_id)

	def get_input_time_src(self, data):
		input_state_id = int(data.get('source'))
		return self.api_input_time_src.get(input_state_id)

	def del_all_ntp_servers(self):
		"""Deletes all NTP servers.
		"""
		endpoint = '/ntp/servers'
		servers = self.get(endpoint)
		if len(servers) > 0:
			for _ in servers:
				# It is always 1 because once you delete an alarm, the position of the second alarm becomes 1
				self.delete('/ntp/servers/1')

	def add_ntp_server(self, ntp_list):
		"""Adds a NTP server to the K2 at self.IP

		Args:
				ntp_list: list of NTP servers ex. [{'role': 0, 'addrName': '10.241.55.21'}]
		"""
		endpoint = '/ntp/servers'
		# Will change this to ntp_list when I start adding NTP servers
		data = {'servers': [{'role': 0, 'addrName': '10.241.55.21'}]}
		self.post(endpoint, data)

	def setup_gnss_prefer_to(self, bool_value):
		"""Sets Hardware Reference Clock in NTPd Config page to prefered or unpreferred.

		Args:
				bool_value: True or False
		"""
		endpoint = '/ntp/option'
		data = {'option': {'hwRefClockPrefer': bool_value,
						   'ntpQueryEnable': False, 'leapSmearEnable': False}}
		self.put(endpoint, data)

	def setup_ntp_prefer_to(self, bool_value, server_ip):
		"""Sets the current NTP server on NTPd Config page to either preferred or unpreferred 

		Args:
				bool_value: True or False
		"""
		# May need to change in future if there are multiple NTP servers. Only coded for one NTP server.
		endpoint = '/ntp/servers'
		data = self.get(endpoint)
		for index, s in enumerate(data, start=1):
			if s.get('addrName') == server_ip:
				s.update({'prefer': bool_value})
				server_config = {'server': s}
				self.put('/ntp/servers/' + str(index), server_config)

	def reset_ntp(self):
		"""Resets the NTP server. Basically clicking restart on NTPd Config page through code."""
		endpoint = '/ntp/servers'
		data = {'restart': True}
		self.post(endpoint, data)

	def switch_input_prio_validation(self, reference, t_list):
		"""Makes sure the the reference input given is valid.

		Args:
				reference: input reference given by user
				t_list: list of timeRefPriority from API get request

		Rasies:
				Invalid reference eg. reference = GNSSSSS Or PTO
				Reference is not currently listed in input source eg. Not listed in input config page
		"""
		if reference not in self.readable_input_time_src:
			logging.error(
				'Invalid reference. Please check spelling. Given reference = ' + reference)
			sys.exit(1)

		valid_curr_ref = False
		for time in t_list:
			if time.get('source') == self.readable_input_time_src.get(reference):
				valid_curr_ref = True
		if not valid_curr_ref:
			logging.error('Given reference ' + reference +
						  ' is not currently listed in input control. Please add it or give a different reference.')
			sys.exit(1)

	def find_reference_switch_index(self, reference, t_list):
		"""Finds what reference to switch the given reference with.
		ex. If PTP is the 1st priority and I want to switch it with reference given eg. GNSS
		old = index of PTP
		new = index of GNSS
		PTP new priority will be GNSS's old priority and GNSS will now be 1st priority

		Args:
				reference: input reference given by user
				t_list: list of timeRefPriority from API get request

		Returns:
				Tuple of the old and new index
		"""
		old = None
		new = None
		for index, time in enumerate(t_list):
			source = time.get('source')
			priority = time.get('priority')
			if self.v1_or_v2 == 'v2':
				# This is for 5.X.X.XX
				if priority == 0 and self.api_input_time_src.get(source) == reference:
					return None, None
				if priority == 0:
					new = index
				if self.api_input_time_src.get(source) == reference:
					old = index
			if self.v1_or_v2 == 'v1':
				# This is  for 4.X.X.XX
				if priority == 1 and self.api_input_time_src.get(source) == reference:
					return None, None
				if priority == 1:
					new = index
				if self.api_input_time_src.get(source) == reference:
					old = index
		if old is not None and new is not None:
			logging.info('Switching ' +
						 str(t_list[old]) + ' with ' + str(t_list[new]))
		return old, new

	def set_input_priority_to(self, reference):
		"""Switches priority from what the currently prefered input is to the reference given.

		Args:
				reference: Input reference eg. GNSS, PTP, Slot A J1 Timecode, etc. 
		"""
		endpoint = '/timing'
		data = self.get(endpoint)
		t_list = data.get('timeRefPriority')

		# validates reference input
		self.switch_input_prio_validation(reference, t_list)
		old, new = self.find_reference_switch_index(reference, t_list)
		# If old or new is None then it means the given reference is already the first priority
		# Only go inside if statement if we need to change the priority
		if old is not None and new is not None:
			if self.v1_or_v2 == 'v2':
				# all of this bellow is for 5.0
				# switches the priority between the current priority and the reference given
				t_list[new].update({'priority': t_list[old].get('priority')})
				t_list[old].update({'priority': 0})
				# Need to loop through the list and add 1 to the priority to satisfy API requirements.
				# The get reuqest when returned, uses 0 to 3 index for priority.
				# The post request needs to be in a 1 to 4 index for it to work properly
				# Will delete if they ever change the get request to be 1 to 4 index
				for index, _ in enumerate(t_list):
					curr_prio = t_list[index].get('priority')
					curr_prio += 1
					t_list[index].update({'priority': curr_prio})
			if self.v1_or_v2 == 'v1':
				# this is for 4.1
				t_list[new].update({'priority': t_list[old].get('priority')})
				t_list[old].update({'priority': 1})

			data = {'timing': {'timeRefPriority': t_list}}
			self.put(endpoint, data)
			logging.info('Successfully switched input references.')

	def clock_class(self):
		d = self.get('/timingService/status')

		# print(d)
		print(json.dumps(d, indent=2))
		clock_class = d[0].get('status').get('clockClass')
		print(clock_class)
