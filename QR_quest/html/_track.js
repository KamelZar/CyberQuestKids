/**
 * CyberQuest — Module de tracking
 * Inclure via <script src="/_track.js"></script> dans chaque page.
 * L'IP du serveur peut être surchargée AVANT l'inclusion :
 *   <script>window.CYBERQUEST_SERVER='http://192.168.0.45:8080';</script>
 */
(function () {
  'use strict';

  var SERVER      = (window.CYBERQUEST_SERVER || 'http://192.168.0.45:8080').replace(/\/$/, '');
  var COOKIE_NAME = 'cqid';

  /* ── Cookie helpers ──────────────────────────────────────── */
  function getTeamId() {
    var m = document.cookie.match(/(?:^|;\s*)cqid=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : null;
  }

  function setTeamId(id) {
    var safe = encodeURIComponent(String(id).trim().slice(0, 16));
    document.cookie = COOKIE_NAME + '=' + safe +
      '; path=/; max-age=86400; SameSite=Lax';
  }

  /* ── Fire-and-forget tracking pixel ─────────────────────── */
  function track(exo, status) {
    var id = getTeamId();
    if (!id) return; // pas d'équipe = pas de tracking
    var url = SERVER
      + '/cyberquest/' + encodeURIComponent(id)
      + '/'           + encodeURIComponent(exo)
      + '/'           + encodeURIComponent(status);
    // Image() : aucun CORS, aucun JS bloquant
    new Image().src = url;
  }

  /* ── Auto-track "view" au chargement ────────────────────── */
  function autoTrack(exo) {
    function fire() { track(exo, 'view'); }
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fire);
    } else {
      fire();
    }
  }

  /* ── Afficher l'ID équipe dans les éléments .cq-team-id ─── */
  function injectTeamBadge() {
    var id = getTeamId();
    if (!id) return;
    var els = document.querySelectorAll('.cq-team-id');
    for (var i = 0; i < els.length; i++) { els[i].textContent = id; }
  }

  /* ── API publique ────────────────────────────────────────── */
  window.CyberTrack = {
    track:           track,
    getTeamId:       getTeamId,
    setTeamId:       setTeamId,
    autoTrack:       autoTrack,
    injectTeamBadge: injectTeamBadge
  };

})();
