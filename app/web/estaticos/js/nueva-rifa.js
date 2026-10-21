// Formulario de nueva rifa: resumen de lo que se recauda, plan de cuotas (filas, sugerencias y suma)
// y premios secos (agregar y quitar filas). Lo general (puntos de miles, validación) está en formularios.js.
const caja = document.getElementById('resumen');
const precio = document.getElementById('valor_boleta');
const pesos = v => '$' + Number(v).toLocaleString('es-CO');
const valorDe = el => (window.leerPesos ? window.leerPesos(el) : Number(el.value)) || 0;

function precioEscogido(opcion) {
  // Precio del tipo de rifa por la duración escogida (6 meses, 1 año…)
  const duracion = document.querySelector('input[name="duracion_id"]:checked');
  const precios = opcion ? JSON.parse(opcion.dataset.precios || '{}') : {};
  return duracion && precios[duracion.value] !== undefined ? Number(precios[duracion.value]) : null;
}

function fechaFin(meses) {
  const d = new Date(); d.setMonth(d.getMonth() + Number(meses));
  return d.toLocaleDateString('es-CO', {day: 'numeric', month: 'long', year: 'numeric'});
}

function sumarMeses(fecha, meses) {
  const d = new Date(fecha); d.setMonth(d.getMonth() + meses); return d;
}

function mesesHastaSorteo() {
  // Meses desde hoy (cuando se publicaría) hasta la fecha del sorteo, contando el mes empezado
  const valor = document.getElementById('fecha_sorteo').value;
  if (!valor) return null;
  const sorteo = new Date(valor + 'T12:00'), hoy = new Date();
  let meses = 0;
  while (sumarMeses(hoy, meses) < sorteo && meses < 120) meses++;
  return Math.max(meses, 1);
}

function costosPorDuracion(opcion) {
  // Para cada duración: cuántos períodos se necesitan para llegar al sorteo y cuánto cuesta en total
  const precios = opcion ? JSON.parse(opcion.dataset.precios || '{}') : {};
  const meses = mesesHastaSorteo();
  return [...document.querySelectorAll('input[name="duracion_id"]')].map(r => {
    const precioPeriodo = precios[r.value] === undefined ? null : Number(precios[r.value]);
    const periodos = meses ? Math.max(1, Math.ceil(meses / Number(r.dataset.meses))) : 1;
    return {radio: r, nombre: r.dataset.nombre, mesesPeriodo: Number(r.dataset.meses), precioPeriodo, periodos,
            total: precioPeriodo === null ? null : precioPeriodo * periodos};
  });
}

function valorPremios() {
  // Premio mayor + premios secos (valores estimados que escribió el organizador)
  let total = valorDe(document.getElementById('valor_premio'));
  document.querySelectorAll('[name^="seco_valor_estimado_"]').forEach(el => { total += valorDe(el); });
  return total;
}

