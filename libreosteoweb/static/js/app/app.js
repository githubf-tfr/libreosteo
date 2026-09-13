
/**
    This file is part of LibreOsteo.

    LibreOsteo is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    LibreOsteo is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
*/
var libreosteoApp = angular.module('libreosteo', [
    'ngCookies',
    'xeditable',
    'ui.bootstrap',
    'loPatient',
    'loTimeline',
    'loDashboard',
    'loOfficeEvent',
    'loInvoice',
    'yaru22.angular-timeago',
    'ngAnimate',
    'duScroll',
    'loUser',
    'angular-growl',
    'angular-loading-bar',
    'ui.router',
    'angular-toArrayFilter',
    'ui.validate',
    'loOfficeSettings',
    'infinite-scroll',
    'loEditFormManager',
    'loHalloEditor',
    'ngFileUpload',
    'loFileManager',
    'angular-bind-html-compile'
]);

libreosteoApp.config(function ($interpolateProvider) {
  $interpolateProvider.startSymbol('{$');
  $interpolateProvider.endSymbol('$}');
});

libreosteoApp.run(function (editableOptions) {
  editableOptions.theme = 'bs3'; // bootstrap3 theme. Can be also 'bs2', 'default'
});

libreosteoApp.run(['$http', '$cookies', function ($http, $cookies) {
    $http.defaults.xsrfHeaderName = 'X-CSRFToken';
    $http.defaults.xsrfCookieName = 'csrftoken';
}]);

libreosteoApp.config(function($httpProvider) {
  $httpProvider.interceptors.push(function($q, $location) {
    return {
      'response': function(response) {
        if (typeof response.data === 'string') {
          if (response.data.indexOf instanceof Function && (
            response.data.indexOf("<form class=\"form-signin\"") != -1) ||
            response.data.indexOf("<!doctype html><html") != -1) {
            $location.url("/accounts/login");
            window.location = "/accounts/login";
          }
        }
        return response;
      },
    }
  });
});

libreosteoApp.config(['growlProvider', function(growlProvider) {
    growlProvider.globalTimeToLive(5000);
    growlProvider.onlyUniqueMessages(false);
}]);

libreosteoApp.config(['$stateProvider', '$urlRouterProvider',
    function ($stateProvider, $urlRouterProvider) {
        $urlRouterProvider.otherwise('/');

        // Les trois etats du dossier patient (`patient`, `patient.examinations`,
        // `patient.examination`) sont retires par D6e T12 : le dossier est desormais un
        // document Django servi sous `/patient/<id>`, sans `#`.
        $stateProvider.
            state('dashboard',
            {
                url : '/',
                templateUrl : 'web-view/partials/dashboard',
                controller : 'DashboardCtrl'
            });
    }
]);

webshim.setOptions('forms-ext', {
    replaceUI: 'auto',
    types: 'date',
    date: {nopicker: false}
});

// WEBShim configuration
webshim.polyfill('forms forms-ext');

libreosteoApp.controller('MainController', ['$scope', 'loEditFormManager', function($scope, loEditFormManager) {
  $scope.editFormManager = loEditFormManager;
}]);

libreosteoApp.filter('htmlToPlaintext', function() {
    return function(text) {
      return  text ? String(text).replace(/<br[^>]*>/gm, ' ').replace(/<[^>]+>/gm, '') : '';
    };
  }
);

libreosteoApp.filter('mimeTypeToClass', function() {
    return function(text) {
        if (text) {
            if (text.includes('application/pdf')){
                return 'fa-file-pdf-o';
            } else if (text.includes('image/')) {
                return 'fa-file-image-o';
            }
        }
        return 'fa-file-text-o';
    }
});
