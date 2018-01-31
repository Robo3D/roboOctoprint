$(function() {
    function SystemViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.usersVM = parameters[1];

        self.lastCommandResponse = undefined;
        self.systemActions = ko.observableArray([]);

        self.requestData = function() {
            self.requestCommandData();
        };

        self.requestCommandData = function() {
            if (!self.loginState.isAdmin()) {
                return $.Deferred().reject().promise();
            }

            return OctoPrint.system.getCommands()
                .done(self.fromCommandResponse);
        };

        self.currentUser = null;
        self.editAccessControl = function(actions){
            // ensures that only 1 access control option exists depending on the state of access control (enabled or disabled)
            // :param: actions (array of objects)
            // :returns: edited_actions(array of objects)
            // objects have following properties: action, actionSource, confirm, name, resource, source (all strings)
            var isAcEnabled = self.usersVM.listHelper.allSize() > 0;
            return _.filter(actions, function (data) {
                if ( data.action == 'aclon' ){
                    return !isAcEnabled;
                }
                else if ( data.action == 'acloff' ){
                    return isAcEnabled && self.currentUser.admin;
                }
                else {
                    return true;
                }
            });
        };

        self.fromCommandResponse = function(response) {
            var actions = [];
            if (response.core && response.core.length) {
                _.each(response.core, function(data) {
                    var action = _.extend({}, data);
                    action.actionSource = "core";
                    actions.push(action);
                });
                if (response.custom && response.custom.length) {
                    actions.push({action: "divider"});
                }
            }
            _.each(response.custom, function(data) {
                var action = _.extend({}, data);
                action.actionSource = "custom";
                actions.push(action);
            });
            self.lastCommandResponse = response;
            self.systemActions(self.editAccessControl(actions) );
        };

        self.triggerCommand = function(commandSpec) {
            var deferred = $.Deferred();

            var callback = function() {
                OctoPrint.system.executeCommand(commandSpec.actionSource, commandSpec.action)
                    .done(function() {
                        if ( commandSpec.action == 'aclon' || commandSpec.action == 'acloff' ){
                            new PNotify({title: "Success", text: _.sprintf(gettext("The command \"%(command)s\" executed successfully. Octoprint will restart automatically..."), {command: commandSpec.name}), type: "success"});
                            deferred.resolve(["success", arguments]);
                            self.triggerCommand({
                                action: "restart",
                                actionSource: "core",
                                name: "Restart OctoPrint"
                            });

                        }
                        else {
                            new PNotify({title: "Success", text: _.sprintf(gettext("The command \"%(command)s\" executed successfully"), {command: commandSpec.name}), type: "success"});
                            deferred.resolve(["success", arguments]);
                        }
                    })
                    .fail(function(jqXHR, textStatus, errorThrown) {
                        if (!commandSpec.hasOwnProperty("ignore") || !commandSpec.ignore) {
                            var error = "<p>" + _.sprintf(gettext("The command \"%(command)s\" could not be executed."), {command: commandSpec.name}) + "</p>";
                            error += pnotifyAdditionalInfo("<pre>" + jqXHR.responseText + "</pre>");
                            new PNotify({title: gettext("Error"), text: error, type: "error", hide: false});
                            deferred.reject(["error", arguments]);
                        } else {
                            deferred.resolve(["ignored", arguments]);
                        }
                    });
            };

            if (commandSpec.confirm) {
                showConfirmationDialog({
                    message: commandSpec.confirm,
                    onproceed: function() {
                        callback();
                    },
                    oncancel: function() {
                        deferred.reject("cancelled", arguments);
                    }
                });
            } else {
                callback();
            }

            return deferred.promise();
        };

        self.onUserLoggedIn = function(user) {
            self.currentUser = user;
            if (user.admin) {
                self.requestData();
            } else {
                self.onUserLoggedOut();
            }
        };

        self.onUserLoggedOut = function() {
            self.lastCommandResponse = undefined;
            self.systemActions([]);
        };

        self.onEventSettingsUpdated = function() {
            if (self.loginState.isAdmin()) {
                self.requestData();
            }
        };
    }

    // view model class, parameters for constructor, container to bind to
    ADDITIONAL_VIEWMODELS.push([
        SystemViewModel,
        ["loginStateViewModel", "usersViewModel"],
        []
    ]);
});