function actualizar() {
  const opcion = document.querySelector('input[name="opcion"]:checked');
  document.querySelectorAll('.tarjeta-opcion').forEach(t => t.classList.toggle('seleccionada', t.contains(opcion)));
  const meses = mesesHastaSorteo();
  const costos = costosPorDuracion(opcion);
  const validos = costos.filter(c => c.total !== null);
  const mejor = validos.length ? validos.reduce((a, b) => (b.total < a.total ? b : a)) : null;

  // Precio y nota de cada duración: si cubre hasta el sorteo o cuántas renovaciones necesitaría
  costos.forEach(c => {
    const el = document.querySelector(`.precio-duracion[data-duracion="${c.radio.value}"]`);
    if (!el) return;
    if (c.precioPeriodo === null) { el.textContent = ''; return; }
    let texto = c.precioPeriodo === 0 ? '· Gratis' : '· ' + pesos(c.precioPeriodo);
    if (meses) texto += c.periodos === 1 ? ' · cubre hasta el sorteo'
      : ` · necesita ${c.periodos - 1} renovación${c.periodos > 2 ? 'es' : ''}: total ${pesos(c.total)}`;
    if (mejor && c === mejor && validos.length > 1 && opcion) texto += ' · ★ le conviene';
    el.textContent = texto;
  });

  const valor = valorDe(precio);
  const escogida = costos.find(c => c.radio.checked);
  if (!opcion || !valor || !escogida || escogida.precioPeriodo === null) { caja.hidden = true; return; }
  const boletas = Number(opcion.dataset.boletas);
  const recaudo = boletas * valor;
  const premios = valorPremios();
  const costoRifaplus = escogida.total;
  const ganancia = recaudo - premios - costoRifaplus;
  let aviso = '';
  if (meses && escogida.periodos > 1) {
    aviso = `<p class="aviso-duracion">Su sorteo es en unos <b>${meses} meses</b>. Con ${escogida.nombre.toLowerCase()} deberá renovar ${escogida.periodos - 1} vez${escogida.periodos > 2 ? 'es' : ''} (total ${pesos(escogida.total)}).` +
      (mejor && mejor !== escogida ? ` Con <b>${mejor.nombre.toLowerCase()}</b> pagaría ${pesos(mejor.total)}.` : '') + ' Usted decide.</p>';
  }
  caja.hidden = false;
  caja.innerHTML = aviso + `<table class="cuentas-rifa">
      <tr><td>Si vende las ${boletas.toLocaleString('es-CO')} boletas a ${pesos(valor)}</td><td>${pesos(recaudo)}</td></tr>
      <tr><td>− Premios (mayor y secos, valor estimado)</td><td>${premios ? '− ' + pesos(premios) : '—'}</td></tr>
      <tr><td>− RifaPlus (${escogida.nombre.toLowerCase()}${escogida.periodos > 1 ? ' × ' + escogida.periodos : ''})</td><td>${costoRifaplus ? '− ' + pesos(costoRifaplus) : 'Gratis'}</td></tr>
      <tr class="total ${ganancia < 0 ? 'negativo' : ''}"><td>Ganancia estimada del organizador</td><td>${pesos(ganancia)}</td></tr>
    </table>
    <p class="ayuda" style="margin:.4rem 0 0">Antes de comisiones de vendedores. ${ganancia < 0 ? '<b>Ojo: con estos valores la rifa da pérdida.</b>' : ''}</p>`;
}
document.getElementById('fecha_sorteo').addEventListener('change', actualizar);
document.addEventListener('input', e => { if (e.target.matches('#valor_premio, [name^="seco_valor_estimado_"]')) actualizar(); });
document.querySelectorAll('input[name="opcion"], input[name="duracion_id"]').forEach(r => r.addEventListener('change', actualizar));
precio.addEventListener('input', actualizar);
actualizar();

// ---------- Plan de cuotas ----------
const numCuotas = document.getElementById('num_cuotas');
const filasCuotas = document.getElementById('filas-cuotas');
const sumaCuotas = document.getElementById('suma-cuotas');
const fechaSorteo = document.getElementById('fecha_sorteo');
let cuotasEditadas = [...filasCuotas.querySelectorAll('input')].some(i => i.value);

const iso = d => d.toISOString().slice(0, 10);

function fechasSugeridas(n) {
  // Reparte las fechas entre la próxima semana y el día del sorteo
  const fin = fechaSorteo.value ? new Date(fechaSorteo.value + 'T12:00') : null;
  const inicio = new Date(); inicio.setDate(inicio.getDate() + 7);
  if (!fin || fin <= inicio) return Array(n).fill(fechaSorteo.value || '');
  const paso = (fin - inicio) / Math.max(n - 1, 1);
  return Array.from({length: n}, (_, i) => iso(new Date(n === 1 ? fin : inicio.getTime() + paso * i)));
}

