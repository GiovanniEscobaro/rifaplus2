// Botón con "ojito" para mostrar u ocultar la clave en todos los campos de contraseña.
(function () {
  const ojoAbierto = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>';
  const ojoCerrado = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 3l18 18"/><path d="M10.6 5.1A10.6 10.6 0 0 1 12 5c6.4 0 10 7 10 7a17.6 17.6 0 0 1-3.2 4.2M6.6 6.6A17.4 17.4 0 0 0 2 12s3.6 7 10 7a9.7 9.7 0 0 0 5.4-1.6"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/></svg>';

  document.querySelectorAll('input[type="password"]').forEach(function (campo) {
    const envoltura = document.createElement('div');
    envoltura.className = 'campo-clave';
    campo.parentNode.insertBefore(envoltura, campo);
    envoltura.appendChild(campo);

    const boton = document.createElement('button');
    boton.type = 'button';
    boton.className = 'ver-clave';
    boton.setAttribute('aria-label', 'Mostrar la clave');
    boton.setAttribute('aria-pressed', 'false');
    boton.innerHTML = ojoAbierto;
    envoltura.appendChild(boton);

    boton.addEventListener('click', function () {
      const visible = campo.type === 'password';
      campo.type = visible ? 'text' : 'password';
      boton.innerHTML = visible ? ojoCerrado : ojoAbierto;
      boton.setAttribute('aria-pressed', String(visible));
      boton.setAttribute('aria-label', visible ? 'Ocultar la clave' : 'Mostrar la clave');
      campo.focus();
    });
  });
})();
