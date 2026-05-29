/**
 * CyberQuest — Module phishing pédagogique
 * Injecter avant </body> avec data-source="roblox|instagram|google|tiktok|signup"
 */
(function () {
  'use strict';

  var SOURCE = (document.currentScript && document.currentScript.getAttribute('data-source'))
    || 'unknown';

  /* ── Traductions ─────────────────────────────────────────── */
  var T = {
    fr: {
      fish:        '🎣',
      title:       'Vous venez de vous faire phisher !',
      line1:       'Votre identifiant et mot de passe viennent d\'être capturés.',
      line2:       'Sur un vrai site malveillant, un inconnu les aurait maintenant en sa possession.',
      collected:   '— ce que nous avons récupéré —',
      lbl_id:      'Identifiant',
      lbl_pw:      'Longueur du mot de passe',
      chars:       'caractères',
      back:        '← Retour',
    },
    nl: {
      fish:        '🎣',
      title:       'Je bent zojuist gephisht!',
      line1:       'Je gebruikersnaam en wachtwoord zijn zojuist onderschept.',
      line2:       'Op een echte malafide site zou een onbekende ze nu in handen hebben.',
      collected:   '— wat we hebben verzameld —',
      lbl_id:      'Gebruikersnaam',
      lbl_pw:      'Lengte van het wachtwoord',
      chars:       'tekens',
      back:        '← Terug',
    },
    en: {
      fish:        '🎣',
      title:       'You just got phished!',
      line1:       'Your login and password were just captured.',
      line2:       'On a real malicious site, a stranger would now have them.',
      collected:   '— what we collected —',
      lbl_id:      'Username',
      lbl_pw:      'Password length',
      chars:       'characters',
      back:        '← Back',
    }
  };

  function getLang() {
    var m = document.cookie.match('(^|;)\\s*cq_lang\\s*=\\s*([^;]+)');
    var l = m ? decodeURIComponent(m[2]) : 'fr';
    return T[l] ? l : 'fr';
  }

  function anonEmail(val) {
    if (!val) return '***';
    var at = val.indexOf('@');
    if (at < 0) return val.charAt(0) + '***';
    return val.charAt(0) + '***' + val.substring(at);
  }

  /* ── Overlay "gotcha" ────────────────────────────────────── */
  function showGotcha(anonId, pwLen) {
    var l = getLang();
    var t = T[l];

    var o = document.createElement('div');
    o.id = 'cq-gotcha';
    o.style.cssText = 'position:fixed;inset:0;z-index:2147483647;'
      + 'background:#0a0c10;color:#e8eaf2;'
      + 'display:flex;flex-direction:column;align-items:center;justify-content:center;'
      + 'padding:24px;font-family:sans-serif;text-align:center;overflow-y:auto;';

    o.innerHTML =
      '<img src="/images/PHISHING_GOTCHA.png" alt="Gotcha" style="width:clamp(120px,28vw,200px);margin-bottom:16px;border-radius:12px" />'
    + '<div style="font-size:clamp(20px,5vw,34px);font-weight:900;color:#ff3b6b;'
    +   'margin-bottom:14px;max-width:560px;line-height:1.2">' + esc(t.title) + '</div>'
    + '<div style="max-width:520px;font-size:15px;color:#8892a4;line-height:1.7;margin-bottom:28px">'
    +   esc(t.line1) + '<br>' + esc(t.line2) + '</div>'
    + '<div style="background:#111520;border:1px solid #1e2535;border-radius:14px;'
    +   'padding:22px 28px;max-width:420px;width:100%;margin-bottom:32px;text-align:left">'
    +   '<div style="font-family:monospace;font-size:10px;color:#3a4260;text-transform:uppercase;'
    +     'letter-spacing:2px;margin-bottom:14px;text-align:center">' + esc(t.collected) + '</div>'
    +   '<div style="display:flex;justify-content:space-between;align-items:center;'
    +     'padding:10px 0;border-bottom:1px solid #1a2035;font-family:monospace;font-size:14px">'
    +     '<span style="color:#5a6580">' + esc(t.lbl_id) + '</span>'
    +     '<span style="color:#00ffd0;word-break:break-all">' + esc(anonId) + '</span>'
    +   '</div>'
    +   '<div style="display:flex;justify-content:space-between;align-items:center;'
    +     'padding:10px 0;font-family:monospace;font-size:14px">'
    +     '<span style="color:#5a6580">' + esc(t.lbl_pw) + '</span>'
    +     '<span style="color:#ffcc00">' + pwLen + ' ' + esc(t.chars) + '</span>'
    +   '</div>'
    + '</div>'
    + '<button id="cq-back-btn" style="'
    +   'background:transparent;border:1px solid #00ffd0;color:#00ffd0;'
    +   'font-family:monospace;font-size:13px;letter-spacing:2px;'
    +   'padding:12px 28px;border-radius:10px;cursor:pointer;text-transform:uppercase;'
    +   '-webkit-appearance:none">' + esc(t.back) + '</button>';

    document.body.appendChild(o);
    document.getElementById('cq-back-btn').onclick = function () { history.back(); };
  }

  function esc(s) {
    return String(s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  /* ── Bouton retour flottant ──────────────────────────────── */
  function addBackButton() {
    if (document.getElementById('cq-float-back')) return;
    var btn = document.createElement('button');
    btn.id = 'cq-float-back';
    btn.textContent = '←';
    btn.title = 'Retour / Terug / Back';
    btn.style.cssText = 'position:fixed;top:10px;left:10px;z-index:9998;'
      + 'background:rgba(0,0,0,0.55);color:#fff;'
      + 'border:1px solid rgba(255,255,255,0.25);border-radius:8px;'
      + 'font-size:20px;width:40px;height:40px;cursor:pointer;'
      + 'display:flex;align-items:center;justify-content:center;-webkit-appearance:none;';
    btn.onclick = function () { history.back(); };
    document.body.appendChild(btn);
  }

  /* ── Neutralise les liens "créer un compte" ─────────────── */
  function disableSignupLinks() {
    var KEYWORDS = ['sign up','signup','register','create','inscription',
                    'créer','aanmaken','s\'inscrire','inschrijven'];
    var SELECTORS = [
      '[data-testid="sign-up-link"]','#sign-up-link','#sign-up-button',
      'a[href*="signup"]','a[href*="register"]','a[href*="create"]',
      'a[href="/accounts/emailsignup/"]','a[href*="accounts/r/"]'
    ];
    SELECTORS.forEach(function (sel) {
      try {
        document.querySelectorAll(sel).forEach(noop);
      } catch (e) {}
    });
    document.querySelectorAll('a, button').forEach(function (el) {
      var txt = (el.textContent || '').toLowerCase().trim();
      if (KEYWORDS.some(function (kw) { return txt.indexOf(kw) >= 0; })) noop(el);
    });
  }

  function noop(el) {
    el.addEventListener('click', function (e) {
      e.preventDefault(); e.stopPropagation();
    }, true);
    el.style.cursor   = 'not-allowed';
    el.style.opacity  = '0.35';
    el.style.pointerEvents = 'auto'; // keep visible but blocked
  }

  /* ── Interception du formulaire ──────────────────────────── */
  function interceptForm() {
    var form = findLoginForm();
    if (!form) return;

    form.setAttribute('action', '#');
    form.setAttribute('data-cq-intercepted', '1');

    // Capture phase → bat les handlers natifs
    form.addEventListener('submit', handleSubmit, true);

    // Filet : intercepte aussi les clics sur submit buttons (Google, Instagram…)
    document.querySelectorAll(
      'input[type="submit"], [jsname="tJiF1e"], .login-button, #passwordNext, [role="button"]'
    ).forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        var f = btn.closest('form') || form;
        if (f && !f.dataset.cqFired) {
          f.dataset.cqFired = '1';
          handleSubmitFromForm(f);
          e.preventDefault(); e.stopPropagation();
          setTimeout(function () { delete f.dataset.cqFired; }, 300);
        }
      }, true);
    });
  }

  function findLoginForm() {
    var forms = document.querySelectorAll('form');
    for (var i = 0; i < forms.length; i++) {
      if (forms[i].querySelector('input[type="password"]')) return forms[i];
    }
    return forms[0] || null;
  }

  function handleSubmit(e) {
    e.preventDefault(); e.stopPropagation();
    handleSubmitFromForm(this);
  }

  function handleSubmitFromForm(form) {
    var emailEl = form.querySelector(
      'input[name="email"], input[name="username"], '
      + 'input[type="email"], input[name="identifier"], '
      + 'input[jsname="YPqjbf"][type="email"], input[type="text"]'
    );
    var passEl = form.querySelector('input[type="password"]');

    var emailVal = emailEl ? (emailEl.value || '').trim() : '';
    var pwLen    = passEl  ? (passEl.value  || '').length  : 0;
    var lang     = getLang();

    fetch('/phishing/catch', {
      method:  'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        email:     emailVal,
        pw_length: pwLen,
        source:    SOURCE,
        lang:      lang
      })
    }).catch(function () {});

    showGotcha(anonEmail(emailVal), pwLen);

    // Tracking missions : marque 'phishing-<source>' comme complété
    if (window.CyberTrack) {
      window.CyberTrack.track('phishing-' + SOURCE, 'gotcha');
      window.CyberTrack.scoreOnce('phishing-' + SOURCE + '-penalty', -30);
    }
  }

  /* ── Boot ────────────────────────────────────────────────── */
  function init() {
    addBackButton();
    disableSignupLinks();
    interceptForm();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
