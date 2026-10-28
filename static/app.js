'use strict';
const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => '&#' + c.charCodeAt(0) + ';');
const store = {
  get(k) { try { return localStorage.getItem(k) || '' } catch { return '' } },
  set(k, v) { try { v ? localStorage.setItem(k, v) : localStorage.removeItem(k) } catch {} },
};
const svg = d => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
const I = {
  user: svg('<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6 8-6s8 2 8 6"/>'),
  heart: svg('<path d="M12 20s-7.5-4.6-7.5-10.2A4.2 4.2 0 0 1 12 7.3a4.2 4.2 0 0 1 7.5 2.5C19.5 15.4 12 20 12 20z"/>'),
  heartF: `<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 20s-7.5-4.6-7.5-10.2A4.2 4.2 0 0 1 12 7.3a4.2 4.2 0 0 1 7.5 2.5C19.5 15.4 12 20 12 20z"/></svg>`,
  chat: svg('<path d="M4 5h16v11H9l-5 4z"/><path d="M8 9.5h8M8 12.5h5"/>'),
  feed: svg('<rect x="5" y="3" width="14" height="18"/><path d="M8 17h8"/>'),
  plus: svg('<path d="M12 5v14M5 12h14"/>'),
  mail: svg('<rect x="3" y="5" width="18" height="14"/><path d="m3 7 9 6 9-6"/>'),
  shield: svg('<path d="M12 3 20 6v6c0 5-3.4 8-8 9-4.6-1-8-4-8-9V6z"/><path d="m9 12 2 2 4-4"/>'),
  lock: svg('<rect x="5" y="11" width="14" height="10"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/><path d="M12 15v2"/>'),
  camera: svg('<rect x="3" y="7" width="18" height="13"/><circle cx="12" cy="13.5" r="3.5"/><path d="M8.5 7 10 4h4l1.5 3"/>'),
  flag: svg('<path d="M5 21V4h11l-2 4 2 4H5"/>'),
};

let T = store.get('t'), ME = null, Q = [], seen = new Set(), pIdx = 0, MATCHES = [], CUR = null, MSGS = [], moreMsgs = false;
let ws = null, wsTry = 0;
const shownMatch = new Set(), V = $('#view');

// api
const FIELD = {email: 'Проверьте email', password: 'Пароль — от 8 символов', name: 'Укажите имя', age: 'Возраст — от 18 до 99',
  tags: 'Нужно от 5 до 10 интересов', bio: '«О себе» — до 500 символов', body: 'Сообщение — до 2000 символов', reason: 'Выберите причину'};
const CODE = {email_unverified: 'Подтвердите email', profile: 'Сначала заполните интересы', banned: 'Аккаунт заблокирован модератором',
  self: 'Это вы', forbidden: 'Недостаточно прав'};
function errText(d, st) {
  if (typeof d === 'string') return CODE[d] || d;
  if (Array.isArray(d) && d[0]) return FIELD[d[0].loc?.at(-1)] || d[0].msg;
  return st >= 500 ? 'Сервер недоступен, попробуйте позже' : 'Ошибка ' + st;
}
async function api(path, {method = 'GET', body, form} = {}) {
  const headers = {};
  if (T) headers.Authorization = 'Bearer ' + T;
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  let r;
  try { r = await fetch('/api/' + path, {method, headers, body: form || (body !== undefined ? JSON.stringify(body) : undefined)}) }
  catch { throw new Error('Нет соединения с сервером') }
  const j = await r.json().catch(() => ({}));
  if (r.status === 401 && T) { logout(); throw new Error('Сессия истекла, войдите снова') }
  if (!r.ok) {
    const e = new Error(errText(j.detail, r.status)); e.code = j.detail; e.status = r.status;
    if (j.detail === 'banned') { logout(); toast(e.message) }
    throw e;
  }
  return j;
}

// utils
function toast(m) {
  const t = $('#toast'); t.textContent = m; t.hidden = false;
  clearTimeout(toast.t); toast.t = setTimeout(() => t.hidden = true, 3200);
}
function tone(s) { let h = 0; for (const c of String(s)) h = (h * 31 + c.codePointAt(0)) >>> 0; return `hsl(40 3% ${34 + h % 30}%)` }
function ph(name, url, cls = '') {
  return `<div class="ph ${cls}" style="--tone:${tone(name)}"><span class="ini">${esc([...String(name || '?')][0].toUpperCase())}</span>${
    url ? `<img src="${esc(url)}" alt="" loading="lazy">` : ''}</div>`;
}
const rtf = new Intl.RelativeTimeFormat('ru', {numeric: 'auto'});
function ago(ts) {
  const s = (new Date(ts) - Date.now()) / 1000;
  for (const [u, n] of [['day', 86400], ['hour', 3600], ['minute', 60]]) if (Math.abs(s) >= n) return rtf.format(Math.round(s / n), u);
  return 'только что';
}
const hm = ts => new Date(ts).toLocaleTimeString('ru', {hour: '2-digit', minute: '2-digit'});
const dayLabel = ts => new Date(ts).toLocaleDateString('ru', {day: 'numeric', month: 'long'});
const loading = () => V.innerHTML = '<div class="loading">Загрузка…</div>';
const unreadTotal = () => MATCHES.reduce((n, m) => n + (+m.unread || 0), 0);

