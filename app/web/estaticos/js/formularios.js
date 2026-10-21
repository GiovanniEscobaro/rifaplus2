// Ayudas de formularios para todo RifaPlus:
// 1) Campos de dinero (.campo-pesos) con puntos de miles mientras se escribe: 100000 -> 100.000
// 2) Validación inmediata (data-validar) al salir de cada campo, y bloqueo del envío si algo está mal.
(function () {
  // ---------- Dinero ----------
  const soloDigitos = v => String(v || '').replace(/\D/g, '');
  const conPuntos = v => { const d = soloDigitos(v); return d ? Number(d).toLocaleString('es-CO') : ''; };
  window.leerPesos = el => Number(soloDigitos(el && el.value)) || 0;

  function formatear(campo) {
    const antes = campo.value;
    const nuevo = conPuntos(antes);
    if (nuevo === antes) return;
    const digitosAntesDelCursor = soloDigitos(antes.slice(0, campo.selectionStart || antes.length)).length;
    campo.value = nuevo;
    let pos = 0, vistos = 0;  // deja el cursor después del mismo dígito
    while (pos < nuevo.length && vistos < digitosAntesDelCursor) { if (/\d/.test(nuevo[pos])) vistos++; pos++; }
    if (document.activeElement === campo) campo.setSelectionRange(pos, pos);
  }
  document.addEventListener('input', e => { if (e.target.matches('.campo-pesos')) formatear(e.target); });
  document.querySelectorAll('.campo-pesos').forEach(formatear);

  // ---------- Validación inmediata ----------
  const reglas = {
    requerido: v => v.trim() ? '' : 'Este dato es obligatorio.',
    nombre: v => v.trim().split(/\s+/).filter(Boolean).length >= 2 && v.trim().length >= 5 ? '' : 'Escriba nombre y apellido.',
    texto: v => v.trim().length >= 3 ? '' : 'Escriba al menos 3 caracteres.',
    celular: v => {
      const d = soloDigitos(v);
      if (/^3\d{9}$/.test(d) || /^573\d{9}$/.test(d)) return '';
      if (v.trim().startsWith('+') && d.length >= 10 && d.length <= 15) return '';
      return 'Escriba un celular válido de 10 dígitos que empiece por 3, por ejemplo 300 123 4567.';
    },
    email: v => /^[^\s@]+@[^\s@]+\.[a-z]{2,}$/i.test(v.trim()) ? '' : 'Escriba un correo válido, por ejemplo nombre@correo.com.',
    documento: v => /^[0-9A-Za-z]{5,20}$/.test(v.replace(/[\s.\-]/g, '')) ? '' : 'Escriba el número de documento completo, sin puntos.',
    direccion: v => v.trim().length >= 5 ? '' : 'Escriba la dirección completa.',
    pesos: v => soloDigitos(v) && Number(soloDigitos(v)) > 0 ? '' : 'Escriba un valor mayor que cero.',
    seleccion: v => v ? '' : 'Escoja una opción.',
  };

  function mensajeDe(campo) {
    if (campo.disabled || campo.readOnly && !campo.value) return '';
    const v = campo.value || '';
    const tipos = (campo.dataset.validar || '').split(' ').filter(Boolean);
    const opcional = !tipos.includes('requerido') && !tipos.includes('seleccion');
    if (opcional && !v.trim()) return '';
    for (const tipo of tipos) { const m = reglas[tipo] ? reglas[tipo](v) : ''; if (m) return m; }
    return '';
  }

  function mostrar(campo, mensaje) {
    const contenedor = campo.closest('.campo') || campo.parentElement;
    let caja = contenedor.querySelector('.error-campo');
    if (!caja) {
      caja = document.createElement('span');
      caja.className = 'error-campo';
      caja.id = (campo.id || campo.name) + '-error';
      caja.setAttribute('aria-live', 'polite');
      contenedor.appendChild(caja);
      campo.setAttribute('aria-describedby', ((campo.getAttribute('aria-describedby') || '') + ' ' + caja.id).trim());
    }
    caja.textContent = mensaje;
    campo.classList.toggle('invalido', !!mensaje);
    campo.classList.toggle('valido', !mensaje && !!campo.value);
    campo.setAttribute('aria-invalid', mensaje ? 'true' : 'false');
  }

  const validar = campo => { const m = mensajeDe(campo); mostrar(campo, m); return !m; };

  document.addEventListener('focusout', e => { if (e.target.matches('[data-validar]')) validar(e.target); });
  document.addEventListener('input', e => {  // si ya estaba en rojo, se corrige mientras escribe
    if (e.target.matches('[data-validar].invalido')) validar(e.target);
  });
  document.addEventListener('change', e => { if (e.target.matches('select[data-validar]')) validar(e.target); });

  document.addEventListener('submit', e => {
    const form = e.target;
    const campos = [...form.querySelectorAll('[data-validar]')];
    const malos = campos.filter(c => !validar(c));
    if (malos.length) { e.preventDefault(); malos[0].focus(); return; }
    // Antes de enviar, el dinero va sin puntos
    form.querySelectorAll('.campo-pesos').forEach(c => { c.value = soloDigitos(c.value); });
  }, true);
})();
