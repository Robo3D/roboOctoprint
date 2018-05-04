# coding=utf-8
from __future__ import absolute_import, division, print_function

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import collections
import logging
import sarge
import threading

from flask import request, make_response, jsonify, url_for
from flask.ext.babel import gettext

from octoprint.settings import settings as s

import octoprint.server
from octoprint.server import admin_permission, NO_CONTENT
from octoprint.server.api import api
from octoprint.server.util.flask import restricted_access, get_remote_address
from octoprint.logging import prefix_multilines


@api.route("/system", methods=["POST"])
@restricted_access
@admin_permission.require(403)
def performSystemAction():
	logging.getLogger(__name__).warn("Deprecated API call to /api/system made by {}, should be migrated to use /system/commands/custom/<action>".format(get_remote_address(request)))

	data = request.values
	if hasattr(request, "json") and request.json:
		data = request.json

	if not "action" in data:
		return make_response("action to perform is not defined", 400)

	return executeSystemCommand("custom", data["action"])


@api.route("/system/commands", methods=["GET"])
@restricted_access
@admin_permission.require(403)
def retrieveSystemCommands():
	return jsonify(core=_to_client_specs(_get_core_command_specs()),
	               custom=_to_client_specs(_get_custom_command_specs()))


@api.route("/system/commands/<string:source>", methods=["GET"])
@restricted_access
@admin_permission.require(403)
def retrieveSystemCommandsForSource(source):
	if source == "core":
		specs = _get_core_command_specs()
	elif source == "custom":
		specs = _get_custom_command_specs()
	else:
		return make_response("Unknown system command source: {}".format(source), 404)

	return jsonify(_to_client_specs(specs))


@api.route("/system/commands/<string:source>/<string:command>", methods=["POST"])
@restricted_access
@admin_permission.require(403)
def executeSystemCommand(source, command):
	logger = logging.getLogger(__name__)

	if command == "divider":
		return make_response("Dividers cannot be executed", 400)

	command_spec = _get_command_spec(source, command)
	if not command_spec:
		return make_response("Command {}:{} not found".format(source, command), 404)

	if not "command" in command_spec:
		return make_response("Command {}:{} does not define a command to execute, can't proceed".format(source, command), 500)

	do_async = command_spec.get("async", False)
	do_ignore = command_spec.get("ignore", False)
	debug = command_spec.get("debug", False)

	if logger.isEnabledFor(logging.DEBUG) or debug:
		logger.info("Performing command for {}:{}: {}".format(source, command, command_spec["command"]))
	else:
		logger.info("Performing command for {}:{}".format(source, command))

	try:
		if "before" in command_spec and callable(command_spec["before"]):
			command_spec["before"]()
	except Exception as e:
		if not do_ignore:
			error = "Command \"before\" for {}:{} failed: {}".format(source, command, str(e))
			logger.warn(error)
			return make_response(error, 500)

	try:
		def execute():
			# we run this with shell=True since we have to trust whatever
			# our admin configured as command and since we want to allow
			# shell-alike handling here...
			p = sarge.run(command_spec["command"],
			              stdout=sarge.Capture(),
			              stderr=sarge.Capture(),
			              shell=True)

			if not do_ignore and p.returncode != 0:
				returncode = p.returncode
				stdout_text = p.stdout.text
				stderr_text = p.stderr.text

				error = "Command for {}:{} failed with return code {}:\nSTDOUT: {}\nSTDERR: {}".format(source, command,
				                                                                                       returncode,
				                                                                                       stdout_text,
				                                                                                       stderr_text)
				logger.warn(prefix_multilines(error, prefix="! "))
				if not do_async:
					raise CommandFailed(error)

		if do_async:
			thread = threading.Thread(target=execute)
			thread.daemon = True
			thread.start()

		else:
			try:
				execute()
			except CommandFailed as exc:
				return make_response(exc.error, 500)

	except Exception as e:
		if not do_ignore:
			error = "Command for {}:{} failed: {}".format(source, command, str(e))
			logger.warn(error)
			import traceback
			err = traceback.format_exc()
			logger.warn(err)
			return make_response(error, 500)

	return NO_CONTENT


def _to_client_specs(specs):
	result = list()
	for spec in specs.values():
		if not "action" in spec or not "source" in spec:
			continue
		copied = dict((k, v) for k, v in spec.items() if k in ("source", "action", "name", "confirm"))
		copied["resource"] = url_for(".executeSystemCommand",
		                             source=spec["source"],
		                             command=spec["action"],
		                             _external=True)
		result.append(copied)
	return result


