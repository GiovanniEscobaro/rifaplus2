// Menú para celulares: el botón «☰ Menú» abre y cierra el menú del panel, del superadministrador o de la cabecera.
document.querySelectorAll('.boton-menu').forEach(boton => {
  const contenedor = boton.closest('.lateral, .cabecera');
  if (!contenedor) return;
  const cerrar = () => { contenedor.classList.remove('menu-abierto'); boton.setAttribute('aria-expanded', 'false'); boton.textContent = '☰ Menú'; };
  boton.addEventListener('click', () => {
    const abierto = contenedor.classList.toggle('menu-abierto');
    boton.setAttribute('aria-expanded', String(abierto));
    boton.textContent = abierto ? '✕ Cerrar' : '☰ Menú';
  });
  contenedor.querySelectorAll('nav a').forEach(a => a.addEventListener('click', cerrar));
  document.addEventListener('keydown', e => { if (e.key === 'Escape') cerrar(); });
});