// layout
function chrome() {
  const [, name = ''] = location.hash.slice(1).split('/');
  const on = n => name === n ? ' class="on" aria-current="page"' : '';
  document.body.classList.toggle('authed', !!T);
  if (!T) {
    $('#tbRight').innerHTML = `<button data-scroll="how">Как это работает</button><i></i><button data-scroll="safe">Безопасность</button><i></i><button data-auth="login">Войти</button>`;
    $('#navL').innerHTML = `<button data-scroll="how">Как это работает</button><button data-scroll="vibes">Совпадения</button><button data-scroll="safe">Безопасность</button>`;
    $('#navR').innerHTML = `<button data-auth="login">${I.user}<span class="lbl">Войти</span></button><button data-auth="register">${I.plus}<span class="lbl">Регистрация</span></button>`;
    $('#tabbar').classList.remove('on'); $('#tabbar').innerHTML = ''; $('#vbar').hidden = true;
    return;
  }
  const un = unreadTotal(), adm = ME?.role === 'admin';
  $('#tbRight').innerHTML = `<span>${esc(ME?.email || '')}</span><i></i><button data-logout>Выйти</button>`;
  $('#navL').innerHTML = `<a href="#/feed"${on('feed')}>Лента</a><a href="#/matches"${on('matches')}>Мэтчи</a><a href="#/chats"${on('chats')}>Чаты</a>` +
    (adm ? `<a href="#/admin"${on('admin')}>Модерация</a>` : '');
  $('#navR').innerHTML = `<a href="#/profile"${on('profile')}>${I.user}<span class="lbl">Профиль</span></a>` +
    `<a href="#/matches"${on('matches')}>${I.heart}<span class="lbl">Мэтчи (${MATCHES.length})</span></a>` +
    `<a href="#/chats"${on('chats')}>${I.chat}<span class="lbl">Чаты</span>${un ? `<span class="badge">${un}</span>` : ''}</a>`;
  $('#tabbar').classList.add('on');
  $('#tabbar').innerHTML = `<a href="#/feed"${on('feed')}>${I.feed}Лента</a><a href="#/matches"${on('matches')}>${I.heart}Мэтчи</a>` +
    `<a href="#/chats"${on('chats')}>${I.chat}Чаты${un ? ` (${un})` : ''}</a>` +
    (adm ? `<a href="#/admin"${on('admin')}>${I.shield}Модер.</a>` : `<a href="#/profile"${on('profile')}>${I.user}Профиль</a>`);
  const vb = $('#vbar');
  vb.hidden = !ME || ME.email_verified;
  if (!vb.hidden) vb.innerHTML = `<span>Подтвердите email — письмо отправлено на ${esc(ME.email)}</span><button class="link" data-resend>Отправить ещё раз</button>`;
}
addEventListener('scroll', () => $('#hdr').classList.toggle('scrolled', scrollY > 8), {passive: true});

document.addEventListener('click', e => {
  const t = e.target.closest('[data-auth],[data-scroll],[data-logout],[data-resend],[data-close]');
  if (!t) return;
  if (t.dataset.auth) openAuth(t.dataset.auth);
  else if (t.dataset.scroll) document.getElementById(t.dataset.scroll)?.scrollIntoView({behavior: 'smooth'});
  else if ('logout' in t.dataset) logout();
  else if ('resend' in t.dataset) resend();
  else if ('close' in t.dataset) t.closest('dialog').close();
});

// routing
const ROUTES = {feed: viewFeed, matches: viewMatches, chats: viewChats, profile: viewProfile, admin: viewAdmin};
async function route() {
  let h = location.hash.slice(1);
  if (h === 'verified' || h === 'verify-failed') {
    toast(h === 'verified' ? 'Email подтверждён' : 'Ссылка недействительна или устарела');
    history.replaceState(null, '', T ? '#/feed' : '#/');
    if (T) await loadMe().catch(() => {});
    h = location.hash.slice(1);
  }
  const [, name = '', arg] = h.split('/');
  if (name !== 'chats') CUR = null;
  if (!T) { chrome(); if (name) { history.replaceState(null, '', '#/') } return viewLanding() }
  if (!ME) { try { await loadMe() } catch (e) { if (T) { chrome(); V.innerHTML = errBlock(e.message) } return } }
  if (!ROUTES[name]) { location.replace('#/feed'); return }
  chrome();
  scrollTo(0, 0);
  await ROUTES[name](arg);
}
addEventListener('hashchange', route);

async function loadMe() {
  ME = await api('me');
  if (ME.email_verified) { connectWS(); await loadMatches().catch(() => {}) }
  chrome();
}
async function loadMatches() { MATCHES = await api('matches'); chrome() }
function logout() {
  T = ''; store.set('t', ''); ME = null; Q = []; seen.clear(); MATCHES = []; CUR = null;
  if (ws) { const w = ws; ws = null; w.onclose = null; w.close() }
  if (location.hash && location.hash !== '#/') location.hash = '#/'; else route();
}
async function resend() {
  try { const r = await api('resend-verification', {method: 'POST'}); toast(r.sent ? 'Письмо отправлено ещё раз' : 'Email уже подтверждён') }
  catch (e) { toast(e.message) }
}
const errBlock = m => `<section class="page"><div class="empty"><p class="kicker lined">Ошибка</p><h3>Что-то<br>пошло не так</h3><p>${esc(m)}</p><button class="btn" onclick="route()">Повторить</button></div></section>`;

