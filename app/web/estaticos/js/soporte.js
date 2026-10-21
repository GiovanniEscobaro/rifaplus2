// Chat de soporte del panel: preguntas frecuentes con respuesta automática y conversación con RifaPlus.
(function () {
  const raiz = document.getElementById('chat-soporte');
  if (!raiz) return;
  const boton = raiz.querySelector('.chat-boton');
  const ventana = raiz.querySelector('.chat-ventana');
  const lista = raiz.querySelector('.chat-mensajes');
  const sugerencias = raiz.querySelector('.chat-sugerencias');
  const formulario = raiz.querySelector('form');
  const campo = formulario.querySelector('textarea');
  const aviso = raiz.querySelector('.chat-aviso');
  const NOMBRES = {organizador: 'Usted', asistente: 'Asistente', rifaplus: 'RifaPlus'};
  let ultimoId = 0, abierto = false;

  function pintar(datos) {
    aviso.hidden = !(datos.sin_leer && !abierto);
    const nuevos = datos.mensajes.filter(m => m.id > ultimoId);
    for (const m of nuevos) {
      const div = document.createElement('div');
      div.className = 'chat-msg ' + m.autor;
      const quien = document.createElement('span');
      quien.className = 'chat-quien';
      quien.textContent = NOMBRES[m.autor] || m.autor;
      const texto = document.createElement('p');
      texto.textContent = m.texto;  // textContent: nunca se interpreta como HTML
      div.append(quien, texto);
      lista.appendChild(div);
      ultimoId = m.id;
    }
    if (nuevos.length) lista.scrollTop = lista.scrollHeight;
    if (!sugerencias.children.length) {
      for (const p of datos.preguntas) {
        const b = document.createElement('button');
        b.type = 'button'; b.className = 'chat-sugerencia'; b.textContent = p.titulo; b.dataset.clave = p.clave;
        sugerencias.appendChild(b);
      }
      const persona = document.createElement('button');
      persona.type = 'button'; persona.className = 'chat-sugerencia persona'; persona.textContent = 'Hablar con una persona';
      persona.dataset.persona = '1';
      sugerencias.appendChild(persona);
    }
  }

  async function cargar() {
    try { const r = await fetch('/panel/soporte', {headers: {Accept: 'application/json'}}); if (r.ok) pintar(await r.json()); }
    catch (e) { /* sin conexión: se reintenta en la próxima consulta */ }
  }

  async function enviar(datos) {
    const r = await fetch('/panel/soporte', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(datos)});
    const respuesta = await r.json();
    if (r.ok) pintar(respuesta); else alert(respuesta.error || 'No se pudo enviar el mensaje.');
  }

  boton.addEventListener('click', () => {
    abierto = !abierto;
    ventana.hidden = !abierto;
    boton.setAttribute('aria-expanded', String(abierto));
    if (abierto) { aviso.hidden = true; cargar(); campo.focus(); }
  });
  raiz.querySelector('.chat-cerrar').addEventListener('click', () => boton.click());
  sugerencias.addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    enviar(b.dataset.persona ? {persona: true} : {pregunta: b.dataset.clave});
  });
  formulario.addEventListener('submit', e => {
    e.preventDefault();
    const texto = campo.value.trim(); if (!texto) return;
    campo.value = ''; enviar({texto});
  });
  campo.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); formulario.requestSubmit(); } });

  cargar();
  setInterval(cargar, 15000);  // revisa respuestas nuevas de RifaPlus cada 15 segundos
})();