def _get_command_spec(source, action):
	if source == "core":
		return _get_core_command_spec(action)
	elif source == "custom":
		return _get_custom_command_spec(action)
	else:
		return None


def _get_core_command_specs():
	def enable_safe_mode():
		s().set(["server", "startOnceInSafeMode"], True)
		s().save()

	acl_enabled = octoprint.server.userManager.enabled
	def set_acl_wizard():
		
		if acl_enabled:
			#disable acl
			s().set(['accessControl', 'enabled'], False)
			s().set(['accessControl', 'salt'], None)
			s().save()

			#delete users.yaml
			import os
			homedir = os.path.expanduser("~")
			if type(homedir) is list:
				homedir = homedir[0]
			users_file = homedir + "/.octoprint/users.yaml"
			if os.path.isfile(users_file):
				os.remove(users_file)
		else:
			#enable acl
			acl = s().get(['accessControl'])
			if not ('salt' in acl):
				s().set(['accessControl', 'enabled'], True)
				s().set(['server', 'firstRun'], True)
				s().save()
	
	name = ""
	confirmation = ""

	if acl_enabled:
		name = "Disable remote access security feature"
		confirmation = ("You are about to disable the remote access security features and DELETE all user accounts. This will make your printer remotely accessible to everyone within your local network. The dashboard and your printer will automatically restart. This will disrupt any active prints.")
	else:
		name = "Enable remote access security feature" 
		confirmation = ("You are about to launch the setup wizard to enable remote access security features. You will have to complete the wizard in order to continue using the web dashboard. The dashboard and your printer will automatically restart once the wizard is finished. This will disrupt any active prints.")
	
	commands = collections.OrderedDict()
	commands['shutdown']=dict(
		command=s().get(["server", "commands", "systemShutdownCommand"]),
		name=gettext("Shutdown system"),
		confirm=gettext("<strong>You are about to shutdown the system.</strong></p><p>This action may disrupt any ongoing print jobs (depending on your printer's controller and general setup that might also apply to prints run directly from your printer's internal storage).")
		)
	commands['reboot']=dict(
		command=s().get(["server", "commands", "systemRestartCommand"]),
		name=gettext("Reboot system"),
		confirm=gettext("<strong>You are about to reboot the system.</strong></p><p>This action may disrupt any ongoing print jobs (depending on your printer's controller and general setup that might also apply to prints run directly from your printer's internal storage).")
		)
	commands['restart']=dict(
		command=s().get(["server", "commands", "serverRestartCommand"]),
		name=gettext("Restart OctoPrint"),
		confirm=gettext("<strong>You are about to restart the OctoPrint server.</strong></p><p>This action may disrupt any ongoing print jobs (depending on your printer's controller and general setup that might also apply to prints run directly from your printer's internal storage).")
		)
	commands['restart_safe']=dict(
		command=s().get(["server", "commands", "serverRestartCommand"]),
		name=gettext("Restart OctoPrint in safe mode"),
		confirm=gettext("<strong>You are about to restart the OctoPrint server in safe mode.</strong></p><p>This action may disrupt any ongoing print jobs (depending on your printer's controller and general setup that might also apply to prints run directly from your printer's internal storage)."),
		before=enable_safe_mode)
	commands['robo_security_wizard']=dict(
		command=s().get(["server", "commands", "serverRestartCommand"]),
		name=name,
		confirm=confirmation,
		before=set_acl_wizard)

	available_commands = collections.OrderedDict()
	for action, spec in commands.items():
		if not spec["command"]:
			continue
		spec.update(dict(action=action,
		                 source="core",
		                 async=True,
		                 debug=True))
		available_commands[action] = spec
	
	return available_commands


def _get_core_command_spec(action):
	available_actions = _get_core_command_specs()
	if not action in available_actions:
		logging.getLogger(__name__).warn("Command for core action {} is not configured, you need to configure the command before it can be used".format(action))
		return None

	return available_actions[action]


def _get_custom_command_specs():
	specs = collections.OrderedDict()
	dividers = 0
	for spec in s().get(["system", "actions"]):
		if not "action" in spec:
			continue
		copied = dict(spec)
		copied["source"] = "custom"

		action = spec["action"]
		if action == "divider":
			dividers += 1
			action = "divider_{}".format(dividers)
		specs[action] = copied
	return specs


def _get_custom_command_spec(action):
	available_actions = _get_custom_command_specs()
	if not action in available_actions:
		return None

	return available_actions[action]


class CommandFailed(Exception):
	def __init__(self, error):
		self.error = error
