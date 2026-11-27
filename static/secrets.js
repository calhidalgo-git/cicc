// Revela un dato protegido al pulsar su botón. Cada consulta queda registrada en la auditoría.
(function () {
  function csrf() {
    var match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }
  document.addEventListener('click', function (event) {
    var button = event.target.closest('button.secret-chip[data-secret-url]');
    if (!button) return;
    button.disabled = true;
    fetch(button.dataset.secretUrl, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrf() },
      credentials: 'same-origin'
    })
      .then(function (r) { return r.json().then(function (d) { return [r.ok, d]; }); })
      .then(function (res) {
        var code = document.createElement('code');
        code.className = 'secret-value';
        code.textContent = res[0] ? res[1].value : (res[1].error || 'No disponible');
        button.replaceWith(code);
      })
      .catch(function () { button.disabled = false; });
  });
})();
