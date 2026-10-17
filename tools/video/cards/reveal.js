// Elements with data-in="n" appear at step n; data-out="n" fade away at step n.
function show(step) {
  document.querySelectorAll('[data-in]').forEach((el, i) => {
    const on = step >= Number(el.dataset.in) && !(el.dataset.out && step >= Number(el.dataset.out))
    el.style.transitionDelay = on ? `${Number(el.dataset.delay || 0)}ms` : '0ms'
    el.style.opacity = on ? '1' : '0'
    el.style.transform = on ? 'none' : ''
  })
}
new MutationObserver(() => show(Number(document.body.dataset.step || -1))).observe(document.body, { attributes: true })
window.addEventListener('load', () => show(Number(document.body.dataset.step || -1)))
