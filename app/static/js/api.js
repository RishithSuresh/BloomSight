/* Tiny JSON API client for the BloomSight Herbarium backend. */

window.BS = window.BS || {};

BS.api = (function () {
  function fileToDataURL(file) {
    return new Promise(function (resolve, reject) {
      const fr = new FileReader();
      fr.onload  = function () { resolve(fr.result); };
      fr.onerror = function () { reject(fr.error);  };
      fr.readAsDataURL(file);
    });
  }

  async function postJSON(url, payload) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    let body;
    try { body = await res.json(); }
    catch (e) { throw new Error("invalid response from server"); }
    if (!res.ok) throw new Error(body.error || ("HTTP " + res.status));
    return body;
  }

  function encrypt(opts)  { return postJSON("/api/encrypt", opts); }
  function decrypt(opts)  { return postJSON("/api/decrypt", opts); }

  function loadImage(src) {
    return new Promise(function (resolve, reject) {
      const img = new Image();
      img.onload  = function () { resolve(img); };
      img.onerror = reject;
      img.src = src;
    });
  }

  return { fileToDataURL, encrypt, decrypt, loadImage };
})();