function construirCuotas() {
  const n = Number(numCuotas.value);
  const valor = valorDe(precio);
  const base = Math.floor(valor / n);
  const fechas = fechasSugeridas(n);
  filasCuotas.innerHTML = '';
  for (let i = 1; i <= n; i++) {
    const v = valor ? (i === n ? valor - base * (n - 1) : base).toLocaleString('es-CO') : '';
    filasCuotas.insertAdjacentHTML('beforeend', `<tr><td>${i}</td>
      <td><input type="text" inputmode="numeric" class="campo-pesos" data-validar="requerido pesos" name="cuota_valor_${i}" value="${v}" aria-label="Valor de la cuota ${i}"></td>
      <td><input type="date" data-validar="requerido" name="cuota_fecha_${i}" value="${fechas[i - 1]}" aria-label="Fecha límite de la cuota ${i}"></td></tr>`);
  }
  cuotasEditadas = false;
  revisarSuma();
}

function revisarSuma() {
  const total = [...filasCuotas.querySelectorAll('.campo-pesos')].reduce((s, i) => s + valorDe(i), 0);
  const valor = valorDe(precio);
  if (!valor) { sumaCuotas.textContent = ''; return; }
  sumaCuotas.textContent = total === valor
    ? `Las cuotas suman ${pesos(total)}: correcto.`
    : `Las cuotas suman ${pesos(total)} y la boleta vale ${pesos(valor)}. Deben ser iguales.`;
  sumaCuotas.style.color = total === valor ? 'var(--ok)' : 'var(--error)';
}

numCuotas.addEventListener('change', construirCuotas);
precio.addEventListener('input', () => { if (!cuotasEditadas) construirCuotas(); else revisarSuma(); });
fechaSorteo.addEventListener('change', () => { if (!cuotasEditadas) construirCuotas(); });
filasCuotas.addEventListener('input', () => { cuotasEditadas = true; revisarSuma(); });
if (!cuotasEditadas) construirCuotas(); else revisarSuma();

// ---------- Premios secos ----------
const filasSecos = document.getElementById('filas-secos');
const plantillaSeco = document.getElementById('plantilla-seco');
function renumerarSecos() {
  filasSecos.querySelectorAll('.fila-seco').forEach((fila, i) => {
    fila.querySelectorAll('[name]').forEach(el => { el.name = el.name.replace(/_(\d+|N)$/, '_' + (i + 1)); });
  });
}
document.getElementById('agregar-seco').addEventListener('click', () => {
  if (filasSecos.children.length >= 24) return;
  filasSecos.appendChild(plantillaSeco.content.cloneNode(true));
  renumerarSecos();
  filasSecos.lastElementChild.querySelector('input').focus();
});
filasSecos.addEventListener('click', e => {
  if (e.target.classList.contains('quitar-seco')) { e.target.closest('.fila-seco').remove(); renumerarSecos(); }
});

// ---------- Fotos de premios: miniatura al escoger, "Quitar foto" ----------
const formulario = document.querySelector('form[enctype="multipart/form-data"]');
const urlFoto = fila => {
  const archivo = fila.querySelector('input[type=file]');
  if (archivo && archivo.files && archivo.files[0]) return URL.createObjectURL(archivo.files[0]);
  const actual = fila.querySelector('input[type=hidden][name$="_actual"], input[type=hidden][name^="seco_foto_actual"]');
  return actual && actual.value ? '/archivos/' + actual.value : '';
};
formulario.addEventListener('change', e => {
  if (e.target.type !== 'file') return;
  const fila = e.target.closest('.foto-fila');
  const img = fila.querySelector('img.miniatura');
  const url = urlFoto(fila);
  if (img && url) { img.src = url; img.hidden = false; }
});
formulario.addEventListener('click', e => {
  if (!e.target.classList.contains('quitar-foto')) return;
  const fila = e.target.closest('.foto-fila');
  fila.querySelector('input[type=hidden]').value = '';
  fila.querySelector('input[type=file]').value = '';
  fila.querySelector('img.miniatura').hidden = true;
  e.target.remove();
  actualizarPrevia();
});

