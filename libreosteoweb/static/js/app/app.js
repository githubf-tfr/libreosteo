
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
    'ui.bootstrap',
    'loDashboard',
    'loOfficeEvent',
    'yaru22.angular-timeago',
    'ngAnimate',
    'duScroll',
    'loUser',
    'angular-growl',
    'angular-loading-bar',
    'ui.router',
    'angular-toArrayFilter',
    'loOfficeSettings',
    'infinite-scroll'
]);

libreosteoApp.config(function ($interpolateProvider) {
  $interpolateProvider.startSymbol('{$');
  $interpolateProvider.endSymbol('$}');
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