// auth
let authMode = 'login';
function openAuth(mode) {
  authMode = mode;
  const reg = mode === 'register';
  $('#authTitle').textContent = reg ? 'Регистрация' : 'Вход';
  $('#aSubmit').textContent = reg ? 'Создать аккаунт' : 'Войти';
  $('#aPw').autocomplete = reg ? 'new-password' : 'current-password';
  $$('.reg', $('#authForm')).forEach(e => e.hidden = !reg);
  $$('[data-tab]').forEach(b => { b.classList.toggle('on', b.dataset.tab === mode); b.setAttribute('aria-selected', b.dataset.tab === mode) });
  $('#aErr').textContent = '';
  const d = $('#authDlg'); if (!d.open) d.showModal();
  $('#aEmail').focus();
}
$$('[data-tab]').forEach(b => b.onclick = () => openAuth(b.dataset.tab));
$('#authForm').onsubmit = async e => {
  e.preventDefault();
  const b = {email: $('#aEmail').value.trim(), password: $('#aPw').value}, btn = $('#aSubmit');
  if (authMode === 'register') { b.name = $('#aName').value.trim(); b.age = +$('#aAge').value || 0 }
  btn.disabled = true;
  try {
    T = (await api(authMode, {method: 'POST', body: b})).token; store.set('t', T);
    $('#authDlg').close(); $('#aPw').value = '';
    await loadMe();
    if (authMode === 'register') { toast('Письмо для подтверждения отправлено на ' + b.email); location.hash = '#/profile' }
    else location.hash = ME.has_profile ? '#/feed' : '#/profile';
    route();
  } catch (err) { $('#aErr').textContent = err.message }
  finally { btn.disabled = false }
};

// landing
function viewLanding() {
  V.innerHTML = `
<section class="hero"><div class="hero-in">
  <p class="kicker lined">Знакомства<br>по смыслу<br>интересов.</p>
  <h1 class="giant" aria-label="Orbita">ORBITA
    <svg class="orbit" viewBox="0 0 1000 400" preserveAspectRatio="none" aria-hidden="true">
      <ellipse cx="500" cy="210" rx="470" ry="92" transform="rotate(-7 500 210)"/>
    </svg>
    <span class="planet" aria-hidden="true"></span>
    <svg class="orbit front" viewBox="0 0 1000 400" preserveAspectRatio="none" aria-hidden="true">
      <path d="M30 210A470 92 0 0 0 970 210" transform="rotate(-7 500 210)"/>
    </svg>
  </h1>
  <div class="hero-foot">
    <div class="hero-cta"><button class="btn" data-auth="register">Создать аккаунт</button><button class="link" data-auth="login">Уже есть аккаунт</button></div>
    <p class="kicker lined">Без геолокации<br>только интересы<br>2026</p>
  </div>
</div></section>

<section class="band" id="how"><div class="band-in">
  <div class="band-item"><div class="tile"><small>01</small><b>#5</b></div>
    <div><h3>Теги</h3><p>Расскажите о себе 5–10 интересами — от «джаза» до «скалолазания».</p><button class="link" data-auth="register">Начать →</button></div></div>
  <div class="band-item"><div class="tile"><small>02</small><b>87%</b></div>
    <div><h3>Смысл</h3><p>Нейросеть сравнивает смысл интересов, а не буквы — и сортирует ленту по близости.</p><button class="link" data-scroll="vibes">Подробнее →</button></div></div>
  <div class="band-item"><div class="tile"><small>03</small><b>♥</b></div>
    <div><h3>Мэтч</h3><p>Взаимный лайк открывает чат. Общие интересы — готовый повод написать первым.</p><button class="link" data-auth="register">Попробовать →</button></div></div>
</div></section>

<section class="season" id="vibes"><div class="season-in">
  <div>
    <p class="kicker">Как совпадают люди</p>
    <h2>Бег ≈<br>марафон</h2>
    <p class="lead">«Бег» и «марафоны» совпадут, даже если слова разные. В карточке — процент близости и подсвеченные общие интересы.</p>
    <button class="btn" data-auth="register">Найти своих</button>
  </div>
  <div class="mock" aria-hidden="true">
    ${ph('Максим', '')}
    <div class="mock-body">
      <p class="kicker">Совпадение</p>
      <p class="sim">87<small>%</small></p>
      <p class="name" style="font-size:20px">Максим, 29</p>
      <div class="chips"><span class="on">марафоны</span><span class="on">кофе</span><span>винил</span></div>
    </div>
  </div>
</div></section>

<section class="feats" id="safe"><div class="feats-in">
  <div class="feat">${I.mail}<div><b>Подтверждённый email</b><span>Лента и чат — только после подтверждения</span></div></div>
  <div class="feat">${I.chat}<div><b>Чат после мэтча</b><span>Никаких сообщений без взаимной симпатии</span></div></div>
  <div class="feat">${I.shield}<div><b>Модерация</b><span>Жалобы, блокировки и проверка анкет</span></div></div>
  <div class="feat">${I.lock}<div><b>Без геолокации</b><span>Не спрашиваем местоположение, удаляем геометки из фото</span></div></div>
</div></section>
<footer class="foot"><b>ORBITA</b><span>Знакомства по смыслу интересов · 18+</span></footer>`;
}

