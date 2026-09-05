// static/js/pendukung.js — pindahan murni dari templates/index.html (split Fase 5).
// Global bersama (api, showToast, openM, fRp, ...) tetap window-scope.

//  PENGATURAN TOKO
// ══════════════════════════════════
async function muatPengaturan() {
  toko = await api('/api/pengaturan');
  updateLogo();
  updatePrintCSS();
}

function updateLogo() {
  const nm = toko.nama_toko || 'KasirToko';
  const w = nm.split(' ');
  const html = w.length > 1 ? `${w[0]}<span>${w.slice(1).join(' ')}</span>` : `<span>${nm}</span>`;
  document.getElementById('logoToko').innerHTML = html;
  const dl = document.getElementById('drawerLogo');
  if (dl) dl.innerHTML = html;
}

function updatePrintCSS() {
  let s = document.getElementById('dynPrint');
  if (!s) { s=document.createElement('style'); s.id='dynPrint'; document.head.appendChild(s); }
  const mm = toko.ukuran_kertas || '58';
  // Driver 58mm → @page 58mm, konten 55mm + margin 1.5mm kiri-kanan → masuk kertas fisik 57mm
  // Driver 80mm → @page 80mm, konten 76mm + margin 2mm kiri-kanan
  const pgW = mm === '58' ? '58' : mm;
  const cW  = mm === '58' ? '55' : `${parseInt(mm)-4}`;
  const mg  = mm === '58' ? '1.5mm' : '2mm';
  const fs    = mm === '58' ? '10px' : '11px';
  const fsNm  = mm === '58' ? '12px' : '14px';
  const fsSub = mm === '58' ? '9px'  : '10px';
  s.textContent = `@media print{
    @page{size:${pgW}mm auto;margin:0;}
    html,body{width:${pgW}mm!important;}
    #printArea{width:${cW}mm!important;margin:0 ${mg}!important;font-size:${fs}!important;line-height:1.4!important;position:static!important;}
    .psnm{font-size:${fsNm}!important;}
    .pssub,.psfooter{font-size:${fsSub}!important;}
    .psrow,.psitem,.psitem-h{font-size:${fs}!important;}
    .psbold{font-size:calc(${fs} + 1px)!important;}
  }`;
}

function openPengaturan() {
  document.getElementById('tNama').value  = toko.nama_toko||'';
  document.getElementById('tAlamat').value= toko.alamat||'';
  document.getElementById('tTelp').value  = toko.telp||'';
  document.getElementById('tPesan').value = toko.pesan_struk||'';
  document.getElementById('tKertas').value= toko.ukuran_kertas||'58';
  // Printer app setting
  const scheme = toko.printer_app_scheme || 'rawbt';
  const knownSchemes = ['rawbt','myprinter','printhand'];
  if (knownSchemes.includes(scheme)) {
    document.getElementById('tPrinterApp').value = scheme;
    document.getElementById('fgCustomScheme').style.display = 'none';
  } else {
    document.getElementById('tPrinterApp').value = 'other';
    document.getElementById('tCustomScheme').value = scheme;
    document.getElementById('fgCustomScheme').style.display = 'block';
  }
  previewToko();
  openM('mPengaturan');
}

// Toggle custom scheme input
document.getElementById('tPrinterApp').addEventListener('change', function() {
  document.getElementById('fgCustomScheme').style.display = this.value === 'other' ? 'block' : 'none';
});

function previewToko() {
  document.getElementById('pvNama').textContent   = document.getElementById('tNama').value||'(Nama Toko)';
  document.getElementById('pvAlamat').textContent = document.getElementById('tAlamat').value||'';
  const telp = document.getElementById('tTelp').value;
  document.getElementById('pvTelp').textContent   = telp?'📞 '+telp:'';
  document.getElementById('pvKertas').textContent = `🖨️ Kertas ${document.getElementById('tKertas').value||'58'}mm`;
}

async function simpanPengaturan() {
  const nama = document.getElementById('tNama').value.trim();
  if (!nama) { showToast('⚠️ Nama toko tidak boleh kosong!'); return; }
  // Tentukan printer app scheme
  let printerScheme = document.getElementById('tPrinterApp').value;
  let printerName = document.getElementById('tPrinterApp').options[document.getElementById('tPrinterApp').selectedIndex].text;
  if (printerScheme === 'other') {
    printerScheme = document.getElementById('tCustomScheme').value.trim().toLowerCase() || 'rawbt';
    printerName = printerScheme;
  }
  const data = {
    nama_toko: nama,
    alamat: document.getElementById('tAlamat').value.trim(),
    telp: document.getElementById('tTelp').value.trim(),
    pesan_struk: document.getElementById('tPesan').value.trim()||'Terima kasih sudah berbelanja!',
    ukuran_kertas: document.getElementById('tKertas').value,
    printer_app_scheme: printerScheme,
    printer_app_name: printerName
  };
  await api('/api/pengaturan','POST', data);
  Object.assign(toko, data);
  updateLogo(); updatePrintCSS();
  closeM('mPengaturan');
  showToast(`✅ Pengaturan toko disimpan ke SQLite!`);
}

// ══════════════════════════════════

//  MODAL & TOAST
// ══════════════════════════════════
function openM(id){document.getElementById(id).classList.add('show');}
function closeM(id){document.getElementById(id).classList.remove('show');}
document.querySelectorAll('.overlay').forEach(m=>{
  m.addEventListener('click',e=>{if(e.target===m)m.classList.remove('show');});
});
function showLoading(v){document.getElementById('loading').classList.toggle('hide',!v);}
let tt;
function showToast(msg){
  const el=document.getElementById('toast');
  el.textContent=msg; el.classList.add('show');
  clearTimeout(tt); tt=setTimeout(()=>el.classList.remove('show'),3000);
}

// ══════════════════════════════════

