// Formulario de venta: WhatsApp igual al celular y búsqueda del comprador por documento.
const mismo = document.getElementById('mismo_numero');
const celular = document.getElementById('celular');
const whatsapp = document.getElementById('whatsapp');
function sincronizar() { whatsapp.readOnly = mismo.checked; if (mismo.checked) whatsapp.value = celular.value; }
mismo.addEventListener('change', sincronizar);
celular.addEventListener('input', sincronizar);
sincronizar();

const documento = document.getElementById('numero_documento');
const aviso = document.getElementById('aviso-comprador');
documento.addEventListener('change', async () => {
  if (documento.value.trim().length < 3) return;
  const r = await fetch(`/panel/compradores/buscar?documento=${encodeURIComponent(documento.value)}`);
  const d = await r.json();
  if (!d.encontrado) { aviso.textContent = ''; return; }
  for (const campo of ['tipo_documento', 'nombre', 'celular', 'whatsapp', 'email', 'direccion', 'ciudad']) {
    const el = document.getElementById(campo);
    if (el && !el.value) el.value = d[campo];
  }
  mismo.checked = d.celular === d.whatsapp;
  document.getElementById('acepta_whatsapp').checked = d.acepta_whatsapp;
  sincronizar();
  aviso.textContent = 'Comprador conocido: completamos sus datos. Revíselos antes de vender.';
});
