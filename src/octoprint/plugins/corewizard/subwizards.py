# coding=utf-8
from __future__ import absolute_import, division, print_function

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import octoprint.plugin

import sys
import inspect
from flask.ext.babel import gettext


# noinspection PyUnresolvedReferences,PyMethodMayBeStatic
class ServerCommandsSubwizard(object):
	def _is_servercommands_wizard_firstrunonly(self):
		return True

	def _is_servercommands_wizard_required(self):
		system_shutdown_command = self._settings.global_get(["server", "commands", "systemShutdownCommand"])
		system_restart_command = self._settings.global_get(["server", "commands", "systemRestartCommand"])
		server_restart_command = self._settings.global_get(["server", "commands", "serverRestartCommand"])

		return not (system_shutdown_command and system_restart_command and server_restart_command)

	def _get_servercommands_wizard_details(self):
		return dict(required=self._is_servercommands_wizard_required())

	def _get_servercommands_wizard_name(self):
		return gettext("Server Commands")


# noinspection PyUnresolvedReferences,PyMethodMayBeStatic
class WebcamSubwizard(object):
	def _is_webcam_wizard_firstrunonly(self):
		return True

	def _is_webcam_wizard_required(self):
		webcam_snapshot_url = self._settings.global_get(["webcam", "snapshot"])
		webcam_stream_url = self._settings.global_get(["webcam", "stream"])
		ffmpeg_path = self._settings.global_get(["webcam", "ffmpeg"])

		return not (webcam_snapshot_url and webcam_stream_url and ffmpeg_path)

	def _get_webcam_wizard_details(self):
		return dict(required=self._is_webcam_wizard_required())

	def _get_webcam_wizard_name(self):
		return gettext("Webcam & Timelapse")


# noinspection PyUnresolvedReferences,PyMethodMayBeStatic
class AclSubwizard(object):
	def _is_acl_wizard_firstrunonly(self):
		return True

	def _is_acl_wizard_required(self):
		return self._user_manager.enabled and not self._user_manager.hasBeenCustomized()

	def _get_acl_wizard_details(self):
		return dict(required=self._is_acl_wizard_required())

	def _get_acl_wizard_name(self):
		return gettext("Access Control")

	def _get_acl_additional_wizard_template_data(self):
		return dict(mandatory=self._is_acl_wizard_required())

	@octoprint.plugin.BlueprintPlugin.route("/acl", methods=["POST"])
	def acl_wizard_api(self):
		from flask import request, abort
		from octoprint.server.api import valid_boolean_trues, NO_CONTENT

		if not self._settings.global_get(["server", "firstRun"]) or self._user_manager.hasBeenCustomized():
			abort(404)

		data = request.values
		if hasattr(request, "json") and request.json:
			data = request.json

		if "ac" in data and data["ac"] in valid_boolean_trues and \
						"user" in data.keys() and "pass1" in data.keys() and \
						"pass2" in data.keys() and data["pass1"] == data["pass2"]:
			# configure access control
			self._settings.global_set_boolean(["accessControl", "enabled"], True)
			self._user_manager.enable()
			self._user_manager.addUser(data["user"], data["pass1"], True, ["user", "admin"], overwrite=True)
		elif "ac" in data.keys() and not data["ac"] in valid_boolean_trues:
			# disable access control
			self._settings.global_set_boolean(["accessControl", "enabled"], False)

			octoprint.server.loginManager.anonymous_user = octoprint.users.DummyUser
			octoprint.server.principals.identity_loaders.appendleft(octoprint.users.dummy_identity_loader)

			self._user_manager.disable()
		self._settings.save()
		return NO_CONTENT


# noinspection PyUnresolvedReferences,PyMethodMayBeStatic
class OnlineCheckSubwizard(object):
	def _is_onlinecheck_wizard_firstrunonly(self):
		return False

	def _is_onlinecheck_wizard_required(self):
		return self._settings.global_get(["server", "onlineCheck", "enabled"]) is None

	def _get_onlinecheck_wizard_details(self):
		return dict(required=self._is_onlinecheck_wizard_required())

	def _get_onlinecheck_wizard_name(self):
		return gettext("Online connectivity check")

	def _get_onlinecheck_additional_wizard_template_data(self):
		return dict(mandatory=self._is_onlinecheck_wizard_required())