//  THEME TOGGLE
// ══════════════════════════════════
function applyThemeUI(isLight) {
  const btn = document.getElementById('btnTheme');
  const tog = document.getElementById('themeToggle');
  const lbl = document.getElementById('drawerThemeLabel');
  // Pakai ikon Lucide agar konsisten (emoji diganti, bukan textContent)
  if (btn) {
    btn.innerHTML = `<i data-lucide="${isLight ? 'sun' : 'moon'}" class="ic"></i>`;
    if (window.lucide) lucide.createIcons();
  }
  if (tog) tog.checked = isLight;
  if (lbl) lbl.textContent = isLight ? 'Mode Gelap' : 'Mode Terang';
}

function toggleTheme() {
  const isLight = document.documentElement.classList.toggle('light');
  localStorage.setItem('theme', isLight ? 'light' : 'dark');
  applyThemeUI(isLight);
}

// ══════════════════════════════════

//  MOBILE NAV
// ══════════════════════════════════
function mobView(view) {
  const right = document.querySelector('.right');
  const isMob = window.innerWidth <= 768;
  if (!isMob) return;
  if (view === 'keranjang') {
    right.classList.add('mob-show');
    document.getElementById('bn-kasir').classList.remove('active');
    document.getElementById('bn-keranjang').classList.add('active');
  } else {
    right.classList.remove('mob-show');
    document.getElementById('bn-keranjang').classList.remove('active');
    document.getElementById('bn-kasir').classList.add('active');
  }
}

// Setelah transaksi sukses → kembali ke kasir di mobile
function mobAfterTrx() {
  if (window.innerWidth <= 768) mobView('kasir');
}

function openDrawer() {
  document.getElementById('drawer').classList.add('open');
  document.getElementById('drawerOverlay').classList.add('show');
}

function closeDrawer() {
  document.getElementById('drawer').classList.remove('open');
  document.getElementById('drawerOverlay').classList.remove('show');
}

function togglePgMenu(e) {
  e.stopPropagation();
  document.getElementById('pgMenu').classList.toggle('show');
}
function closePgMenu() {
  document.getElementById('pgMenu').classList.remove('show');
}
document.addEventListener('click', () => closePgMenu());

function toggleDrawerPg() {
  const sub = document.getElementById('drawerPgSub');
  const arr = document.getElementById('dnArr');
  arr.textContent = sub.classList.toggle('open') ? '▾' : '▸';
}

// ══════════════════════════════════

//  UTILS
// ══════════════════════════════════
const fRp  = n => 'Rp '+Math.round(n).toLocaleString('id-ID');
const fRpS = n => n>=1000?(n/1000)+'rb':n;
const pRp  = s => parseInt(s.replace(/[^0-9]/g,''))||0;


// ══════════════════════════════════

//  PIUTANG (PELUNASAN CICILAN)
// ══════════════════════════════════
async function openPiutang() {
  openM('mPiutang');
  await muatPiutang();
  await muatReminderPiutang();
}

async function muatPiutang() {
  const cari = document.getElementById('piutangCari')?.value || '';
  showLoading(true);
  try {
    const data = await api(`/api/piutang?cari=${encodeURIComponent(cari)}`);
    renderPiutangList(data);
    updatePiutangStats(data);
  } catch(e) {
    showToast('❌ ' + e.message);
  }
  showLoading(false);
}

function renderPiutangList(data) {
  const el = document.getElementById('piutangList');
  if (!data.length) {
    el.innerHTML = `<div style="text-align:center;color:var(--muted);padding:40px">
      <div style="font-size:48px;margin-bottom:12px">✅</div>
      <div>Tidak ada piutang belum lunas</div>
    </div>`;
    return;
  }
  
  el.innerHTML = data.map(p => {
    const tgl = new Date(p.waktu).toLocaleDateString('id-ID', {day:'numeric',month:'short',year:'2-digit'});
    const hariLewat = Math.floor((new Date() - new Date(p.waktu)) / (1000*60*60*24));
    const warningClass = hariLewat > 30 ? 'style="color:var(--red)"' : '';
    const warningBadge = hariLewat > 30 ? `<span style="background:var(--red);color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;margin-left:8px">${hariLewat} hari</span>` : '';
    
    return `
    <div style="background:var(--surface2);border:1px solid var(--border);border-radius:12px;padding:14px;margin-bottom:12px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">
        <div>
          <div style="font-weight:700;font-size:15px">${p.no_trx} ${warningBadge}</div>
          <div style="font-size:12px;color:var(--muted)">${tgl} • ${p.pelanggan_nama || 'Tanpa Nama'}</div>
        </div>
        <div style="text-align:right">
          <div style="font-size:18px;font-weight:800;color:var(--red)">${fRp(p.sisa_real || p.sisa_piutang)}</div>
          <div style="font-size:11px;color:var(--muted)">Sisa Piutang</div>
        </div>
      </div>
      
      <div style="display:flex;gap:16px;margin-bottom:12px;font-size:12px">
        <div><span style="color:var(--muted)">Total:</span> <b>${fRp(p.total)}</b></div>
        <div><span style="color:var(--muted)">Terbayar:</span> <b style="color:var(--green)">${fRp(p.total_bayar || 0)}</b></div>
        <div><span style="color:var(--muted)">Telpon:</span> <b>${p.pelanggan_telp || '-'}</b></div>
      </div>
      
      <div style="display:flex;gap:8px">
        <button class="mbtn pri" style="flex:1" onclick="openBayarPiutang(${p.id}, '${p.no_trx}', ${p.total}, ${p.total_bayar || 0}, ${p.sisa_real || p.sisa_piutang})">💰 Bayar</button>
        <button class="mbtn sec" onclick="lihatHistoryPiutang(${p.id})">📝 History</button>
      </div>
    </div>`;
  }).join('');
}

