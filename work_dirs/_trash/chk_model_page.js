(() => {
  const h1 = document.querySelector('h1');
  const buy = document.querySelector('.emd-btn--buy');
  const spec = document.querySelector('.emd-btn--spec');
  const rows = document.querySelectorAll('.emd-card table tr').length;
  const fm = document.querySelectorAll('.emd-fm li').length;
  const rel = document.querySelectorAll('.emd-rel li').length;
  const ld = document.querySelectorAll('script[type="application/ld+json"]').length;
  const details = document.querySelectorAll('.emd-faq').length;
  return JSON.stringify({
    title: document.title.slice(0, 90),
    h1: h1 && h1.textContent.slice(0, 60),
    buy: buy && buy.href.slice(0, 70),
    specBtn: !!spec,
    specRows: rows,
    fmItems: fm,
    related: rel,
    ldJson: ld,
    faqs: details
  });
})()
