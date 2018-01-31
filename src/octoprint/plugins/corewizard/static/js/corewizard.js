$(function() {
    function CoreWizardAclViewModel(parameters) {
        var self = this;

        self.loginStateViewModel = parameters[0];
        self.wizardViewModel = parameters[1];

        self.username = ko.observable(undefined);
        self.password = ko.observable(undefined);
        self.confirmedPassword = ko.observable(undefined);

        self.decision = ko.observable();

        self.acRadio = ko.observable('enabled');
        self.acRadio.subscribe(function (newValue) {
          var msg;
          if (newValue == 'enabled') {
            msg = 'enable Access Control';
          }
          else {
            msg = 'disable Access Control';
            self.username(undefined);
            self.password(undefined);
            self.confirmedPassword(undefined);
          }
          $('#acMsg').text(msg);
        });

        self.passwordMismatch = ko.pureComputed(function() {
            return self.password() != self.confirmedPassword();
        });

        self.validUsername = ko.pureComputed(function() {
            return self.username() && self.username().trim() != "";
        });

        self.validPassword = ko.pureComputed(function() {
            return self.password() && self.password().trim() != "";
        });

        self.validData = ko.pureComputed(function() {
            return !self.passwordMismatch() && self.validUsername() && self.validPassword();
        });

        self.keepAccessControl = function() {
            if (!self.validData()) return;

            var data = {
                "ac": true,
                "user": self.username(),
                "pass1": self.password(),
                "pass2": self.confirmedPassword()
            };

            self._sendData(data, function () {
                // Currently, login function occurs after .finishWizard gets called. this causes a 401 error that halts the execution of .finishWizard.done(). Rerun .finishWizard and .done as callback function after login completes.
                self.wizardViewModel.wizards = ["corewizard"];
                self.wizardViewModel.finishWizard()
                    .done(function () {
                        self.wizardViewModel.closeDialog();
                        self.wizardViewModel.reloadOverlay.show();
                    });
            });
        };

        self.disableAccessControl = function() {
          var data = { "ac": false };
          self._sendData(data);
        };

        self._sendData = function(data, callback) {
            OctoPrint.postJson("plugin/corewizard/acl", data)
                .done(function() {
                    self.decision(data.ac);
                    if (data.ac) {
                        // we now log the user in
                        var user = data.user;
                        var pass = data.pass1;
                        self.loginStateViewModel.login(user, pass, true)
                            .done(function() {
                                if (callback) callback();
                            });
                    } else {
                        if (callback) callback();
                    }
                });
        };

        self.onBeforeWizardTabChange = function(next, current) {
            if (!current || !_.startsWith(current, "wizard_plugin_corewizard_acl_") || self.acRadio() != 'enabled' ) {
                return true;
            }

            if (self.acRadio()=='enabled' && !self.validData()) {
              var results = [
                { name: "Invalid username", isValid: self.validUsername() },
                { name: "Invalid password", isValid: self.validPassword() },
                { name: "Passwords do not match", isValid: !self.passwordMismatch() }
              ];
              var msg = 'Please look over the username and password form.</br>';
              for (var i = 0; i < results.length; i++) {
                var addition = results[i].name + "</br>";
                if ( !results[i].isValid ) msg += addition;
              }

              showMessageDialog({
                  title: gettext("Enter valid username and password"),
                  message: gettext(msg),
                  close: "Ok"
              });
              return false;
            }
            else {
              return true;
            }
        };

        self.onWizardFinish = function() {
            if (!self.decision()) {
                if ( self.acRadio() == 'enabled' ) {
                  self.keepAccessControl();
                }
                else {
                  self.disableAccessControl();
                }
                return "reload";
            }
        };
    }

    function CoreWizardSSHViewModel(parameters){
      var self = this;

      self.settingsViewModel = parameters[0];

      self.sshRadio = ko.observable('disabled');
      self.sshRadio.subscribe(function (newValue) {
        var msg;
        if (newValue == 'enabled'){
          msg = 'enable SSH';
        }
        else{
          msg = 'disable SSH';
        }
        $('#sshMsg').text(msg);
      });

      self.enableSSH = function () {
        if (self.sshRadio == 'enabled') {
          var data = { "ssh": true };
          self._sendData(data);
        }
      };

      self._sendData = function (data) {
        OctoPrint.postJson("plugin/corewizard/ssh", data)
          .done(function () {
          });
      };

      self.onWizardFinish = function () {
        var data = {ssh: null};
        if (self.sshRadio() == 'enabled') {
          data.ssh = true;
        }
        else {
          data.ssh = false;
        }
        self._sendData(data);
        return "reload";
      };

    }

    function CoreWizardWebcamViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];

        self.onWizardFinish = function() {
            if (self.settingsViewModel.webcam_streamUrl()
                || (self.settingsViewModel.webcam_snapshotUrl() && self.settingsViewModel.webcam_ffmpegPath())) {
                return "reload";
            }
        }
    }

    function CoreWizardServerCommandsViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];
    }

    function CoreWizardPrinterProfileViewModel(parameters) {
        var self = this;

        self.printerProfiles = parameters[0];

        self.editor = self.printerProfiles.createProfileEditor();
        self.editorLoaded = ko.observable(false);

        self.onStartup = function() {
            OctoPrint.printerprofiles.get("_default")
                .done(function(data) {
                    self.editor.fromProfileData(data);
                    self.editorLoaded(true);
                });
        };

        self.onWizardFinish = function() {
            OctoPrint.printerprofiles.update("_default", self.editor.toProfileData())
                .done(function() {
                    self.printerProfiles.requestData();
                });
        };
    }

    OCTOPRINT_VIEWMODELS.push([
        CoreWizardAclViewModel,
        ["loginStateViewModel", "wizardViewModel"],
        "#wizard_plugin_corewizard_acl"
    ], [
        CoreWizardSSHViewModel,
        ['settingsViewModel'],
        '#wizard_plugin_corewizard_ssh'
    ], [
        CoreWizardWebcamViewModel,
        ["settingsViewModel"],
        "#wizard_plugin_corewizard_webcam"
    ], [
        CoreWizardServerCommandsViewModel,
        ["settingsViewModel"],
        "#wizard_plugin_corewizard_servercommands"
    ], [
        CoreWizardPrinterProfileViewModel,
        ["printerProfilesViewModel"],
        "#wizard_plugin_corewizard_printerprofile"
    ]);
});