// email verification
function gate() {
  V.innerHTML = `<section class="page"><div class="empty">
    <p class="kicker lined">Последний шаг</p><h3>Подтвердите<br>email</h3>
    <p>Мы отправили письмо на <b>${esc(ME.email)}</b>. Перейдите по ссылке из письма — и откроются лента, мэтчи и чат.</p>
    <div class="hero-cta"><button class="btn" data-resend>Отправить ещё раз</button><button class="link" id="recheck">Я подтвердил(а)</button></div>
    <a class="link quiet" href="#/profile">Пока заполнить профиль →</a></div></section>`;
  $('#recheck').onclick = async () => { await loadMe().catch(() => {}); ME.email_verified ? route() : toast('Email ещё не подтверждён') };
}
addEventListener('focus', () => { if (T && ME && !ME.email_verified) loadMe().then(() => ME.email_verified && route()).catch(() => {}) });

// feed
async function more() {
  const r = await api('feed?limit=20');
  Q.push(...r.filter(c => !seen.has(c.id) && seen.add(c.id)));
}
async function viewFeed() {
  if (!ME.email_verified) return gate();
  if (!ME.has_profile) { toast('Сначала заполните интересы'); location.replace('#/profile'); return }
  if (!Q.length) {
    loading();
    try { await more() } catch (e) {
      if (e.code === 'profile') { ME.has_profile = false; return location.replace('#/profile') }
      if (e.code === 'email_unverified') { ME.email_verified = false; chrome(); return gate() }
      V.innerHTML = errBlock(e.message); return;
    }
  }
  renderFeed();
}
function renderFeed() {
  if (location.hash !== '#/feed') return;
  const c = Q[0];
  if (!c) {
    V.innerHTML = `<section class="page"><div class="empty"><p class="kicker lined">Лента</p><h3>Пока<br>всё</h3>
      <p>Подходящие люди закончились. Добавьте больше интересов или загляните позже — новые анкеты появляются каждый день.</p>
      <div class="hero-cta"><a class="btn" href="#/profile">Изменить интересы</a><button class="link" id="reload">Обновить</button></div></div></section>`;
    $('#reload').onclick = () => { seen.clear(); viewFeed() };
    return;
  }
  const photos = c.photos || [], cur = photos[pIdx] || '', common = new Set(c.common);
  V.innerHTML = `<section class="page">
  <div class="page-head"><h2 class="h-sec">Лента</h2><a class="link" href="#/profile">Изменить интересы</a></div>
  <div class="feed">
    <div class="feed-photo" id="fp" aria-label="Фото. Перетащите вправо — нравится, влево — пропустить">
      ${photos.length > 1 ? `<div class="dots">${photos.map((_, i) => `<i class="${i === pIdx ? 'on' : ''}"></i>`).join('')}</div>` : ''}
      <span class="stamp like">Нравится</span><span class="stamp nope">Мимо</span>
      ${ph(c.name, cur)}
    </div>
    <div class="feed-info">
      <p class="kicker">Совпадение по смыслу интересов</p>
      <p class="sim">${Math.max(0, Math.round(c.sim * 100))}<small>%</small></p>
      <h3 class="name">${esc(c.name)}, ${c.age}</h3>
      ${c.bio ? `<p class="bio">${esc(c.bio)}</p>` : ''}
      <p class="kicker mut">Интересы${common.size ? ' · общие выделены' : ''}</p>
      <div class="chips">${c.tags.map(t => `<span class="${common.has(t) ? 'on' : ''}">${esc(t)}</span>`).join('')}</div>
      <div class="acts">
        <button class="btn ghost" id="nope" aria-label="Пропустить">Пропустить</button>
        <button class="btn" id="like" aria-label="Нравится">Нравится ${I.heartF.replace('<svg', '<svg width="14" height="14"')}</button>
      </div>
      <div><button class="link quiet" id="rep">Пожаловаться</button></div>
    </div>
  </div>
  ${Q.length > 1 ? `<div class="page-head sub"><h3 class="h-sec">Далее в ленте</h3><span class="kicker mut">${Q.length - 1}+ анкет</span></div>
  <div class="grid4">${Q.slice(1, 5).map(n => `<div class="pcard">${ph(n.name, n.photos?.[0])}
    <div class="meta"><b>${esc(n.name)}, ${n.age}</b><span>${Math.round(n.sim * 100)}%</span></div></div>`).join('')}</div>` : ''}
  </section>`;
  $('#nope').onclick = () => vote(false);
  $('#like').onclick = () => vote(true);
  $('#rep').onclick = () => openReport(c, () => { Q = Q.filter(x => x.id !== c.id); pIdx = 0; renderFeed() });
  drag($('#fp'), photos.length);
}
function drag(el, n) {
  let x0 = null, dx = 0;
  const [like, nope] = [$('.stamp.like', el), $('.stamp.nope', el)];
  el.onpointerdown = e => { x0 = e.clientX; dx = 0; el.classList.add('drag'); el.setPointerCapture(e.pointerId) };
  el.onpointermove = e => {
    if (x0 == null) return;
    dx = e.clientX - x0;
    el.style.transform = `translateX(${dx}px) rotate(${dx / 30}deg)`;
    like.style.opacity = Math.max(0, Math.min(1, dx / 110)); nope.style.opacity = Math.max(0, Math.min(1, -dx / 110));
  };
  el.onpointerup = el.onpointercancel = e => {
    if (x0 == null) return;
    x0 = null; el.classList.remove('drag');
    if (Math.abs(dx) > 110) return vote(dx > 0);
    el.style.transform = ''; like.style.opacity = nope.style.opacity = 0;
    if (Math.abs(dx) < 6 && n > 1 && e.type === 'pointerup') {
      const r = el.getBoundingClientRect();
      pIdx = (pIdx + (e.clientX - r.left > r.width / 2 ? 1 : n - 1)) % n; renderFeed();
    }
  };
}
async function vote(liked) {
  const c = Q.shift(); if (!c) return;
  pIdx = 0; renderFeed();
  if (Q.length < 5) more().then(() => { if (Q.length && location.hash === '#/feed' && !$('#fp')) renderFeed() }).catch(() => {});
  try {
    const r = await api('swipe', {method: 'POST', body: {target: c.id, liked}});
    if (r.match) showMatch({id: c.id, name: c.name, age: c.age, photo: c.photos?.[0]});
  } catch (e) { if (e.status === 429) toast(e.message) }
}
addEventListener('keydown', e => {
  if (location.hash !== '#/feed' || e.target.closest('input,textarea,dialog') || !Q[0] || !$('#matchOv').hidden) return;
  if (e.key === 'ArrowRight') vote(true); else if (e.key === 'ArrowLeft') vote(false);
});