// ---------- Vista previa de la boleta ----------
const previa = sel => document.querySelector(`[data-previa="${sel}"]`);
const fechaLarga = iso => iso ? new Date(iso + 'T12:00').toLocaleDateString('es-CO', {day: 'numeric', month: 'long', year: 'numeric'}) : '';
const fechaCorta = iso => iso ? new Date(iso + 'T12:00').toLocaleDateString('es-CO') : '';
const texto = (id, porDefecto) => (document.getElementById(id)?.value || '').trim() || porDefecto;

function actualizarPrevia() {
  previa('nombre').textContent = texto('nombre', 'Nombre de la rifa');
  previa('premio').textContent = texto('premio_mayor', 'Premio mayor');
  const loteria = document.getElementById('loteria_id');
  const nombreLoteria = loteria ? loteria.options[loteria.selectedIndex].text.replace(/\s*\(.*\)$/, '') : 'lotería';
  const valorPremio = valorDe(document.getElementById('valor_premio'));
  const fecha = document.getElementById('fecha_sorteo').value;
  previa('detalle-mayor').textContent = (valorPremio ? `Avaluado en ${pesos(valorPremio)} · ` : '') +
    `Juega con la ${nombreLoteria}` + (fecha ? ` el ${fechaLarga(fecha)}` : '');
  const fotoMayor = urlFoto(document.getElementById('foto_mayor').closest('.foto-fila'));
  previa('foto-mayor').hidden = !fotoMayor;
  if (fotoMayor) previa('foto-mayor').src = fotoMayor;

  // Números de ejemplo según la opción escogida (cifras-números por boleta)
  const opcion = document.querySelector('input[name="opcion"]:checked');
  const [cifras, cantidad] = opcion ? opcion.value.split('-').map(Number) : [2, 1];
  const etiqueta = cantidad === 1 ? '7'.padStart(cifras, '0') : '1';
  previa('etiqueta').textContent = previa('etiqueta2').textContent = etiqueta;
  previa('numeros').innerHTML = cantidad === 1 ? `<span>${etiqueta}</span>`
    : Array.from({length: cantidad}, () => `<span>${'#'.repeat(cifras)}</span>`).join('');

  // Valor y cuotas
  previa('valor').textContent = `Valor ${pesos(valorDe(precio))}`;
  const cuotas = [...filasCuotas.querySelectorAll('tr')];
  previa('cuotas').innerHTML = cuotas.length > 1 ? cuotas.map((fila, i) => {
    const [v, f] = fila.querySelectorAll('input');
    return `<tr><td>○ Cuota ${i + 1}</td><td>${pesos(valorDe(v))}</td><td>${fechaCorta(f.value)}</td></tr>`;
  }).join('') : '';

  // Premios secos
  const secos = [...filasSecos.querySelectorAll('.fila-seco')].map(fila => {
    const nombre = fila.querySelector('[name^="seco_descripcion"]').value.trim();
    if (!nombre) return '';
    const sel = fila.querySelector('select');
    const valor = valorDe(fila.querySelector('[name^="seco_valor_estimado"]'));
    const f = fila.querySelector('[name^="seco_fecha_juego"]').value;
    const foto = urlFoto(fila.querySelector('.foto-fila'));
    return `<li>${foto ? `<img class="bi-foto-seco" src="${foto}" alt="">` : ''}<div><b>${nombre.replace(/</g, '&lt;')}</b>` +
      `${valor ? ' · ' + pesos(valor) : ''}<span>${sel.options[sel.selectedIndex].text} · ${fechaLarga(f)}</span></div></li>`;
  }).filter(Boolean);
  previa('secos').innerHTML = secos.join('');
  previa('bloque-secos').hidden = secos.length === 0;
}
let esperaPrevia;
formulario.addEventListener('input', () => { clearTimeout(esperaPrevia); esperaPrevia = setTimeout(actualizarPrevia, 150); });
formulario.addEventListener('change', () => { clearTimeout(esperaPrevia); esperaPrevia = setTimeout(actualizarPrevia, 50); });
formulario.addEventListener('click', e => { if (e.target.closest('#agregar-seco, .quitar-seco')) setTimeout(actualizarPrevia, 50); });
actualizarPrevia();
