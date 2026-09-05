// static/js/api.js — pindahan murni dari templates/index.html (split Fase 5).
// Global bersama (api, showToast, openM, fRp, ...) tetap window-scope.

//  STATE
// ══════════════════════════════════
let cart = [];
let katAktif = 'Semua';
let emojiSel = '📦';
let toko = {};
let lastTrx = null;
const EMOJI_CATS = {
  '🍔 Makanan': ['🍜','🍛','🍣','🍱','🍕','🍔','🌮','🌯','🥙','🍟','🌭','🥪','🥗','🥘','🍲','🍝','🧆','🥚','🍳','🥞','🧇','🧈','🥓','🥩','🍗','🍖','🌽','🥕','🧄','🧅','🥔','🍠','🥦','🥬','🥒','🫑','🥑','🍅','🍆','🧀','🫘','🥜','🥐','🍞','🥖','🥫','🍬','🍭','🎂','🍪','🍰','🧁','🍩','🍫','🧁','🥧','🍦','🍨','🍧','🥮','🍡','🍢','🍣','🍤','🍥','🍡','🥟','🥠','🥡','🦀','🦞','🦐','🦑','🦪','🍦'], 
  '🥤 Minuman': ['💧','🧋','🥤','🥛','☕','🫖','🍵','🧃','🍹','🍺','🥂','🍷','🍸','🥃','🧉','🍾','🫗','🧊','🥛','🍼','🫖','🍶','🍾','🥂','🍻','🥃','🍷','🍸','🍹','🧉','🧋','🥤','🧃'],
  '🧼 Kebutuhan Rumah': ['🧼','🧴','🪥','🦷','🧻','🧽','🪒','🫧','🪣','🧺','🪠','🧹','🫙','🧊','🛒','🧮','💡','🔦','🕯️','🔋','🔌','🪜','🪞','🛁','🚿','🧲','🧰','🧯','🧪','🌡️','🩹','🩺','💊','💉','🌿','🪴','🧷','🧵','🧶'],
  '👗 Fashion': ['👗','👔','👕','👖','🩱','👙','👚','🧥','🥼','🩲','🩳','👜','👝','🎒','💼','👞','👟','🥾','👠','👡','👢','🧣','🧤','🧢','👒','🎩','💍','💎','📿','⌚','👓','🕶️'],
  '📱 Elektronik': ['📱','💻','⌨️','🖥️','🖨️','📷','📹','🎮','🕹️','📺','📻','📡','🔋','💾','💿','📀','🎧','🎵','🔊','📞','☎️'],
  '📦 Umum': ['📦','🛍️','🎁','🏷️','🗃️','📋','📌','🖊️','✂️','📏','🪄','🗝️','🔑','💰','💳','🎫','🏪','🏬','🏥','💊','🩺','🩹','🌿','🪴','🌸','⭐','🎉','🎊','🧸','🛒','🧺','🧮','📎','🖇️','📐','✏️','🖋️','🖌️','📝','💼','📁','📂','🗂️','📅','📆','🗒️','🗓️','📇','📈','📉','📊','📍','✂️','🗃️','🗄️','🗑️','🔒','🔓','🔏','🔐','🔑','🔨','🔧','🔩','⚙️','🗜️','⚖️','🔗','⛓️','🧰','🧲','🪜','⚗️','🧪','🌡️','🧯','🛋️','🪑','🪞','🪟','🛏️','🛌','🖼️'],
};
let emojiCat = Object.keys(EMOJI_CATS)[0];

// ══════════════════════════════════

//  INIT
// ══════════════════════════════════
async function init() {
  // load saved theme
  if (localStorage.getItem('theme') === 'light') {
    document.documentElement.classList.add('light');
    const tog = document.getElementById('themeToggle');
    if (tog) tog.checked = true;
    applyThemeUI(true);
  }
  updateClock(); setInterval(updateClock, 1000);
  renderEmojiPicker();
  await Promise.all([muatPengaturan(), muatKategori(), muatProduk()]);
  setTodayDate();
  _updateTkBadge(); // cek pending tutup kasir (pemilik)
}

function setTodayDate() {
  const today = new Date().toISOString().split('T')[0];
  ['rTanggal','rDari','rKe','lDari','lKe'].forEach(id => {
    let el = document.getElementById(id);
    if (el) el.value = today;
  });
}

function updateClock() {
  const n = new Date();
  document.getElementById('clock').textContent = n.toLocaleTimeString('id-ID');
  document.getElementById('tgl').textContent = n.toLocaleDateString('id-ID',{weekday:'short',day:'numeric',month:'short',year:'numeric'});
}

// ══════════════════════════════════

//  API CALLS
// ══════════════════════════════════
async function api(url, method='GET', body=null) {
  const opts = { method, headers: {'Content-Type':'application/json'} };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  if (res.status === 401) {
    // Sesi berakhir — redirect ke login
    window.location.href = '/login';
    return;
  }
  if (!res.ok) {
    // Sertakan pesan error dari server (JSON {error}) agar toast informatif
    let msg = `HTTP ${res.status}`, rbody = null;
    try { rbody = await res.clone().json(); if (rbody && rbody.error) msg = rbody.error; } catch(_) {}
    const err = new Error(msg); err.status = res.status; err.body = rbody;
    throw err;
  }
  return res.json();
}

// ══════════════════════════════════
