// Formulario de registro: WhatsApp igual al celular y marca de la opción persona natural/jurídica.
const mismo = document.getElementById('mismo_numero'), wa = document.getElementById('whatsapp'), cel = document.getElementById('celular');
function sincronizar(){ wa.disabled = mismo.checked; if (mismo.checked) wa.value = cel.value; }
mismo.addEventListener('change', sincronizar); cel.addEventListener('input', sincronizar); sincronizar();

// Marca la opción escogida (persona natural o jurídica) también en navegadores sin soporte de :has
const opciones = document.querySelectorAll('.opcion input[type=radio]');
function marcar() { opciones.forEach(r => r.closest('.opcion').classList.toggle('seleccionada', r.checked)); }
opciones.forEach(r => r.addEventListener('change', marcar)); marcar();