function showMatch(u) {
  if (shownMatch.has(u.id)) return;
  shownMatch.add(u.id);
  loadMatches().catch(() => {});
  const ov = $('#matchOv'), mine = ME.photos?.[0]?.url;
  ov.innerHTML = `<div><p class="kicker">Взаимная симпатия</p><h2>ЭТО<br>МЭТЧ</h2>
    <div class="pair">${ph(ME.name, mine)}${ph(u.name, u.photo)}</div>
    <p>Вы и ${esc(u.name)} понравились друг другу</p>
    <div class="row"><a class="btn inv" href="#/chats/${u.id}" id="mGo">Написать</a><button class="btn" style="border-color:#fff" id="mClose">Продолжить</button></div></div>`;
  ov.hidden = false; $('#mGo').focus();
  const close = () => ov.hidden = true;
  $('#mGo').onclick = close; $('#mClose').onclick = close;
  ov.onkeydown = e => e.key === 'Escape' && close();
}

// reports
let repTarget = null, repDone = null;
function openReport(u, done) {
  repTarget = u; repDone = done;
  $('#repWho').textContent = `На пользователя ${u.name}`;
  $('#repForm').reset(); $('#repErr').textContent = '';
  $('#repDlg').showModal();
}
$('#repForm').onsubmit = async e => {
  e.preventDefault();
  const reason = $('#repForm').reason.value;
  if (!reason) { $('#repErr').textContent = 'Выберите причину'; return }
  try {
    await api(`users/${repTarget.id}/report`, {method: 'POST', body: {reason, comment: $('#repText').value}});
    $('#repDlg').close(); toast('Жалоба отправлена, пользователь заблокирован');
    MATCHES = MATCHES.filter(m => m.id !== repTarget.id); chrome();
    repDone?.();
  } catch (err) { $('#repErr').textContent = err.message }
};

// matches
async function viewMatches() {
  if (!ME.email_verified) return gate();
  loading();
  try { await loadMatches() } catch (e) { V.innerHTML = errBlock(e.message); return }
  V.innerHTML = `<section class="page">
  <div class="page-head"><h2 class="h-sec">Ваши мэтчи</h2><span class="kicker mut">${MATCHES.length} ${plural(MATCHES.length, 'человек', 'человека', 'человек')}</span></div>
  ${MATCHES.length ? `<div class="grid4">${MATCHES.map(m => `<a class="pcard" href="#/chats/${m.id}">
      <div style="position:relative">${ph(m.name, m.photo)}<span class="heart" aria-hidden="true">${I.heartF}</span></div>
      <div class="meta"><b>${esc(m.name)}, ${m.age}</b>${+m.unread ? `<span class="badge">${m.unread}</span>` : ''}</div>
      <span>${m.last_body ? esc(m.last_body.slice(0, 60)) : 'Мэтч ' + ago(m.matched_at)}</span>
      <span class="link" style="align-self:flex-start;color:var(--ink)">Написать →</span></a>`).join('')}</div>`
    : `<div class="empty"><h3>Пока нет<br>мэтчей</h3><p>Ставьте лайки в ленте — когда симпатия взаимна, здесь появится человек и откроется чат.</p><a class="btn" href="#/feed">В ленту</a></div>`}
  </section>`;
}
const plural = (n, a, b, c) => n % 10 === 1 && n % 100 !== 11 ? a : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20) ? b : c;