# noinspection PyUnresolvedReferences,PyMethodMayBeStatic
class PluginBlacklistSubwizard(object):
	def _is_pluginblacklist_wizard_firstrunonly(self):
		return False

	def _is_pluginblacklist_wizard_required(self):
		return self._settings.global_get(["server", "pluginBlacklist", "enabled"]) is None

	def _get_pluginblacklist_wizard_details(self):
		return dict(required=self._is_pluginblacklist_wizard_required())

	def _get_pluginblacklist_wizard_name(self):
		return gettext("Plugin blacklist")

	def _get_pluginblacklist_additional_wizard_template_data(self):
		return dict(mandatory=self._is_pluginblacklist_wizard_required())


# noinspection PyUnresolvedReferences,PyMethodMayBeStatic
class PrinterProfileSubwizard(object):
	def _is_printerprofile_wizard_firstrunonly(self):
		return True

	def _is_printerprofile_wizard_required(self):
		return self._printer_profile_manager.is_default_unmodified() and self._printer_profile_manager.profile_count == 1

	def _get_printerprofile_wizard_details(self):
		return dict(required=self._is_printerprofile_wizard_required())

	def _get_printerprofile_wizard_name(self):
		return gettext("Default Printer Profile")

class SSHSubwizard(object):
	def _is_ssh_wizard_firstrunonly(self):
		return True

	def _is_ssh_wizard_required(self):
		return True

	def _get_ssh_wizard_details(self):
		return dict(required=self._is_ssh_wizard_required())

	def _get_ssh_wizard_name(self):
		return gettext("SSH Control")

	def _get_ssh_additional_wizard_template_data(self):
		return dict(mandatory=self._is_acl_wizard_required())

	@octoprint.plugin.BlueprintPlugin.route("/ssh", methods=["POST"])
	def get_ssh_control(self):
		import subprocess
		from flask import request, abort
		from octoprint.server.api import NO_CONTENT
		valid_boolean_trues = [True, "true", "yes", "y", "1"]
		valid_boolean_falses = [False, "false", "no", "n", "0"]

		if not self._settings.global_get(["server", "firstRun"]):
			abort(404)

		data = request.values
		if hasattr(request, "json") and request.json:
			data = request.json

		action = []

		if "ssh" in data and data["ssh"] in valid_boolean_trues:
			enable = 'sudo systemctl enable ssh'
			start = 'sudo systemctl start ssh'
			action.append(enable)
			action.append(start)

		elif "ssh" in data and data["ssh"] in valid_boolean_falses:
			disable = 'sudo systemctl disable ssh'
			stop = 'sudo systemctl stop ssh'
			action.append(disable)
			action.append(stop)
		else:
			self._logger.info("Supplied action could not be taken")

		if len(action) != 0:
			for act in action:
				self._logger.info("Executing command: {}".format(act))
				temp_p = subprocess.Popen(act,
							stdout=subprocess.PIPE,
							shell=True
						 )
				output, error = temp_p.communicate()
				p_status = temp_p.wait()

				self._logger.info(output)
				self._logger.info(error)
				self._logger.info(p_status)
		else:
			self._logger.info("No Actions could be taken")


		return NO_CONTENT



	@octoprint.plugin.BlueprintPlugin.route("/ssh/status", methods=["GET"])
	def ssh_get_status(self):
		import subprocess
		try:
			o = subprocess.check_output(['sudo','service','ssh','status'])
			is_enabled = 'Active: active' in o
		except subprocess.CalledProcessError as e:
			is_enabled = False
		finally:
			return "enabled" if is_enabled else "disabled"






Subwizards = type("Subwizwards",
				  tuple(cls for clsname, cls in inspect.getmembers(sys.modules[__name__], inspect.isclass)
						if clsname.endswith("Subwizard")),
				  dict())