function updatePiutangStats(data) {
  const totalCount = data.length;
  const totalNominal = data.reduce((s, p) => s + (p.sisa_real || p.sisa_piutang), 0);
  const jatuhTempo = data.filter(p => {
    const hari = Math.floor((new Date() - new Date(p.waktu)) / (1000*60*60*24));
    return hari > 30;
  }).length;
  
  document.getElementById('piutangTotalCount').textContent = totalCount;
  document.getElementById('piutangTotalNominal').textContent = fRp(totalNominal);
  document.getElementById('piutangJatuhTempo').textContent = jatuhTempo;
}

async function muatReminderPiutang() {
  try {
    const data = await api('/api/piutang/reminder?hari=30');
    const el = document.getElementById('piutangReminder');
    const txt = document.getElementById('piutangReminderText');
    
    if (data.total_piutang > 0) {
      el.style.display = 'block';
      txt.textContent = `${data.total_piutang} piutang >30 hari (total ${fRp(data.total_nominal)})`;
    } else {
      el.style.display = 'none';
    }
  } catch(e) {
    console.error('Gagal muat reminder:', e);
  }
}

function filterPiutangJatuhTempo() {
  // Filter list untuk hanya tampilkan yang >30 hari
  document.getElementById('piutangCari').value = '';
  muatPiutangJatuhTempo();
}

async function muatPiutangJatuhTempo() {
  showLoading(true);
  try {
    const data = await api('/api/piutang/reminder?hari=30');
    renderPiutangList(data.piutang_list);
    updatePiutangStats(data.piutang_list);
  } catch(e) {
    showToast('❌ ' + e.message);
  }
  showLoading(false);
}

async function openBayarPiutang(trxId, noTrx, total, terbayar, sisa) {
  document.getElementById('bpTrxId').value = trxId;
  document.getElementById('bpSubtitle').textContent = `No. Transaksi: ${noTrx}`;
  document.getElementById('bpTotal').textContent = fRp(total);
  document.getElementById('bpTerbayar').textContent = fRp(terbayar);
  document.getElementById('bpSisa').textContent = fRp(sisa);
  document.getElementById('bpNominal').value = '';
  document.getElementById('bpCatatan').value = '';
  document.getElementById('btnBayarPiutang').disabled = true;
  
  // Muat history
  await muatHistoryBayar(trxId);
  
  openM('mBayarPiutang');
}

