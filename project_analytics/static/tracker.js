(function () {
  'use strict';

  var project = window.PROJECT_ANALYTICS_PROJECT;
  if (!project) {
    console.warn('PROJECT_ANALYTICS_PROJECT is missing.');
    return;
  }

  var endpoint = window.PROJECT_ANALYTICS_ENDPOINT || 'https://YOUR-ANALYTICS-DOMAIN/log';
  var key = 'project_analytics_client_id_' + project;
  var clientId = localStorage.getItem(key);

  if (!clientId) {
    clientId = (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random().toString(16).slice(2));
    localStorage.setItem(key, clientId);
  }

  var payload = {
    project: project,
    client_id: clientId,
    path: location.pathname + location.search,
    referrer: document.referrer || ''
  };

  try {
    var body = JSON.stringify(payload);
    if (navigator.sendBeacon) {
      navigator.sendBeacon(endpoint, new Blob([body], { type: 'application/json' }));
    } else {
      fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body,
        keepalive: true,
        mode: 'cors'
      }).catch(function () {});
    }
  } catch (_) {}
})();
