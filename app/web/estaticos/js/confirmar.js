// Confirmaciones del superadministrador: el botón de borrar solo se activa al escribir el texto exacto.
document.querySelectorAll('input[data-debe-ser]').forEach(campo => {
  const boton = campo.closest('form').querySelector('button[type=submit]');
  const esperado = campo.dataset.debeSer.trim().toLowerCase();
  campo.addEventListener('input', () => { boton.disabled = campo.value.trim().toLowerCase() !== esperado; });
});
document.querySelectorAll('[data-confirmar]').forEach(boton => {
  boton.addEventListener('click', e => { if (!confirm(boton.dataset.confirmar)) e.preventDefault(); });
});