async function muatHistoryBayar(trxId) {
  try {
    const data = await api(`/api/piutang/${trxId}/history`);
    const el = document.getElementById('bpHistory');
    
    if (!data.history.length) {
      el.innerHTML = '<div style="text-align:center;color:var(--muted);padding:8px">Belum ada pembayaran</div>';
      return;
    }
    
    el.innerHTML = data.history.map(h => {
      const tgl = new Date(h.waktu).toLocaleString('id-ID', {day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'});
      return `<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border2)">
        <div>
          <div style="font-weight:600">${fRp(h.nominal)}</div>
          <div style="font-size:11px;color:var(--muted)">${tgl} • ${h.metode_bayar}</div>
        </div>
        <div style="font-size:11px;color:var(--muted)">${h.dibuat_oleh}</div>
      </div>`;
    }).join('');
  } catch(e) {
    document.getElementById('bpHistory').innerHTML = '<div style="text-align:center;color:var(--muted);padding:8px">Gagal memuat history</div>';
  }
}

function setBpNominal(value) {
  if (value === 'sisa') {
    const sisaText = document.getElementById('bpSisa').textContent;
    document.getElementById('bpNominal').value = parseInt(sisaText.replace(/[^0-9]/g, '')) || 0;
  } else {
    document.getElementById('bpNominal').value = value;
  }
  validasiBayarPiutang();
}

function validasiBayarPiutang() {
  const nominal = parseInt(document.getElementById('bpNominal').value) || 0;
  const sisaText = document.getElementById('bpSisa').textContent;
  const sisa = parseInt(sisaText.replace(/[^0-9]/g, '')) || 0;
  
  const btn = document.getElementById('btnBayarPiutang');
  btn.disabled = nominal <= 0 || nominal > sisa;
  
  if (nominal > sisa) {
    btn.textContent = '⚠️ Melebihi Sisa';
  } else if (nominal === sisa) {
    btn.textContent = '💰 Bayar Lunas';
  } else {
    btn.textContent = '💰 Bayar';
  }
}

async function prosesBayarPiutang() {
  const trxId = document.getElementById('bpTrxId').value;
  const nominal = parseInt(document.getElementById('bpNominal').value) || 0;
  const metode = document.getElementById('bpMetode').value;
  const catatan = document.getElementById('bpCatatan').value.trim();

  if (!nominal || nominal <= 0) {
    showToast('❌ Nominal harus lebih dari 0');
    return;
  }

  // Idempotency key: dibuat sekali per klik agar double-submit tidak bayar 2x
  if (!window._bpIdemKey) window._bpIdemKey = 'bp-' + Date.now() + '-' + Math.random().toString(36).slice(2);
  const idemKey = window._bpIdemKey;

  showLoading(true);
  try {
    const result = await api(`/api/piutang/${trxId}/bayar`, 'POST', {
      nominal,
      metode_bayar: metode,
      catatan,
      idempotency_key: idemKey
    });
    window._bpIdemKey = null; // sukses → key baru untuk pembayaran berikutnya

    if (result.is_lunas) {
      showToast('✅ Piutang telah lunas!');
    } else {
      showToast(`✅ Pembayaran ${fRp(nominal)} tersimpan. Sisa: ${fRp(result.sisa_piutang)}`);
    }

    closeM('mBayarPiutang');
    await muatPiutang();
    await muatReminderPiutang();
  } catch(e) {
    // 409 duplikat = klik ganda yang sudah tertangani server
    if (e.status === 409 && e.body && e.body.duplikat) {
      window._bpIdemKey = null;
      showToast('ℹ️ Pembayaran sudah diproses sebelumnya');
      closeM('mBayarPiutang');
      await muatPiutang();
    } else {
      showToast('❌ ' + e.message);
    }
  }
  showLoading(false);
}

async function lihatHistoryPiutang(trxId) {
  // Buka modal bayar tapi readonly (bisa untuk lihat history)
  showLoading(true);
  try {
    const data = await api(`/api/piutang/${trxId}/history`);
    const p = data.transaksi;
    openBayarPiutang(trxId, p.no_trx, p.total, data.total_bayar, p.sisa_piutang);
  } catch(e) {
    showToast('❌ ' + e.message);
  }
  showLoading(false);
}

// ══════════════════════════════════

//  PELANGGAN
// ══════════════════════════════════
let plgMode = 'kelola'; // 'kelola' | 'pilih' | 'pilih_piutang'

function openPelanggan(mode = 'kelola') {
  plgMode = mode;
  const titles = {
    'pilih': '👤 Pilih Pelanggan',
    'pilih_piutang': '👤 Pilih Pelanggan (Piutang)',
    'kelola': '👥 Pelanggan'
  };
  document.getElementById('plgModalTitle').textContent = titles[mode] || '👥 Pelanggan';
  plgGoList();
  openM('mPelanggan');
}

function plgGoList() {
  document.getElementById('plgVList').style.display   = '';
  document.getElementById('plgVForm').style.display   = 'none';
  document.getElementById('plgVDetail').style.display = 'none';
  document.getElementById('plgBackBtn').style.display = 'none';
  const titles = {
    'pilih': '👤 Pilih Pelanggan',
    'pilih_piutang': '👤 Pilih Pelanggan (Piutang)',
    'kelola': '👥 Pelanggan'
  };
  document.getElementById('plgModalTitle').textContent = titles[plgMode] || '👥 Pelanggan';
  muatPelanggan();
}

function plgGoForm(id = null) {
  document.getElementById('plgVList').style.display   = 'none';
  document.getElementById('plgVForm').style.display   = '';
  document.getElementById('plgVDetail').style.display = 'none';
  document.getElementById('plgBackBtn').style.display = '';
  document.getElementById('plgEditId').value  = id || '';
  document.getElementById('plgModalTitle').textContent = id ? '✏️ Edit Pelanggan' : '➕ Tambah Pelanggan';

  if (!id) {
    ['plgNama','plgTelp','plgAlamat','plgCatatan'].forEach(i => document.getElementById(i).value = '');
  }
}

async function plgGoDetail(id) {
  document.getElementById('plgVList').style.display   = 'none';
  document.getElementById('plgVForm').style.display   = 'none';
  document.getElementById('plgVDetail').style.display = '';
  document.getElementById('plgBackBtn').style.display = '';

  showLoading(true);
  const data = await api(`/api/pelanggan/${id}`);
  showLoading(false);
  const plg = data.pelanggan;
  const st  = data.stats;

  document.getElementById('plgModalTitle').textContent = plg.nama;
  document.getElementById('plgDetailInfo').innerHTML = `
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
      <div class="plg-avatar" style="width:48px;height:48px;font-size:18px;">${plg.nama[0].toUpperCase()}</div>
      <div>
        <div style="font-size:15px;font-weight:700;">${plg.nama}</div>
        <div style="font-size:12px;color:var(--muted);">${plg.telepon || '—'}</div>
        <div style="font-size:12px;color:var(--muted);">${plg.alamat || ''}</div>
      </div>
      <div style="margin-left:auto;display:flex;gap:6px;">
        <button class="bed" onclick="plgEditLoad(${plg.id})">✏️ Edit</button>
        <button class="bdl" onclick="hapusPelanggan(${plg.id})">🗑</button>
      </div>
    </div>
    <div class="plg-stat-row">
      <div class="plg-stat">
        <div class="plg-stat-val">${st.total_trx}</div>
        <div class="plg-stat-lbl">Transaksi</div>
      </div>
      <div class="plg-stat">
        <div class="plg-stat-val">${fRp(st.total_belanja)}</div>
        <div class="plg-stat-lbl">Total Belanja</div>
      </div>
    </div>
    ${plg.catatan ? `<div style="margin-top:10px;font-size:12px;color:var(--muted);font-style:italic">📝 ${plg.catatan}</div>` : ''}
  `;

  const trxEl = document.getElementById('plgDetailTrx');
  if (!data.transaksi.length) {
    trxEl.innerHTML = '<div style="text-align:center;color:var(--muted);padding:16px;font-size:13px">Belum ada transaksi</div>';
    return;
  }
  trxEl.innerHTML = data.transaksi.map(t => {
    const tgl = new Date(t.waktu).toLocaleString('id-ID', {day:'numeric',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'});
    return `
      <div class="plg-trx-item">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <div>
            <div class="plg-trx-no">${t.no_trx} · ${tgl}</div>
            <div class="plg-trx-val">${fRp(t.total)}</div>
          </div>
          <div style="font-size:11px;color:var(--muted);text-align:right">
            ${t.bayar > t.total ? `<div style="color:var(--green)">Kembalian ${fRp(t.kembalian)}</div>` : ''}
          </div>
        </div>
      </div>`;
  }).join('');
}

async function plgEditLoad(id) {
  showLoading(true);
  const data = await api(`/api/pelanggan/${id}`);
  showLoading(false);
  const plg = data.pelanggan;
  document.getElementById('plgNama').value    = plg.nama;
  document.getElementById('plgTelp').value    = plg.telepon;
  document.getElementById('plgAlamat').value  = plg.alamat;
  document.getElementById('plgCatatan').value = plg.catatan;
  plgGoForm(id);
}

async function muatPelanggan() {
  const cari = document.getElementById('plgCari')?.value || '';
  const data = await api(`/api/pelanggan?cari=${encodeURIComponent(cari)}`);
  const el   = document.getElementById('plgList');

  if (!data.length) {
    el.innerHTML = `<div style="text-align:center;color:var(--muted);padding:24px;font-size:13px">
      ${cari ? 'Pelanggan tidak ditemukan' : 'Belum ada pelanggan — klik "+ Tambah"'}
    </div>`;
    return;
  }

  el.innerHTML = data.map(p => {
    const inisial = p.nama[0].toUpperCase();
    const subinfo = [p.telepon, p.total_trx > 0 ? `${p.total_trx}x transaksi` : ''].filter(Boolean).join(' · ');
    if (plgMode === 'pilih' || plgMode === 'pilih_piutang') {
      return `
        <div class="plg-item clickable" onclick="pilihPelanggan(${p.id}, '${p.nama.replace(/'/g,"\\'")}')">
          <div class="plg-avatar">${inisial}</div>
          <div class="plg-info">
            <div class="plg-nama">${p.nama}</div>
            <div class="plg-sub">${subinfo || '—'}</div>
          </div>
          <span style="font-size:12px;color:var(--accent);font-weight:600;">Pilih →</span>
        </div>`;
    }
    return `
      <div class="plg-item clickable" onclick="plgGoDetail(${p.id})">
        <div class="plg-avatar">${inisial}</div>
        <div class="plg-info">
          <div class="plg-nama">${p.nama}</div>
          <div class="plg-sub">${subinfo || '—'}</div>
        </div>
        <div class="plg-acts">
          <span style="font-size:11px;color:var(--muted)">${fRp(p.total_belanja)}</span>
        </div>
      </div>`;
  }).join('');
}

async function simpanPelanggan() {
  const nama = document.getElementById('plgNama').value.trim();
  if (!nama) { showToast('⚠️ Nama pelanggan wajib diisi'); return; }
  const id   = document.getElementById('plgEditId').value;
  const body = {
    nama,
    telepon  : document.getElementById('plgTelp').value.trim(),
    alamat   : document.getElementById('plgAlamat').value.trim(),
    catatan  : document.getElementById('plgCatatan').value.trim()
  };
  showLoading(true);
  try {
    if (id) {
      await api(`/api/pelanggan/${id}`, 'PUT', body);
      showToast('✅ Data pelanggan diperbarui');
    } else {
      try {
        await api('/api/pelanggan', 'POST', body);
      } catch(e) {
        // 409 = nama duplikat: tawarkan tambah paksa
        if (e.status === 409 && e.body && e.body.butuh_force) {
          const daftar = (e.body.duplikat || []).map(p => `- ${p.nama}${p.telepon ? ' (' + p.telepon + ')' : ''}`).join('\n');
          if (confirm(`Nama "${nama}" sudah ada:\n${daftar}\n\nTetap tambah sebagai pelanggan baru?`)) {
            await api('/api/pelanggan', 'POST', Object.assign({force: true}, body));
          } else { showLoading(false); return; }
        } else { throw e; }
      }
      showToast('✅ Pelanggan ditambahkan');
    }
    plgGoList();
  } catch(e) {
    showToast('❌ ' + e.message);
  }
  showLoading(false);
}

async function hapusPelanggan(id) {
  if (!confirm('Hapus pelanggan ini? Riwayat transaksinya tetap tersimpan.')) return;
  showLoading(true);
  try {
    await api(`/api/pelanggan/${id}`, 'DELETE');
    showToast('🗑 Pelanggan dihapus');
    plgGoList();
  } catch(e) {
    // mis. 400 saat masih ada piutang aktif
    showToast('❌ ' + e.message);
  }
  showLoading(false);
}

function pilihPelanggan(id, nama) {
  // Mode piutang - isi input di form piutang
  if (plgMode === 'pilih_piutang') {
    piutangPelangganId = id;
    const piutangNama = document.getElementById('piutangNama');
    if (piutangNama) piutangNama.value = nama;
    const selectedPlgId = document.getElementById('selectedPlgId');
    if (selectedPlgId) selectedPlgId.value = id;
    closeM('mPelanggan');
    showToast(`👤 Pelanggan dipilih: ${nama}`);
    return;
  }
  
  // Mode biasa (pilih untuk transaksi reguler)
  document.getElementById('selectedPlgId').value = id;
  const inputPelanggan = document.getElementById('inputPelanggan');
  if (inputPelanggan) inputPelanggan.value = nama;
  closeM('mPelanggan');
  showToast(`👤 Pelanggan: ${nama}`);
}

function clearPelanggan() {
  document.getElementById('selectedPlgId').value = '';
  const inputPelanggan = document.getElementById('inputPelanggan');
  if (inputPelanggan) inputPelanggan.value = '';
  // Reset piutang fields
  piutangPelangganId = null;
  const piutangNama = document.getElementById('piutangNama');
  if (piutangNama) piutangNama.value = '';
}

// ══════════════════════════════════

//  MANAJEMEN PENGGUNA (pemilik only)
// ══════════════════════════════════
async function openPengguna() {
  openM('mPengguna');
  await muatPengguna();
}

async function muatPengguna() {
  showLoading(true);
  const list = await api('/api/pengguna');
  showLoading(false);
  if (!list) return;
  const currentId = APP_USER.id;
  document.getElementById('pgList').innerHTML = list.map(u => {
    const isOwner = u.role === 'pemilik';
    const isSelf  = u.id === currentId;
    return `
    <div class="pg-item">
      <div class="pg-avatar ${isOwner ? 'owner' : 'staff'}">${u.nama[0].toUpperCase()}</div>
      <div class="pg-info">
        <div class="pg-nama">${u.nama} <span class="role-pill ${isOwner ? 'owner' : 'staff'}">${isOwner ? '👑 Pemilik' : '👤 Karyawan'}</span>${isSelf ? ' <span style="font-size:10px;color:var(--muted)">(Saya)</span>' : ''}</div>
        <div class="pg-sub">@${u.username} · ${u.aktif ? 'Aktif' : '<span style="color:var(--red)">Nonaktif</span>'}</div>
      </div>
      <div style="display:flex;gap:5px;flex-shrink:0;">
        <button class="bed" onclick="resetPassPengguna(${u.id},'${u.nama.replace(/'/g,"\\'")}')">🔑 Reset</button>
        ${!isSelf ? `<button class="bdl" onclick="hapusPenggunaEl(${u.id},'${u.nama.replace(/'/g,"\\'")}')">🗑</button>` : ''}
      </div>
    </div>`;
  }).join('') || '<div style="text-align:center;color:var(--muted);padding:20px">Tidak ada pengguna</div>';
}

async function tambahPengguna() {
  const username = document.getElementById('pgUsername').value.trim();
  const nama     = document.getElementById('pgNama').value.trim();
  const password = document.getElementById('pgPassword').value;
  const role     = document.getElementById('pgRole').value;
  if (!username || !nama || !password) { showToast('⚠️ Lengkapi semua field!'); return; }
  showLoading(true);
  try {
    await api('/api/pengguna', 'POST', { username, nama, password, role });
    ['pgUsername','pgNama','pgPassword'].forEach(id => document.getElementById(id).value = '');
    await muatPengguna();
    showToast(`✅ Pengguna ${nama} ditambahkan`);
  } catch(e) { showToast('❌ ' + e.message); }
  showLoading(false);
}

async function hapusPenggunaEl(id, nama) {
  if (!confirm(`Nonaktifkan akun "${nama}"?`)) return;
  showLoading(true);
  await api(`/api/pengguna/${id}`, 'DELETE');
  await muatPengguna();
  showToast(`🗑 Akun ${nama} dinonaktifkan`);
  showLoading(false);
}

function resetPassPengguna(id, nama) {
  const pass = prompt(`Reset password untuk ${nama}:\n(minimal 6 karakter)`);
  if (!pass) return;
  if (pass.length < 6) { showToast('⚠️ Password minimal 6 karakter'); return; }
  showLoading(true);
  api(`/api/pengguna/${id}/reset-password`, 'POST', { password: pass })
    .then(() => { showToast(`✅ Password ${nama} berhasil direset`); showLoading(false); })
    .catch(e => { showToast('❌ ' + e.message); showLoading(false); });
}

// ═══════════════════════════════════════════════════════════════

//  SUPERADMIN PANEL (MULTI-TENANT)
// ═══════════════════════════════════════════════════════════════
let superadminCurrentTab = 'stores';
let superadminStores = [];
let superadminOwners = [];

function initSuperadmin() {
  // Cek apakah user adalah superadmin
  if (APP_USER && APP_USER.is_superadmin) {
    document.getElementById('mSuperadmin').style.display = '';
    loadStoreSwitcher();
  }
}

function openSuperadminPanel() {
  openM('mSuperadmin');
  switchSuperadminTab('stores');
  checkGhostMode();
}

function switchSuperadminTab(tab) {
  superadminCurrentTab = tab;
  
  // Update tab buttons
  ['Stores', 'Owners', 'CreateStore', 'CreateOwner', 'Logs'].forEach(t => {
    document.getElementById('saTab' + t).classList.toggle('active', t.toLowerCase() === tab.toLowerCase());
  });
  
  // Update panels
  document.getElementById('saPanelStores').style.display = tab === 'stores' ? 'block' : 'none';
  document.getElementById('saPanelOwners').style.display = tab === 'owners' ? 'block' : 'none';
  document.getElementById('saPanelCreateStore').style.display = tab === 'createStore' ? 'block' : 'none';
  document.getElementById('saPanelCreateOwner').style.display = tab === 'createOwner' ? 'block' : 'none';
  document.getElementById('saPanelLogs').style.display = tab === 'logs' ? 'block' : 'none';
  
  // Load data
  if (tab === 'stores') loadSuperadminStores();
  if (tab === 'owners') loadSuperadminOwners();
  if (tab === 'createStore') loadOwnersForSelect();
  if (tab === 'logs') loadSuperadminLogs();
}

async function loadSuperadminStores() {
  showLoading(true);
  try {
    const stores = await api('/api/admin/stores');
    superadminStores = stores;
    const el = document.getElementById('superadminStoresList');
    
    if (!stores.length) {
      el.innerHTML = '<div style="text-align:center;color:var(--muted);padding:40px;">Belum ada toko</div>';
    } else {
      el.innerHTML = stores.map(s => `
        <div style="background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px;margin-bottom:10px;">
          <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:8px;">
            <div>
              <div style="font-weight:700;font-size:15px;">${s.name}</div>
              <div style="font-size:12px;color:var(--muted);">@${s.slug}</div>
            </div>
            <span style="background:${s.is_active ? 'var(--green)' : 'var(--red)'};color:#111;font-size:10px;font-weight:700;padding:3px 8px;border-radius:6px;">${s.is_active ? 'AKTIF' : 'NONAKTIF'}</span>
          </div>
          <div style="font-size:12px;color:var(--muted);margin-bottom:8px;">
            👤 Pemilik: ${s.owner_name || '-'}<br>
            📍 ${s.address || '-'}<br>
            📞 ${s.phone || '-'}<br>
            📦 ${s.product_count || 0} produk · 🛒 ${s.transaction_count || 0} transaksi
          </div>
          <div style="display:flex;gap:8px;">
            <button class="mbtn pri" style="flex:1;padding:8px;font-size:12px;" onclick="enterGhostMode(${s.id}, '${s.name.replace(/'/g, "\\'")}')">
              <span>👻</span> Masuk
            </button>
            <button class="mbtn" style="padding:8px;font-size:12px;background:var(--blue);color:#fff;" onclick="openEditStoreSuperadmin(${s.id})">
              ✏️ Edit
            </button>
          </div>
        </div>
      `).join('');
    }
  } catch(e) {
    showToast('[ERR] Gagal memuat toko: ' + e.message);
  }
  showLoading(false);
}

async function openEditStoreSuperadmin(storeId) {
  const store = superadminStores.find(s => s.id === storeId);
  if (!store) return;
  
  // Load owners list untuk dropdown
  await loadOwnersForEditStore();
  
  document.getElementById('saEditStoreId').value = store.id;
  document.getElementById('saEditStoreName').value = store.name || '';
  document.getElementById('saEditStoreSlug').value = store.slug || '';
  document.getElementById('saEditStoreAddress').value = store.address || '';
  document.getElementById('saEditStorePhone').value = store.phone || '';
  document.getElementById('saEditStoreEmail').value = store.email || '';
  document.getElementById('saEditStoreStatus').value = store.is_active ? '1' : '0';
  document.getElementById('saEditStoreOwner').value = store.owner_id || '';
  
  openM('mEditTokoSuperadmin');
}

async function loadOwnersForEditStore() {
  try {
    const owners = await api('/api/admin/owners');
    const select = document.getElementById('saEditStoreOwner');
    select.innerHTML = '<option value="">-- Pilih Pemilik --</option>' + 
      owners.map(o => `<option value="${o.id}">${o.nama} (${o.username})</option>`).join('');
  } catch(e) {
    console.error('Gagal load owners:', e);
  }
}

function openResetPasswordOwner(ownerId, nama, username) {
  document.getElementById('saResetOwnerId').value = ownerId;
  document.getElementById('saResetOwnerNama').textContent = nama;
  document.getElementById('saResetOwnerUsername').textContent = '@' + username;
  document.getElementById('saResetOwnerPassword').value = '';
  openM('mResetPasswordOwner');
}

async function saveResetPasswordOwner() {
  const ownerId = document.getElementById('saResetOwnerId').value;
  const password = document.getElementById('saResetOwnerPassword').value.trim();
  
  if (!password) {
    showToast('⚠️ Password baru wajib diisi');
    return;
  }
  if (password.length < 6) {
    showToast('⚠️ Password minimal 6 karakter');
    return;
  }
  
  showLoading(true);
  try {
    await api(`/api/admin/owners/${ownerId}/reset-password`, 'POST', {password});
    showToast('✅ Password pemilik berhasil direset');
    closeM('mResetPasswordOwner');
  } catch(e) {
    showToast('❌ ' + e.message);
  }
  showLoading(false);
}

async function saveEditStoreSuperadmin() {
  const storeId = document.getElementById('saEditStoreId').value;
  const data = {
    name: document.getElementById('saEditStoreName').value.trim(),
    slug: document.getElementById('saEditStoreSlug').value.trim(),
    owner_id: parseInt(document.getElementById('saEditStoreOwner').value) || null,
    address: document.getElementById('saEditStoreAddress').value.trim(),
    phone: document.getElementById('saEditStorePhone').value.trim(),
    email: document.getElementById('saEditStoreEmail').value.trim(),
    is_active: parseInt(document.getElementById('saEditStoreStatus').value)
  };
  
  if (!data.name) {
    showToast('[WARN] Nama toko wajib diisi');
    return;
  }
  
  if (!data.slug) {
    showToast('[WARN] Slug wajib diisi');
    return;
  }
  
  if (!data.owner_id) {
    showToast('[WARN] Pemilik toko wajib dipilih');
    return;
  }
  
  showLoading(true);
  try {
    await api(`/api/admin/stores/${storeId}`, 'PUT', data);
    showToast('[OK] Toko berhasil diupdate');
    closeM('mEditTokoSuperadmin');
    loadSuperadminStores();
  } catch(e) {
    showToast('[ERR] ' + e.message);
  }
  showLoading(false);
}

async function loadSuperadminOwners() {
  showLoading(true);
  try {
    const owners = await api('/api/admin/owners');
    superadminOwners = owners;
    const el = document.getElementById('superadminOwnersList');
    
    if (!owners.length) {
      el.innerHTML = '<div style="text-align:center;color:var(--muted);padding:40px;">Belum ada pemilik</div>';
    } else {
      el.innerHTML = owners.map(o => `
        <div style="background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px;margin-bottom:10px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <div style="font-weight:700;font-size:15px;">${o.nama}</div>
              <div style="font-size:12px;color:var(--muted);">@${o.username} · ${o.store_count} toko</div>
            </div>
            <div style="display:flex;gap:8px;align-items:center;">
              <span style="background:${o.aktif ? 'var(--green)' : 'var(--red)'};color:#111;font-size:10px;font-weight:700;padding:3px 8px;border-radius:6px;">${o.aktif ? 'AKTIF' : 'NONAKTIF'}</span>
              <button onclick="openResetPasswordOwner(${o.id}, '${o.nama}', '${o.username}')" style="background:var(--accent);color:#111;border:none;padding:6px 12px;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer;" title="Reset Password">🔑 Reset Password</button>
            </div>
          </div>
        </div>
      `).join('');
    }
  } catch(e) {
    showToast('❌ Gagal memuat pemilik: ' + e.message);
  }
  showLoading(false);
}

async function loadOwnersForSelect() {
  try {
    const owners = await api('/api/admin/owners');
    const select = document.getElementById('saStoreOwner');
    select.innerHTML = '<option value="">Pilih pemilik...</option>' + 
      owners.map(o => `<option value="${o.id}">${o.nama} (@${o.username})</option>`).join('');
  } catch(e) {
    console.error('Gagal load owners:', e);
  }
}

async function loadSuperadminLogs() {
  showLoading(true);
  try {
    const logs = await api('/api/admin/logs');
    const el = document.getElementById('superadminLogsList');
    
    if (!logs.length) {
      el.innerHTML = '<div style="text-align:center;color:var(--muted);padding:40px;">Belum ada log</div>';
    } else {
      el.innerHTML = logs.map(l => `
        <div style="border-bottom:1px solid var(--border);padding:10px 0;">
          <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted);">
            <span>${new Date(l.dibuat).toLocaleString('id-ID')}</span>
            <span>${l.admin_name}</span>
          </div>
          <div style="font-size:13px;margin-top:4px;">
            <strong>${l.action_type}</strong> ${l.store_name ? '· ' + l.store_name : ''}
          </div>
        </div>
      `).join('');
    }
  } catch(e) {
    showToast('❌ Gagal memuat logs: ' + e.message);
  }
  showLoading(false);
}

async function createStore() {
  const name = document.getElementById('saStoreName').value.trim();
  const ownerId = document.getElementById('saStoreOwner').value;
  const address = document.getElementById('saStoreAddress').value.trim();
  const phone = document.getElementById('saStorePhone').value.trim();
  
  if (!name) { showToast('❌ Nama toko wajib diisi'); return; }
  if (!ownerId) { showToast('❌ Pemilik wajib dipilih'); return; }
  
  showLoading(true);
  try {
    await api('/api/admin/stores', 'POST', { name, owner_id: ownerId, address, phone });
    showToast('✅ Toko berhasil dibuat');
    document.getElementById('saStoreName').value = '';
    document.getElementById('saStoreAddress').value = '';
    document.getElementById('saStorePhone').value = '';
    switchSuperadminTab('stores');
  } catch(e) {
    showToast('❌ ' + e.message);
  }
  showLoading(false);
}

async function createOwner() {
  const username = document.getElementById('saOwnerUsername').value.trim().toLowerCase();
  const nama = document.getElementById('saOwnerNama').value.trim();
  const password = document.getElementById('saOwnerPassword').value;
  
  if (!username || !nama || !password) { showToast('❌ Semua field wajib diisi'); return; }
  if (password.length < 6) { showToast('❌ Password minimal 6 karakter'); return; }
  
  showLoading(true);
  try {
    await api('/api/admin/owners', 'POST', { username, nama, password });
    showToast('✅ Pemilik berhasil dibuat');
    document.getElementById('saOwnerUsername').value = '';
    document.getElementById('saOwnerNama').value = '';
    document.getElementById('saOwnerPassword').value = '';
    switchSuperadminTab('owners');
  } catch(e) {
    showToast('❌ ' + e.message);
  }
  showLoading(false);
}

async function enterGhostMode(storeId, storeName) {
  showLoading(true);
  try {
    await api(`/api/admin/enter-store/${storeId}`, 'POST');
    showToast(`[OK] Masuk ke toko: ${storeName}, refresh halaman...`);
    closeM('mSuperadmin');
    // Refresh halaman untuk update nama toko dan semua data
    setTimeout(() => location.reload(), 500);
  } catch(e) {
    showToast('[ERR] ' + e.message);
    showLoading(false);
  }
}

async function exitGhostMode() {
  showLoading(true);
  try {
    await api('/api/admin/exit-store', 'POST');
    showToast('[OK] Keluar dari toko, refresh halaman...');
    // Refresh halaman untuk update nama toko dan semua data
    setTimeout(() => location.reload(), 500);
  } catch(e) {
    showToast('[ERR] ' + e.message);
    showLoading(false);
  }
}

function checkGhostMode() {
  // Cek apakah sedang ghost mode (dari session)
  // Ini akan dihandle oleh backend, tapi kita bisa cek dari data yang diload
}

// ═══════════════════════════════════════════════════════════════

//  STORE SWITCHER (UNTUK PEMILIK DENGAN MULTIPLE TOKO)
// ═══════════════════════════════════════════════════════════════
function loadStoreSwitcher() {
  if (!APP_USER) return;
  
  // Gunakan APP_STORES dari backend atau fetch dari API
  const stores = APP_STORES || [];
  
  if (stores.length > 1 || APP_USER.is_superadmin) {
    const container = document.getElementById('storeSwitcherContainer');
    const select = document.getElementById('storeSwitcher');
    
    container.style.display = 'block';
    select.innerHTML = stores.map(s => 
      `<option value="${s.id}">${s.name}</option>`
    ).join('');
  }
}

async function switchStore(storeId) {
  showLoading(true);
  try {
    await api(`/api/switch-store/${storeId}`, 'POST');
    showToast('[OK] Berhasil pindah toko, refresh halaman...');
    // Refresh halaman untuk update nama toko dan semua data
    setTimeout(() => location.reload(), 500);
  } catch(e) {
    showToast('[ERR] ' + e.message);
    showLoading(false);
  }
}

// Init saat halaman load
document.addEventListener('DOMContentLoaded', initSuperadmin);

// ══════════════════════════════════

//  GANTI PASSWORD SENDIRI
// ══════════════════════════════════
function openGantiPassword() {
  document.getElementById('gpNamaUser').textContent = APP_USER.nama;
  ['gpLama','gpBaru','gpKonfirm'].forEach(id => document.getElementById(id).value = '');
  openM('mGantiPassword');
}

async function simpanGantiPassword() {
  const lama   = document.getElementById('gpLama').value;
  const baru   = document.getElementById('gpBaru').value;
  const konfirm= document.getElementById('gpKonfirm').value;
  if (!lama || !baru) { showToast('⚠️ Semua field wajib diisi'); return; }
  if (baru.length < 6) { showToast('⚠️ Password baru minimal 6 karakter'); return; }
  if (baru !== konfirm) { showToast('⚠️ Konfirmasi password tidak cocok'); return; }
  showLoading(true);
  try {
    await api('/api/pengguna/ganti-password', 'POST', { password_lama: lama, password_baru: baru });
    closeM('mGantiPassword');
    showToast('✅ Password berhasil diganti');
  } catch(e) { showToast('❌ ' + e.message); }
  showLoading(false);
}

// ══════════════════════════════════

//  SERVICE WORKER REGISTRATION
// ══════════════════════════════════
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then(reg => {
        console.log('SW registered:', reg.scope);
        // Force update check
        reg.update();
        // Jika ada SW baru, langsung pakai
        if (reg.installing) {
          console.log('SW installing...');
        }
        reg.addEventListener('updatefound', () => {
          const newWorker = reg.installing;
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              console.log('New SW installed, reloading...');
              window.location.reload();
            }
          });
        });
      })
      .catch(err => console.warn('SW failed:', err));
  });
}
