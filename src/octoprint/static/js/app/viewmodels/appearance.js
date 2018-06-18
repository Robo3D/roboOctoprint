$(function() {
    function AppearanceViewModel(parameters) {
        var self = this;

        self.name = parameters[0].appearance_name;
        self.color = parameters[0].appearance_color;
        self.colorTransparent = parameters[0].appearance_colorTransparent;
        self.hostname = ""

        var request = new XMLHttpRequest()

        // Override function to handle server response
        request.onreadystatechange = function() {
          if (request.readyState == XMLHttpRequest.DONE) {
            console.log(request.response);
            self.hostname = request.response;
          }
        }
        request.open("GET", "api/printer/hostname");
        request.setRequestHeader("Content-Type", "application/json");
        request.setRequestHeader("X-Api-Key", OctoPrint.options.apikey);

        request.send();

        self.brand = ko.pureComputed(function() {
            // if (self.name())
            //     return self.name();
            // else
            //     return gettext("OctoPrint");
            return self.hostname
        });

        self.fullbrand = ko.pureComputed(function() {
            // if (self.name())
            //     return gettext("OctoPrint") + ": " + self.name();
            // else
            //     return gettext("OctoPrint");
            return self.hostname




        });

        self.title = ko.pureComputed(function() {
            // if (self.name())
            //     return self.name() + " [" + gettext("OctoPrint") + "]";
            // else
            //     return gettext("OctoPrint");
            return self.hostname
        });
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: AppearanceViewModel,
        dependencies: ["settingsViewModel"],
        elements: ["head"]
    });
});
