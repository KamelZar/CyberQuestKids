/**
 * CyberQuest — Module de tracking
 * Inclure via <script src="/_track.js"></script> dans chaque page.
 */
(function () {
  'use strict';

  // Chemin relatif — fonctionne peu importe l'IP du serveur
  var SERVER = window.location.origin;

  /* ── Cookie helpers ──────────────────────────────────────── */
  function getCookie(name) {
    var m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? decodeURIComponent(m[2]) : null;
  }

  function getTeamId() {
    // cq_team posé par team-select.html (nom d'équipe : snowden, hopper, ...)
    return getCookie('cq_team');
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

  /* ── Score une activité une seule fois (sessionStorage) ─── */
  function scoreOnce(activity, points) {
    var key = 'cq_scored_' + activity;
    try { if (sessionStorage.getItem(key)) return; } catch(e) {}
    var id = getTeamId();
    if (!id) return;
    try { sessionStorage.setItem(key, '1'); } catch(e) {}
    fetch(SERVER + '/workshop/score', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ team_id: id, activity: activity, points: points })
    }).catch(function() {});
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
    autoTrack:       autoTrack,
    scoreOnce:       scoreOnce,
    injectTeamBadge: injectTeamBadge
  };

})();
