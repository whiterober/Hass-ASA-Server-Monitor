(function(){
  const DARK_LUM = 128;
  function apply(){
    var b = getComputedStyle(document.documentElement).getPropertyValue('--primary-background-color').trim();
    var m = b.match(/\d+/g);
    if (m) {
      var lum = 0.299 * m[0] + 0.587 * m[1] + 0.114 * m[2];
      document.documentElement.setAttribute('data-theme', lum < DARK_LUM ? 'dark' : 'light');
    }
  }
  apply();
  // Watch for theme changes (HA updates CSS vars on theme switch)
  new MutationObserver(apply).observe(document.documentElement, {attributes:true,attributeFilter:['style','class']});
  // Also re-check on HA connection state change
  window.addEventListener('locationchange', apply);
  setInterval(apply, 2000); // fallback polling
})();
