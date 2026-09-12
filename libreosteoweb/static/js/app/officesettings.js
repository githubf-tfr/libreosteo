
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
var officesettings = angular.module('loOfficeSettings', ['ngResource']);

officesettings.factory('OfficeSettingsServ', ['$resource',
  function ($resource) {
    "use strict";
    return $resource('api/settings/:settingsId', null, {
      get : {method: 'GET', isArray : true},
      save : {method : 'PUT'},
    });
  }
]);

officesettings.factory('OfficePaimentMeansServ', ['$resource',
  function($resource) {
    return $resource('api/paiment-mean/:paimentMeanId', null, {
      get : {method :  'GET', params: {paimentMeanId : 'paimentMeanId'}},
      save : {method : 'PUT', params: {paimentMeanId: 'paimentMeanId'}},
      add : {method: 'POST'},
      query : {method: 'GET', isArray: true}
      });
}]);