// chat
async function viewChats(arg) {
  if (!ME.email_verified) return gate();
  CUR = arg ? +arg : null;
  if (!MATCHES.length || !CUR) await loadMatches().catch(() => {});
  V.innerHTML = `<section class="page">
  <div class="page-head"><h2 class="h-sec">Чаты</h2><a class="link" href="#/matches">Все мэтчи</a></div>
  <div class="chat ${CUR ? 'open' : ''}"><div class="clist" id="clist"></div><div class="conv" id="conv"></div></div></section>`;
  renderList();
  if (!CUR) {
    $('#conv').innerHTML = `<div class="conv-empty"><div><p class="kicker">Сообщения</p><p>${MATCHES.length ? 'Выберите собеседника слева' : 'Чат откроется после первого мэтча'}</p></div></div>`;
    return;
  }
  const m = MATCHES.find(x => x.id === CUR);
  if (!m) { $('#conv').innerHTML = `<div class="conv-empty"><p>Этот чат недоступен</p></div>`; return }
  $('#conv').innerHTML = `<div class="conv-h"><a class="link quiet back" href="#/chats">← Назад</a><b>${esc(m.name)}, ${m.age}</b>
    <span style="display:flex;gap:18px"><button class="link quiet" id="cRep">Пожаловаться</button><button class="link quiet" id="cBlock">Заблокировать</button></span></div>
    <div class="msgs" id="msgs" aria-live="polite"><div class="loading">Загрузка…</div></div>
    <form class="compose" id="compose"><textarea id="mText" rows="1" maxlength="2000" placeholder="Сообщение…" aria-label="Сообщение"></textarea><button class="btn">Отправить</button></form>`;
  $('#cRep').onclick = () => openReport(m, () => location.hash = '#/chats');
  $('#cBlock').onclick = async () => {
    if (!confirm(`Заблокировать ${m.name}? Мэтч и чат исчезнут у вас обоих.`)) return;
    try { await api(`users/${m.id}/block`, {method: 'POST'}); MATCHES = MATCHES.filter(x => x.id !== m.id); toast('Пользователь заблокирован'); location.hash = '#/chats' }
    catch (e) { toast(e.message) }
  };
  const ta = $('#mText');
  ta.onkeydown = e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); $('#compose').requestSubmit() } };
  ta.oninput = () => { ta.style.height = 'auto'; ta.style.height = ta.scrollHeight + 'px' };
  $('#compose').onsubmit = async e => {
    e.preventDefault();
    const body = ta.value.trim(); if (!body) return;
    ta.value = ''; ta.style.height = '';
    try { addMsg(await api(`chats/${CUR}/messages`, {method: 'POST', body: {body}})) }
    catch (err) { ta.value = body; toast(err.message) }
  };
  try {
    MSGS = await api(`chats/${CUR}/messages?limit=50`); moreMsgs = MSGS.length === 50;
    m.unread = 0; chrome(); renderList(); renderMsgs(true);
  } catch (e) { $('#msgs').innerHTML = `<div class="conv-empty"><p>${esc(e.message)}</p></div>` }
  $('#msgs').onscroll = async ev => {
    const el = ev.target;
    if (el.scrollTop > 40 || !moreMsgs || el.dataset.busy) return;
    el.dataset.busy = 1;
    try {
      const older = await api(`chats/${CUR}/messages?limit=50&before=${MSGS[0].id}`);
      moreMsgs = older.length === 50;
      const h = el.scrollHeight; MSGS = [...older, ...MSGS]; renderMsgs(); el.scrollTop = el.scrollHeight - h;
    } finally { delete el.dataset.busy }
  };
  ta.focus();
}
function renderList() {
  const el = $('#clist'); if (!el) return;
  el.innerHTML = MATCHES.map(m => `<a class="citem ${m.id === CUR ? 'on' : ''}" href="#/chats/${m.id}">${ph(m.name, m.photo)}
    <div><b>${esc(m.name)}</b><p>${m.last_body ? (m.last_sender === ME.id ? 'Вы: ' : '') + esc(m.last_body) : 'Новый мэтч — напишите первым'}</p></div>
    ${+m.unread ? `<span class="badge">${m.unread}</span>` : `<span class="kicker mut" style="font-size:9.5px">${m.last_at ? hm(m.last_at) : ''}</span>`}</a>`).join('')
    || `<div class="conv-empty"><p>Мэтчей пока нет</p></div>`;
}
function renderMsgs(bottom) {
  const el = $('#msgs'); if (!el) return;
  const stick = bottom || el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  let last = '', html = moreMsgs ? '<div class="day">↑ Ранние сообщения</div>' : '';
  const lastMine = [...MSGS].reverse().find(m => m.sender === ME.id);
  for (const m of MSGS) {
    const d = dayLabel(m.created_at);
    if (d !== last) { html += `<div class="day">${d}</div>`; last = d }
    const me = m.sender === ME.id;
    html += `<div class="msg ${me ? 'me' : ''}">${esc(m.body)}<time>${hm(m.created_at)}${me && m === lastMine && m.read_at ? ' · прочитано' : ''}</time></div>`;
  }
  el.innerHTML = html || `<div class="conv-empty"><div><p class="kicker">Новый мэтч</p><p>Начните с общего интереса — это самый простой повод.</p></div></div>`;
  if (stick) el.scrollTop = el.scrollHeight;
}
function addMsg(m) {
  if (MSGS.some(x => x.id === m.id)) return;
  MSGS.push(m); renderMsgs(m.sender === ME.id);
  const mt = MATCHES.find(x => x.id === CUR);
  if (mt) { Object.assign(mt, {last_body: m.body, last_sender: m.sender, last_at: m.created_at}); MATCHES = [mt, ...MATCHES.filter(x => x !== mt)]; renderList() }
}

