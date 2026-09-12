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
var invoices = angular.module('loInvoice', ['ngResource', 'loUser', 'loOfficeSettings']);

invoices.factory('InvoiceService', ['$resource', function ($resource) {
  "use strict";
  return $resource('api/invoices/:invoiceId', null, {
    query: { method: 'GET', isArray: true },
    get: { method: 'GET', params: { invoiceId: 'invoiceId' } },
    cancel: {
      method: 'POST',
      params: { invoiceId: 'invoiceId' },
      url: 'api/invoices/:invoiceId/cancel'
    },
    send: {
      method: 'POST',
      params: { invoiceId: 'invoiceId' },
      url: 'api/invoices/:invoiceId/send'
    }
  });
}]);


var InvoiceSendCtrl = function ($scope, $uibModalInstance, message, email) {
  $scope.message = message;
  $scope.email = email;

  $scope.ok = function () {
    $uibModalInstance.close($scope.email);
  };

  $scope.cancel = function () {
    $uibModalInstance.dismiss('cancel');
  };

  $scope.validateEmail = function (email) {
    const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return pattern.test(email);
  }
}