// realtime
function connectWS() {
  if (ws || !T) return;
  const s = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/ws`);
  ws = s;
  s.onopen = () => { s.send(T); wsTry = 0 };
  s.onmessage = e => { try { onEvent(JSON.parse(e.data)) } catch {} };
  s.onclose = ev => {
    if (ws !== s) return;
    ws = null;
    if (ev.code !== 4401 && T) setTimeout(connectWS, Math.min(30000, 1000 * 2 ** wsTry++));
  };
}
setInterval(() => ws?.readyState === 1 && ws.send('ping'), 25000);
function onEvent(ev) {
  if (ev.type === 'message') {
    const m = ev.message, mine = m.sender === ME.id;
    if (CUR === ev.chat && location.hash.startsWith('#/chats/')) {
      addMsg(m);
      if (!mine) api(`chats/${CUR}/read`, {method: 'POST'}).catch(() => {});
    } else {
      const mt = MATCHES.find(x => x.id === ev.chat);
      if (mt) { Object.assign(mt, {last_body: m.body, last_sender: m.sender, last_at: m.created_at}); if (!mine) mt.unread = (+mt.unread || 0) + 1 }
      else loadMatches().catch(() => {});
      if (!mine) toast(`Новое сообщение${mt ? ' от ' + mt.name : ''}`);
      chrome(); renderList();
    }
  } else if (ev.type === 'read') {
    if (CUR === ev.chat) { MSGS.forEach(m => { if (m.sender === ME.id && m.id <= ev.upto) m.read_at ||= new Date().toISOString() }); renderMsgs() }
  } else if (ev.type === 'match') {
    showMatch(ev.user);
  } else if (ev.type === 'unmatch') {
    MATCHES = MATCHES.filter(m => m.id !== ev.chat); chrome();
    if (CUR === ev.chat) { toast('Чат закрыт'); location.hash = '#/chats' } else renderList();
  }
}

// profile
function tagList(s) { return [...new Set(s.split(',').map(t => t.trim().toLowerCase()).filter(Boolean))] }
function viewProfile() {
  const first = !ME.has_profile;
  V.innerHTML = `<section class="page">
  <div class="page-head"><h2 class="h-sec">${first ? 'Расскажите о себе' : 'Профиль'}</h2><span class="kicker mut">${esc(ME.name)}, ${ME.age}</span></div>
  <div class="prof">
    <div class="stack">
      <p class="kicker">Фото · до 6</p>
      <div class="pgrid" id="pgrid"></div>
      <input type="file" id="pfile" accept="image/jpeg,image/png,image/webp" multiple hidden>
      <p class="hint">JPEG, PNG или WebP до 8 МБ. Мы перекодируем фото и удаляем метаданные, включая геометки камеры.</p>
    </div>
    <form class="stack" id="pform">
      <div class="field"><label for="ptags">Интересы · 5–10 через запятую</label>
        <textarea id="ptags" rows="3" placeholder="бег, кофе, настолки, джаз, фотография">${esc((ME.tags || []).join(', '))}</textarea></div>
      <div class="chips light" id="pchips"></div>
      <div class="field"><label for="pbio">О себе</label><textarea id="pbio" rows="4" maxlength="500" placeholder="Пара фраз — необязательно">${esc(ME.bio || '')}</textarea></div>
      <button class="btn" id="psave">${first ? 'Сохранить и смотреть людей' : 'Сохранить'}</button>
      <p class="err" id="perr" role="alert"></p>
      <div class="acct">
        <p class="kicker mut">Аккаунт</p>
        <p style="margin:0">${esc(ME.email)} · ${ME.email_verified ? '<span class="pill dark">Подтверждён</span>' : '<span class="pill">Не подтверждён</span> <button type="button" class="link" data-resend>Отправить письмо</button>'}</p>
        <div><button type="button" class="link quiet" data-logout>Выйти из аккаунта</button></div>
      </div>
    </form>
  </div></section>`;
  const chips = () => { const t = tagList($('#ptags').value); $('#pchips').innerHTML = t.map(x => `<span>${esc(x)}</span>`).join('') + `<span class="kicker mut" style="border:0;padding:6px 0">${t.length}/10</span>` };
  $('#ptags').oninput = chips; chips();
  renderPhotos();
  $('#pfile').onchange = async e => {
    for (const f of [...e.target.files]) {
      const fd = new FormData(); fd.append('file', f);
      try { ME.photos = await api('photos', {method: 'POST', form: fd}); renderPhotos() }
      catch (err) { toast(err.message); break }
    }
    e.target.value = '';
  };
  $('#pform').onsubmit = async e => {
    e.preventDefault();
    const tags = tagList($('#ptags').value);
    if (tags.length < 5 || tags.length > 10) { $('#perr').textContent = 'Нужно от 5 до 10 разных интересов'; return }
    $('#psave').disabled = true; $('#perr').textContent = '';
    try {
      await api('profile', {method: 'PUT', body: {tags, bio: $('#pbio').value}});
      Q = []; seen.clear(); ME = await api('me'); chrome();
      toast('Профиль сохранён');
      if (first) location.hash = '#/feed';
    } catch (err) { $('#perr').textContent = err.message }
    finally { $('#psave').disabled = false }
  };
}
function renderPhotos() {
  const g = $('#pgrid'); if (!g) return;
  const ps = ME.photos || [];
  g.innerHTML = ps.map((p, i) => `<div class="pslot">${i === 0 ? '<span class="main">ГЛАВНОЕ</span>' : ''}${ph(ME.name, p.url)}
    <div class="tools">${i ? `<button data-main="${p.id}">Главное</button>` : '<span></span>'}<button data-del="${p.id}" aria-label="Удалить фото">Удалить</button></div></div>`).join('') +
    (ps.length < 6 ? `<button class="padd" id="padd" type="button"><span>+</span>Добавить фото</button>` : '');
  $('#padd')?.addEventListener('click', () => $('#pfile').click());
  $$('[data-del]', g).forEach(b => b.onclick = async () => {
    try { ME.photos = await api('photos/' + b.dataset.del, {method: 'DELETE'}); renderPhotos() } catch (e) { toast(e.message) } });
  $$('[data-main]', g).forEach(b => b.onclick = async () => {
    try { ME.photos = await api(`photos/${b.dataset.main}/main`, {method: 'POST'}); renderPhotos() } catch (e) { toast(e.message) } });
}

// admin
const REASONS = {spam: 'Спам', fake: 'Фейк', abuse: 'Оскорбления', inappropriate_photo: 'Фото', underage: 'Младше 18', other: 'Другое'};
async function viewAdmin(status = 'open') {
  if (ME.role !== 'admin') { location.replace('#/feed'); return }
  loading();
  let rows;
  try { rows = await api('admin/reports?status=' + status) } catch (e) { V.innerHTML = errBlock(e.message); return }
  const tab = (s, l) => `<a href="#/admin/${s}" class="link ${s === status ? '' : 'quiet'}">${l}</a>`;
  V.innerHTML = `<section class="page">
  <div class="page-head"><h2 class="h-sec">Модерация</h2><div style="display:flex;gap:22px">${tab('open', 'Открытые')}${tab('actioned', 'Заблокированы')}${tab('dismissed', 'Отклонённые')}</div></div>
  ${rows.length ? rows.map(r => `<div class="rep">
    ${ph(r.target_name, r.photos[0]?.url)}
    <div>
      <p style="margin:0 0 8px"><span class="pill dark">${REASONS[r.reason] || r.reason}</span>${r.banned_at ? '<span class="pill">Забанен</span>' : ''}${r.hidden_at && !r.banned_at ? '<span class="pill">Скрыт</span>' : ''}<span class="kicker mut">жалоб открыто: ${r.open_reports}</span></p>
      <h4>${esc(r.target_name)}, ${r.target_age} <span class="mut" style="font-weight:400">#${r.target}</span></h4>
      <p class="hint">${esc(r.target_bio || 'без описания')}</p>
      <div class="chips light" style="margin-top:8px">${r.target_tags.map(t => `<span>${esc(t)}</span>`).join('')}</div>
      ${r.comment ? `<blockquote>«${esc(r.comment)}» — ${esc(r.reporter_name)}</blockquote>` : `<p class="hint" style="margin-top:8px">от ${esc(r.reporter_name)} · ${ago(r.created_at)}</p>`}
      ${r.messages.length ? `<p class="kicker mut" style="margin-top:12px">Сообщения жалующемуся</p>${r.messages.slice(0, 5).map(m => `<blockquote>${esc(m.body)}</blockquote>`).join('')}` : ''}
      ${r.photos.length ? `<div class="thumbs">${r.photos.map(p => `<div style="position:relative">${ph(r.target_name, p.url)}<button data-delph="${p.id}">Удалить</button></div>`).join('')}</div>` : ''}
    </div>
    <div class="side">${status === 'open' ? `<button class="btn" data-act="ban" data-id="${r.id}">Заблокировать</button><button class="btn ghost" data-act="dismiss" data-id="${r.id}">Отклонить</button>`
      : r.banned_at ? `<button class="btn ghost" data-unban="${r.target}">Разблокировать</button>` : ''}</div>
  </div>`).join('') : `<div class="empty"><h3>Чисто</h3><p>Жалоб в этом разделе нет.</p></div>`}
  </section>`;
  $$('[data-act]').forEach(b => b.onclick = async () => {
    if (b.dataset.act === 'ban' && !confirm('Заблокировать пользователя?')) return;
    try { await api('admin/reports/' + b.dataset.id, {method: 'POST', body: {action: b.dataset.act}}); toast('Готово'); viewAdmin(status) } catch (e) { toast(e.message) } });
  $$('[data-unban]').forEach(b => b.onclick = async () => {
    try { await api(`admin/users/${b.dataset.unban}/unban`, {method: 'POST'}); toast('Разблокирован'); viewAdmin(status) } catch (e) { toast(e.message) } });
  $$('[data-delph]').forEach(b => b.onclick = async () => {
    if (!confirm('Удалить фото?')) return;
    try { await api('admin/photos/' + b.dataset.delph, {method: 'DELETE'}); toast('Фото удалено'); viewAdmin(status) } catch (e) { toast(e.message) } });
}

route();
