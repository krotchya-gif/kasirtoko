// static/js/produk.js — pindahan murni dari templates/index.html (split Fase 5).
// Global bersama (api, showToast, openM, fRp, ...) tetap window-scope.

//  KATEGORI & PRODUK
// ══════════════════════════════════
async function muatKategori() {
  const kats = await api('/api/produk/kategori');
  const tabs = ['Semua', ...kats];
  document.getElementById('katTabs').innerHTML = tabs.map(k=>
    `<button class="tab ${k===katAktif?'active':''}" onclick="setKat('${k}')">${k}</button>`).join('');
  document.getElementById('katDL').innerHTML = kats.map(k=>`<option value="${k}">`).join('');
}

async function muatProduk() {
  const q    = document.getElementById('cari').value;
  const list = await api(`/api/produk?kategori=${encodeURIComponent(katAktif)}&cari=${encodeURIComponent(q)}&limit=200`);
  renderProduk(list);
}

function filterProduk() { muatProduk(); }

function setKat(k) {
  katAktif = k;
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.textContent===k));
  muatProduk();
}

function safeEmoji(e) {
  if (!e || !e.trim()) return '📦';
  // Reject plain ASCII / curly-quote junk (", ", «, etc.)
  if (/^[\x00-\x7F\u2018-\u201F\u00AB\u00BB]+$/.test(e.trim())) return '📦';
  return e.trim();
}

function renderProduk(list) {
  const g = document.getElementById('produkGrid');
  if (!list.length) { g.innerHTML='<div class="no-res">😔 Produk tidak ditemukan</div>'; return; }

  // Tampilkan info jumlah produk jika banyak
  const infoBar = list.length >= 200
    ? `<div style="grid-column:1/-1;background:rgba(245,166,35,.1);border:1px solid var(--accent);border-radius:8px;padding:8px 12px;font-size:12px;color:var(--accent);margin-bottom:4px">
        ⚠️ Menampilkan 200 produk pertama. Gunakan pencarian atau filter kategori untuk menemukan produk lain.
       </div>`
    : '';

  g.innerHTML = infoBar + list.map(p=>{
    const lowThresh = (p.stok_min > 0) ? p.stok_min : 5;
    const isLow = p.stok > 0 && p.stok <= lowThresh;
    const stockLabel = p.stok===0 ? '❌ Habis' : isLow ? `⚠️ Sisa ${p.stok}` : `Stok: ${p.stok}`;
    const disBadge = p.diskon > 0 ? `<span class="dis-badge">${p.diskon}%</span>` : '';
    const origPrice = p.diskon > 0 ? `<span class="ph-coret">${fRp(Math.round(p.harga/(1-p.diskon/100)))}</span>` : '';
    return `
    <div class="pcard ${p.stok===0?'habis':''}"
         data-id="${p.id}"
         data-nama="${encodeURIComponent(p.nama)}"
         data-harga="${p.harga}"
         data-emoji="${encodeURIComponent(safeEmoji(p.emoji))}"
         data-stok="${p.stok}"
         onclick="addToCartEl(this)">
      ${disBadge}
      <span class="pe">${safeEmoji(p.emoji)}</span>
      <div class="pn">${p.nama}</div>
      <div class="ph">${origPrice}${fRp(p.harga)}</div>
      <div class="ps ${isLow?'low':''}">${stockLabel}</div>
    </div>`;
  }).join('');
}

function addToCartEl(el) {
  const id    = parseInt(el.dataset.id);
  const nama  = decodeURIComponent(el.dataset.nama);
  const harga = parseInt(el.dataset.harga);
  const emoji = decodeURIComponent(el.dataset.emoji);
  const stok  = parseInt(el.dataset.stok);
  addToCart(id, nama, harga, emoji, stok);
}

// ══════════════════════════════════

//  BARCODE SCANNER (html5-qrcode)
// ══════════════════════════════════
let _html5QrCode = null;
let _scanMode = 'kasir'; // 'kasir' atau 'form'

// Mode kasir: tambah ke keranjang
function openBarcodeScanner() {
  _scanMode = 'kasir';
  document.getElementById('manualBarcode').value = '';
  openM('mBarcode');
  startBarcodeScan();
}

// Mode form: isi field barcode
function openBarcodeScannerForForm() {
  _scanMode = 'form';
  document.getElementById('manualBarcode').value = '';
  openM('mBarcode');
  startBarcodeScan();
}

function closeBarcodeScanner() {
  stopBarcodeScan();
  closeM('mBarcode');
}

async function startBarcodeScan() {
  const status = document.getElementById('scanner-status');
  const container = document.getElementById('scanner-container');
  
  // Reset
  await stopBarcodeScan();
  
  // Cek support kamera
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    status.textContent = '⚠️ Browser tidak support kamera. Gunakan input manual.';
    status.style.background = 'rgba(255,193,7,0.9)';
    status.style.color = '#000';
    return;
  }
  
  status.textContent = '📷 Memulai scanner...';
  status.style.background = 'rgba(0,0,0,0.6)';
  status.style.color = '#fff';
  
  try {
    // Gunakan html5-qrcode jika tersedia, atau fallback ke BarcodeDetector
    if (typeof Html5Qrcode !== 'undefined') {
      await startHtml5QrCode();
    } else if ('BarcodeDetector' in window) {
      await startBarcodeDetector();
    } else {
      status.textContent = '⚠️ Scanner tidak tersedia. Gunakan input manual.';
    }
  } catch(e) {
    console.error('Scanner error:', e);
    status.textContent = '❌ ' + e.message + '. Gunakan input manual.';
    status.style.background = 'rgba(220,53,69,0.9)';
  }
}

async function startHtml5QrCode() {
  const status = document.getElementById('scanner-status');
  
  _html5QrCode = new Html5Qrcode('scanner-container');
  
  const config = { 
    fps: 10, 
    qrbox: { width: 250, height: 150 },
    aspectRatio: 1.333
  };
  
  status.textContent = '📷 Meminta akses kamera...';
  
  await _html5QrCode.start(
    { facingMode: 'environment' },
    config,
    (decodedText, decodedResult) => {
      // Barcode terdeteksi
      status.textContent = '✅ Barcode: ' + decodedText;
      stopBarcodeScan();
      processBarcode(decodedText);
    },
    (errorMessage) => {
      // Scan error (biasanya no code found, ignore)
    }
  );
  
  status.textContent = '📷 Arahkan kamera ke barcode...';
}

async function startBarcodeDetector() {
  const status = document.getElementById('scanner-status');
  const video = document.getElementById('scanner-video');
  
  const barcodeDetector = new BarcodeDetector({ 
    formats: ['ean_13', 'ean_8', 'code_39', 'code_128', 'upc_a', 'upc_e', 'qr_code'] 
  });
  
  const stream = await navigator.mediaDevices.getUserMedia({ 
    video: { facingMode: 'environment', width: 1280, height: 720 }
  });
  
  video.srcObject = stream;
  
  await new Promise((resolve) => {
    video.onloadedmetadata = () => {
      video.play();
      resolve();
    };
  });
  
  status.textContent = '📷 Arahkan kamera ke barcode...';
  
  const scanFrame = async () => {
    if (!video.srcObject) return;
    try {
      const barcodes = await barcodeDetector.detect(video);
      if (barcodes.length > 0) {
        const barcode = barcodes[0].rawValue;
        status.textContent = '✅ Barcode: ' + barcode;
        video.srcObject.getTracks().forEach(t => t.stop());
        video.srcObject = null;
        await processBarcode(barcode);
        return;
      }
    } catch(e) {}
    requestAnimationFrame(scanFrame);
  };
  
  scanFrame();
}

async function stopBarcodeScan() {
  if (_html5QrCode) {
    try {
      await _html5QrCode.stop();
      await _html5QrCode.clear();
    } catch(e) {}
    _html5QrCode = null;
  }
  
  const video = document.getElementById('scanner-video');
  if (video && video.srcObject) {
    video.srcObject.getTracks().forEach(t => t.stop());
    video.srcObject = null;
  }
}

async function processBarcode(barcode) {
  if (!barcode) return;
  
  // Mode form: langsung isi field barcode, tidak perlu cek ke server
  if (_scanMode === 'form') {
    document.getElementById('fBarcode').value = barcode;
    closeM('mBarcode');
    stopBarcodeScan();
    showToast('✅ Barcode: ' + barcode);
    return;
  }
  
  // Mode kasir: cari produk dan tambah ke keranjang
  showLoading(true);
  try {
    const produk = await api(`/api/produk/scan/${encodeURIComponent(barcode)}`);
    
    if (produk.error) {
      showToast('❌ Produk dengan barcode ' + barcode + ' tidak ditemukan');
      startBarcodeScan();
    } else {
      addToCart(produk);
      closeM('mBarcode');
      stopBarcodeScan();
      showToast(`✅ ${produk.nama} ditambahkan ke keranjang`);
    }
  } catch(e) {
    showToast('❌ Error: ' + e.message);
    startBarcodeScan();
  }
  showLoading(false);
}

function submitManualBarcode() {
  const barcode = document.getElementById('manualBarcode').value.trim();
  if (barcode) {
    processBarcode(barcode);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const manualInput = document.getElementById('manualBarcode');
  if (manualInput) {
    manualInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') submitManualBarcode();
    });
  }
});

// ══════════════════════════════════

//  TAMBAH / EDIT PRODUK
// ══════════════════════════════════
//  TAMBAH / EDIT PRODUK
// ══════════════════════════════════
function renderEmojiPicker() {
  const cats = Object.keys(EMOJI_CATS);
  const list = EMOJI_CATS[emojiCat] || [];
  const tabs = cats.map(c =>
    `<div class="epick-cat${c===emojiCat?' sel':''}" onclick="setEmojiCat('${c}')">${c}</div>`
  ).join('');
  const grid = list.map(e =>
    `<div class="epe${e===emojiSel?' sel':''}" onclick="pilihEmoji('${e}')">${e}</div>`
  ).join('');
  document.getElementById('epick').innerHTML =
    `<div class="epick-cats">${tabs}</div><div style="display:flex;flex-wrap:wrap;gap:5px;">${grid}</div>`;
}
function setEmojiCat(c) { emojiCat = c; renderEmojiPicker(); }
function pilihEmoji(e) {
  emojiSel=e; document.querySelectorAll('.epe').forEach(el=>el.classList.toggle('sel',el.textContent===e));
}

function openTambah() {
  document.getElementById('fTitle').textContent='➕ Tambah Produk Baru';
  document.getElementById('fSub').textContent='Isi detail produk baru';
  document.getElementById('fEId').value='';
  ['fNama','fKat','fHarga','fStok','fHModal','fStokMin','fDiskon','fBarcode'].forEach(id=>document.getElementById(id).value='');
  emojiSel='📦'; renderEmojiPicker();
  openM('mProduk');
}

function generateRandomBarcode() {
  // Generate 12 digit random barcode (compatible dengan EAN13)
  const prefix = '2'; // 2 adalah prefix untuk internal use
  const random = Math.floor(Math.random() * 10000000000).toString().padStart(10, '0');
  const code12 = prefix + random;
  
  // Calculate EAN13 check digit
  let sum = 0;
  for (let i = 0; i < 12; i++) {
    sum += parseInt(code12[i]) * (i % 2 === 0 ? 1 : 3);
  }
  const checkDigit = (10 - (sum % 10)) % 10;
  const code13 = code12 + checkDigit;
  
  document.getElementById('fBarcode').value = code13;
  showToast('✅ Barcode generated: ' + code13);
}

async function simpanProduk() {
  const nama       = document.getElementById('fNama').value.trim();
  const kat        = document.getElementById('fKat').value.trim();
  const harga      = parseInt(document.getElementById('fHarga').value)||0;
  const stok       = parseInt(document.getElementById('fStok').value)||0;
  const harga_modal= parseInt(document.getElementById('fHModal').value)||0;
  const stok_min   = parseInt(document.getElementById('fStokMin').value)||0;
  const diskon     = Math.min(100, Math.max(0, parseInt(document.getElementById('fDiskon').value)||0));
  const barcode    = document.getElementById('fBarcode').value.trim();
  const eid        = document.getElementById('fEId').value;
  if (!nama||!kat||harga<=0) { showToast('⚠️ Lengkapi semua field!'); return; }
  const body = {nama, kategori:kat, harga, stok, emoji:emojiSel, harga_modal, stok_min, diskon, barcode};
  showLoading(true);
  try {
    let saved;
    if (eid) { saved = await api(`/api/produk/${eid}`,'PUT',body); showToast(`✅ ${nama} diperbarui`); }
    else     { saved = await api('/api/produk','POST',body);        showToast(`✅ ${nama} ditambahkan!`); }
    closeM('mProduk');
    await muatKategori(); await muatProduk();
    // Refresh kelola list jika modal masih terbuka
    if (kelolaData.length) {
      if (eid) kelolaData = kelolaData.map(p => p.id === saved.id ? saved : p);
      else     kelolaData.push(saved);
      _buildKelolaTabs();
      filterKelola();
    }
  } catch(e) { showToast('❌ Gagal: '+e.message); }
  showLoading(false);
}

// ══════════════════════════════════

//  KELOLA PRODUK
// ══════════════════════════════════
let kelolaData = [];
let kelolaKat  = 'Semua';

async function openKelola() {
  showLoading(true);
  kelolaData = await api('/api/produk?limit=2000');
  kelolaKat  = 'Semua';
  document.getElementById('kelolaSearch').value = '';
  document.getElementById('kelolaSort').value   = 'nama_az';
  _buildKelolaTabs();
  filterKelola();
  showLoading(false);
  openM('mKelola');
}

function _buildKelolaTabs() {
  const kats = ['Semua', ...new Set(kelolaData.map(p => p.kategori).sort((a,b)=>a.localeCompare(b,'id')))];
  document.getElementById('kelolaTabs').innerHTML = kats.map(k => {
    const cnt = k === 'Semua' ? kelolaData.length : kelolaData.filter(p=>p.kategori===k).length;
    return `<button class="tab ${k===kelolaKat?'active':''}" data-kat="${k}" onclick="setKelolaKat('${k}')">${k} <span style="opacity:.65">(${cnt})</span></button>`;
  }).join('');
}

function setKelolaKat(kat) {
  kelolaKat = kat;
  document.querySelectorAll('#kelolaTabs .tab').forEach(b => b.classList.toggle('active', b.dataset.kat === kat));
  filterKelola();
}

function filterKelola() {
  const q    = document.getElementById('kelolaSearch').value.toLowerCase().trim();
  const sort = document.getElementById('kelolaSort').value;

  let list = kelolaKat === 'Semua' ? kelolaData : kelolaData.filter(p => p.kategori === kelolaKat);
  if (q) list = list.filter(p => p.nama.toLowerCase().includes(q) || p.kategori.toLowerCase().includes(q));

  list = [...list].sort((a, b) => {
    switch (sort) {
      case 'nama_az':    return a.nama.localeCompare(b.nama, 'id');
      case 'nama_za':    return b.nama.localeCompare(a.nama, 'id');
      case 'harga_asc':  return a.harga - b.harga;
      case 'harga_desc': return b.harga - a.harga;
      case 'stok_asc':   return a.stok  - b.stok;
      case 'stok_desc':  return b.stok  - a.stok;
      case 'margin_desc': {
        const ma = a.harga_modal > 0 ? (a.harga - a.harga_modal) / a.harga_modal : -999;
        const mb = b.harga_modal > 0 ? (b.harga - b.harga_modal) / b.harga_modal : -999;
        return mb - ma;
      }
      default: return 0;
    }
  });

  const total = kelolaKat === 'Semua' ? kelolaData.length : kelolaData.filter(p=>p.kategori===kelolaKat).length;
  document.getElementById('kelolaInfo').textContent =
    list.length === total
      ? `${total} produk`
      : `${list.length} dari ${total} produk${q ? ` · "${q}"` : ''}`;

  _renderKelolaList(list);
}

function _renderKelolaList(list) {
  if (!list.length) {
    document.getElementById('kelolaList').innerHTML =
      '<div style="text-align:center;color:var(--muted);padding:28px;font-size:13px">😔 Tidak ada produk ditemukan</div>';
    return;
  }
  document.getElementById('kelolaList').innerHTML = list.map(p=>{
    const margin = p.harga_modal > 0 ? Math.round((p.harga - p.harga_modal) / p.harga_modal * 100) : null;
    const marginChip = margin !== null
      ? `<span class="margin-chip ${margin<0?'neg':''}">${margin>=0?'+':''}${margin}%</span>` : '';
    const lowThresh = p.stok_min > 0 ? p.stok_min : 5;
    const stokWarn  = (p.stok <= lowThresh && p.stok >= 0)
      ? `<span class="stok-min-chip">⚠️ ${p.stok}</span>` : '';
    const disLabel  = p.diskon > 0
      ? ` <span style="font-size:10px;color:var(--red);font-weight:700">${p.diskon}% OFF</span>` : '';
    return `
    <div class="mpi">
      <span class="mpe">${p.emoji||'📦'}</span>
      <div class="mpinf">
        <div class="mpn">${p.nama} <span style="font-size:10px;color:var(--muted)">[${p.kategori}]</span>${disLabel}</div>
        <div class="mph">${fRp(p.harga)}${p.harga_modal>0?` <span style="font-size:10px;color:var(--muted)">modal: ${fRp(p.harga_modal)}</span>`:''}${marginChip}</div>
        <div class="mps">Stok: ${p.stok}${stokWarn}${p.stok_min>0?` (min: ${p.stok_min})`:''}</div>
      </div>
      <button class="bed"
        data-id="${p.id}" data-nama="${encodeURIComponent(p.nama)}"
        data-kat="${encodeURIComponent(p.kategori)}" data-harga="${p.harga}"
        data-stok="${p.stok}" data-emoji="${encodeURIComponent(p.emoji||'📦')}"
        data-hmodal="${p.harga_modal||0}" data-stokmin="${p.stok_min||0}" data-diskon="${p.diskon||0}"
        onclick="editProdukEl(this)">✏️ Edit</button>
      ${APP_USER && APP_USER.role === 'pemilik' ? `
        <button class="bed" style="border-color:var(--purple);color:var(--purple);" 
          data-id="${p.id}" data-nama="${encodeURIComponent(p.nama)}" data-kat="${encodeURIComponent(p.kategori)}"
          data-stok="${p.stok}" data-emoji="${encodeURIComponent(p.emoji||'📦')}"
          onclick="adjustStokEl(this)">⚖️ Stok</button>
        ${p.barcode ? `<button class="bed" style="border-color:var(--green);color:var(--green);" 
          onclick="quickPreviewBarcode('${p.barcode}', '${encodeURIComponent(p.nama)}')">🏷️</button>` : ''}
        <button class="bdl" data-id="${p.id}" data-nama="${encodeURIComponent(p.nama)}" onclick="hapusProdukEl(this)">🗑</button>
      ` : ''}
    </div>`;
  }).join('');
}

function editProdukEl(el) {
  editProduk(
    el.dataset.id,
    decodeURIComponent(el.dataset.nama),
    decodeURIComponent(el.dataset.kat),
    el.dataset.harga,
    el.dataset.stok,
    decodeURIComponent(el.dataset.emoji),
    el.dataset.hmodal || 0,
    el.dataset.stokmin || 0,
    el.dataset.diskon || 0,
    decodeURIComponent(el.dataset.barcode || '')
  );
}

async function hapusProdukEl(el) {
  hapusProduk(el.dataset.id, decodeURIComponent(el.dataset.nama));
}

function adjustStokEl(el) {
  const produk = {
    id: parseInt(el.dataset.id),
    nama: decodeURIComponent(el.dataset.nama),
    kategori: decodeURIComponent(el.dataset.kat),
    stok: parseInt(el.dataset.stok),
    emoji: decodeURIComponent(el.dataset.emoji)
  };
  openAdjustStok(produk);
}

async function quickPreviewBarcode(barcode, namaEncoded) {
  const nama = decodeURIComponent(namaEncoded);
  showLoading(true);
  try {
    const res = await fetch('/api/barcode/generate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({code: barcode, format: 'code128'})
    });
    
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.error || 'Gagal generate barcode');
    }
    
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    
    document.getElementById('barcodePreviewTitle').textContent = nama;
    document.getElementById('barcodePreviewImg').src = url;
    document.getElementById('barcodePreviewCode').textContent = barcode;
    document.getElementById('barcodeDownloadLink').href = url;
    document.getElementById('barcodeDownloadLink').download = `barcode-${barcode}.png`;
    
    openM('mBarcodePreview');
  } catch(e) {
    showToast('❌ ' + e.message);
  }
  showLoading(false);
}

function editProduk(id, nama, kat, harga, stok, emoji, hmodal=0, stokmin=0, diskon=0, barcode='') {
  document.getElementById('fTitle').textContent='✏️ Edit Produk';
  document.getElementById('fSub').textContent='Perbarui detail produk';
  document.getElementById('fEId').value=id;
  document.getElementById('fNama').value=nama;
  document.getElementById('fKat').value=kat;
  document.getElementById('fHarga').value=harga;
  document.getElementById('fStok').value=stok;
  document.getElementById('fHModal').value=hmodal||'';
  document.getElementById('fStokMin').value=stokmin||'';
  document.getElementById('fDiskon').value=diskon||'';
  document.getElementById('fBarcode').value=barcode||'';
  emojiSel=emoji; renderEmojiPicker();
  closeM('mKelola'); openM('mProduk');
}

async function hapusProduk(id, nama) {
  if (!confirm(`Hapus produk "${nama}"?`)) return;
  showLoading(true);
  await api(`/api/produk/${id}`,'DELETE');
  showToast(`🗑 ${nama} dihapus`);
  // Hapus dari cache lokal lalu re-render tanpa close modal
  kelolaData = kelolaData.filter(p => p.id !== parseInt(id));
  _buildKelolaTabs();
  filterKelola();
  await muatKategori(); await muatProduk();
  showLoading(false);
}

// ══════════════════════════════════

//  ADJUST STOK MANUAL
// ══════════════════════════════════
let adjustCurrentStok = 0;
let adjustCurrentProduk = null;

function openAdjustStok(produk) {
  adjustCurrentProduk = produk;
  adjustCurrentStok = produk.stok;
  
  document.getElementById('adjustProdukId').value = produk.id;
  document.getElementById('adjustEmoji').textContent = produk.emoji || '📦';
  document.getElementById('adjustNamaProduk').textContent = produk.nama;
  document.getElementById('adjustKategori').textContent = produk.kategori;
  document.getElementById('adjustStokSaatIni').textContent = produk.stok;
  document.getElementById('adjustStokBaru').value = produk.stok;
  document.getElementById('adjustAlasan').value = '';
  document.getElementById('adjustKeterangan').value = '';
  
  hitungSelisihAdjust();
  openM('mAdjustStok');
}

function hitungSelisihAdjust() {
  const baru = parseInt(document.getElementById('adjustStokBaru').value) || 0;
  const selisih = baru - adjustCurrentStok;
  const el = document.getElementById('adjustSelisih');
  
  if (selisih === 0) {
    el.textContent = '-';
    el.style.color = 'var(--muted)';
  } else if (selisih > 0) {
    el.textContent = '+' + selisih;
    el.style.color = 'var(--green)';
  } else {
    el.textContent = selisih;
    el.style.color = 'var(--red)';
  }
}

async function prosesAdjustStok() {
  const id = document.getElementById('adjustProdukId').value;
  const stokBaru = parseInt(document.getElementById('adjustStokBaru').value);
  const alasan = document.getElementById('adjustAlasan').value;
  const keterangan = document.getElementById('adjustKeterangan').value.trim();
  
  if (isNaN(stokBaru) || stokBaru < 0) {
    showToast('⚠️ Stok baru tidak valid');
    return;
  }
  if (stokBaru === adjustCurrentStok) {
    showToast('⚠️ Tidak ada perubahan stok');
    return;
  }
  if (!alasan) {
    showToast('⚠️ Pilih alasan adjust');
    return;
  }
  
  showLoading(true);
  try {
    await api(`/api/produk/${id}/adjust-stok`, 'POST', {
      stok_baru: stokBaru,
      alasan: alasan,
      keterangan: keterangan
    });
    showToast('✅ Stok berhasil di-adjust');
    closeM('mAdjustStok');
    await muatProduk();
    // Refresh kelola list jika terbuka
    if (kelolaData.length) {
      await openKelola();
    }
  } catch(e) {
    showToast('❌ ' + e.message);
  }
  showLoading(false);
}

// ══════════════════════════════════

//  BARCODE GENERATOR
// ══════════════════════════════════
let barcodeData = [];
let selectedBarcodeItems = new Set();

async function openBarcodeGenerator() {
  openM('mBarcodeGen');
  await muatBarcodeList();
}

async function muatBarcodeList() {
  showLoading(true);
  try {
    // Ambil semua produk yang punya barcode
    const produk = await api('/api/produk?limit=2000');
    barcodeData = produk.filter(p => p.barcode && p.barcode.trim() !== '');
    
    // Populate kategori filter
    const kats = [...new Set(barcodeData.map(p => p.kategori))].sort();
    const katSelect = document.getElementById('barcodeKatFilter');
    katSelect.innerHTML = '<option value="">Semua Kategori</option>' + 
      kats.map(k => `<option value="${k}">${k}</option>`).join('');
    
    selectedBarcodeItems.clear();
    updateBarcodeSelection();
    renderBarcodeList();
  } catch(e) {
    console.error('Error loading barcode list:', e);
  }
  showLoading(false);
}

function renderBarcodeList() {
  const filter = document.getElementById('barcodeFilter').value.toLowerCase();
  const katFilter = document.getElementById('barcodeKatFilter').value;
  const el = document.getElementById('barcodeList');
  
  let filtered = barcodeData;
  if (filter) {
    filtered = filtered.filter(p => p.nama.toLowerCase().includes(filter) || p.barcode.includes(filter));
  }
  if (katFilter) {
    filtered = filtered.filter(p => p.kategori === katFilter);
  }
  
  if (!filtered.length) {
    el.innerHTML = '<div style="text-align:center;color:var(--muted);padding:24px;">Tidak ada produk dengan barcode</div>';
    return;
  }
  
  el.innerHTML = filtered.map(p => {
    const isChecked = selectedBarcodeItems.has(p.id);
    return `
      <div style="display:flex;align-items:center;gap:12px;padding:12px;background:var(--surface2);border:1px solid var(--border);border-radius:10px;margin-bottom:8px;${isChecked?'border-color:var(--accent);':''}">
        <input type="checkbox" id="bc-${p.id}" value="${p.id}" 
          ${isChecked?'checked':''} onchange="toggleBarcodeItem(${p.id})"
          style="width:20px;height:20px;cursor:pointer;flex-shrink:0;">
        <div style="flex:1;min-width:0;">
          <div style="font-weight:600;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${p.emoji||'📦'} ${p.nama}</div>
          <div style="font-size:11px;color:var(--muted);">${p.kategori} · ${fRp(p.harga)}</div>
        </div>
        <div style="font-family:var(--fh);font-size:14px;font-weight:700;letter-spacing:1px;padding:4px 10px;background:var(--surface);border-radius:6px;border:1px solid var(--border);">${p.barcode}</div>
        <button class="mbtn" style="padding:6px 12px;font-size:11px;background:var(--blue);color:#fff;flex-shrink:0;" onclick="previewBarcode(${p.id})">👁 Preview</button>
      </div>
    `;
  }).join('');
}

function filterBarcodeList() {
  renderBarcodeList();
}

function toggleBarcodeItem(id) {
  if (selectedBarcodeItems.has(id)) {
    selectedBarcodeItems.delete(id);
  } else {
    selectedBarcodeItems.add(id);
  }
  updateBarcodeSelection();
  renderBarcodeList();
}

function toggleSelectAllBarcode() {
  const checked = document.getElementById('selectAllBarcode').checked;
  const filter = document.getElementById('barcodeFilter').value.toLowerCase();
  const katFilter = document.getElementById('barcodeKatFilter').value;
  
  let filtered = barcodeData;
  if (filter) {
    filtered = filtered.filter(p => p.nama.toLowerCase().includes(filter) || p.barcode.includes(filter));
  }
  if (katFilter) {
    filtered = filtered.filter(p => p.kategori === katFilter);
  }
  
  if (checked) {
    filtered.forEach(p => selectedBarcodeItems.add(p.id));
  } else {
    filtered.forEach(p => selectedBarcodeItems.delete(p.id));
  }
  
  updateBarcodeSelection();
  renderBarcodeList();
}

function updateBarcodeSelection() {
  document.getElementById('barcodeSelectedCount').textContent = `${selectedBarcodeItems.size} dipilih`;
}

async function previewBarcode(id) {
  const produk = barcodeData.find(p => p.id === id);
  if (!produk) return;
  
  showLoading(true);
  try {
    const res = await fetch('/api/barcode/generate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({code: produk.barcode, format: 'code128'})
    });
    
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.error || 'Gagal generate barcode');
    }
    
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    
    document.getElementById('barcodePreviewTitle').textContent = produk.nama;
    document.getElementById('barcodePreviewImg').src = url;
    document.getElementById('barcodePreviewCode').textContent = produk.barcode;
    document.getElementById('barcodeDownloadLink').href = url;
    document.getElementById('barcodeDownloadLink').download = `barcode-${produk.barcode}.png`;
    
    openM('mBarcodePreview');
  } catch(e) {
    showToast('❌ ' + e.message);
  }
  showLoading(false);
}

async function generateBarcodeSheet() {
  if (selectedBarcodeItems.size === 0) {
    showToast('⚠️ Pilih minimal 1 produk');
    return;
  }
  
  const items = barcodeData
    .filter(p => selectedBarcodeItems.has(p.id))
    .map(p => ({
      id: p.id,
      nama: p.nama,
      barcode: p.barcode,
      harga: p.harga
    }));
  
  showLoading(true);
  try {
    const res = await fetch('/api/barcode/print-sheet', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({items})
    });
    
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.error || 'Gagal generate sheet');
    }
    
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'barcode-sheet.pdf';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    showToast('✅ PDF barcode sheet sedang didownload');
  } catch(e) {
    showToast('❌ ' + e.message);
  }
  showLoading(false);
}

// ══════════════════════════════════

//  STOK LOG / RIWAYAT PERUBAHAN STOK
// ══════════════════════════════════
async function openStokLog() { 
  openM('mStokLog'); 
  const today = new Date().toISOString().split('T')[0];
  if (!document.getElementById('slDari').value) document.getElementById('slDari').value = today;
  if (!document.getElementById('slKe').value) document.getElementById('slKe').value = today;
  await muatStokLog(); 
}

async function muatStokLog() {
  const dari = document.getElementById('slDari').value;
  const ke   = document.getElementById('slKe').value;
  const tipe = document.getElementById('slTipe').value;
  showLoading(true);
  
  let url = `/api/stok-log?dari=${dari}&ke=${ke}&limit=100`;
  if (tipe) url += `&tipe=${tipe}`;
  
  const list = await api(url);
  const el = document.getElementById('slContent');
  
  if (!list.length) {
    el.innerHTML='<div style="color:var(--muted);text-align:center;padding:24px;font-size:14px">Tidak ada riwayat perubahan stok di periode ini</div>';
    showLoading(false); return;
  }
  
  const alasanMap = {
    'stok_fisik': 'Stok Fisik Berbeda',
    'rusak': 'Barang Rusak/Hilang',
    'expired': 'Barang Expired',
    'penyesuaian': 'Penyesuaian Awal',
    'lainnya': 'Lainnya',
    'void_transaksi': 'Void Transaksi',
    'restore_transaksi': 'Restore Transaksi'
  };
  
  const tipeBadge = (tipe) => {
    if (tipe === 'masuk') return `<span style="background:var(--green);color:#111;font-size:10px;font-weight:700;padding:2px 8px;border-radius:6px;">MASUK</span>`;
    if (tipe === 'keluar') return `<span style="background:var(--red);color:#fff;font-size:10px;font-weight:700;padding:2px 8px;border-radius:6px;">KELUAR</span>`;
    return `<span style="background:var(--blue);color:#fff;font-size:10px;font-weight:700;padding:2px 8px;border-radius:6px;">ADJUST</span>`;
  };
  
  el.innerHTML=`
    <div style="max-height:400px;overflow-y:auto;scrollbar-width:thin;scrollbar-color:var(--border) transparent;">
    ${list.map(l=>{
      const wkt = new Date(l.waktu).toLocaleString('id-ID', {day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'});
      return `
      <div class="ri" style="${l.tipe==='masuk'?'border-left:3px solid var(--green);':l.tipe==='keluar'?'border-left:3px solid var(--red);':'border-left:3px solid var(--blue);'}">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="font-size:20px;">${l.produk_emoji||'📦'}</span>
            <span style="font-weight:600;">${l.produk_nama}</span>
          </div>
          ${tipeBadge(l.tipe)}
        </div>
        <div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px;">
          <span style="color:var(--muted);">${wkt} · ${l.dibuat_oleh}</span>
          <span style="font-family:var(--fh);font-weight:700;color:var(--accent);">${l.stok_sebelum} → ${l.stok_sesudah}</span>
        </div>
        <div style="font-size:11px;color:var(--muted);background:var(--surface);padding:6px 10px;border-radius:6px;margin-top:6px;">
          <div><strong>Jumlah:</strong> ${l.tipe==='masuk'?'+':l.tipe==='keluar'?'-':''}${l.jumlah}</div>
          <div><strong>Alasan:</strong> ${alasanMap[l.alasan] || l.alasan}</div>
          ${l.keterangan ? `<div><strong>Ket:</strong> ${l.keterangan}</div>` : ''}
        </div>
      </div>`;
    }).join('')}
    </div>`;
  showLoading(false);
}

// ══════════════════════════════════

//  IMPORT / EXPORT PRODUK
// ══════════════════════════════════
let selectedFile = null;

function openImportExport() {
  switchTab('export');
  resetFile();
  document.getElementById('importResult').style.display = 'none';
  openM('mImportExport');
}

function switchTab(tab) {
  document.getElementById('panelExport').style.display = tab === 'export' ? '' : 'none';
  document.getElementById('panelImport').style.display = tab === 'import' ? '' : 'none';
  document.getElementById('tabExport').classList.toggle('active', tab === 'export');
  document.getElementById('tabImport').classList.toggle('active', tab === 'import');
}

function updateModeUI() {
  const mode = document.querySelector('input[name="modeImport"]:checked').value;
  ['Tambah','Timpa','Ganti'].forEach(m => {
    const lbl = document.getElementById('lbl'+m);
    if (lbl) lbl.style.borderColor = (mode === m.toLowerCase()) ? 'var(--accent)' : 'var(--border)';
  });
  // mode ganti → border merah
  const lblGanti = document.getElementById('lblGanti');
  if (lblGanti) lblGanti.style.borderColor = (mode === 'ganti') ? 'var(--red)' : 'var(--border)';
}

// EXPORT
function exportProdukCSV() {
  window.location.href = '/api/produk/export-csv';
  showToast('✅ File CSV produk sedang didownload...');
}

function downloadTemplate() {
  window.location.href = '/api/produk/template-csv';
  showToast('📄 Template CSV didownload...');
}

// DRAG & DROP
function dragOver(e) {
  e.preventDefault();
  document.getElementById('dropzone').classList.add('dragover');
}
function dragLeave(e) {
  document.getElementById('dropzone').classList.remove('dragover');
}
function dropFile(e) {
  e.preventDefault();
  document.getElementById('dropzone').classList.remove('dragover');
  const f = e.dataTransfer.files[0];
  if (f) setFile(f);
}
function onFileSelected(e) {
  const f = e.target.files[0];
  if (f) setFile(f);
}

function setFile(f) {
  if (!f.name.endsWith('.csv')) { showToast('⚠️ Hanya file .csv yang diterima!'); return; }
  if (f.size > 5 * 1024 * 1024) { showToast('⚠️ File terlalu besar (maks 5MB)!'); return; }
  selectedFile = f;
  document.getElementById('dropText').textContent = '✅ File terpilih';
  const fp = document.getElementById('filePreview');
  fp.style.display = 'flex';
  document.getElementById('fileName').textContent = f.name;
  document.getElementById('fileInfo').textContent = `Ukuran: ${(f.size/1024).toFixed(1)} KB`;
  document.getElementById('btnImport').disabled = false;
  document.getElementById('importResult').style.display = 'none';
}

function resetFile() {
  selectedFile = null;
  document.getElementById('fileInput').value = '';
  document.getElementById('dropText').textContent = 'Klik atau drag & drop file CSV di sini';
  document.getElementById('filePreview').style.display = 'none';
  document.getElementById('btnImport').disabled = true;
  document.getElementById('importResult').style.display = 'none';
}

// IMPORT
async function prosesImport() {
  if (!selectedFile) { showToast('⚠️ Pilih file CSV terlebih dahulu!'); return; }
  const mode = document.querySelector('input[name="modeImport"]:checked').value;

  if (mode === 'ganti') {
    if (!confirm('⚠️ Mode GANTI SEMUA akan menonaktifkan semua produk lama!\nYakin ingin melanjutkan?')) return;
  }

  const fd = new FormData();
  fd.append('file', selectedFile);
  fd.append('mode', mode);

  showLoading(true);
  document.getElementById('btnImport').disabled = true;

  try {
    const res = await fetch('/api/produk/import-csv', { method: 'POST', body: fd });
    const data = await res.json();

    const el = document.getElementById('importResult');
    el.style.display = 'block';

    if (!res.ok || data.error) {
      el.innerHTML = `<div class="ir-err">❌ <strong>Gagal import:</strong> ${data.error || 'Error tidak diketahui'}${
        data.detail ? '<ul style="margin-top:6px;padding-left:16px">' + data.detail.map(e=>`<li>${e}</li>`).join('') + '</ul>' : ''
      }</div>`;
    } else {
      const modeLabel = {tambah:'➕ Tambah Saja', timpa:'🔄 Tambah & Update', ganti:'⚠️ Ganti Semua'}[data.mode];
      el.innerHTML = `
        <div class="ir-ok">
          <div style="font-weight:700;font-size:14px;margin-bottom:8px">✅ Import berhasil! Mode: ${modeLabel}</div>
          <div class="ir-stat">
            <div class="ir-chip" style="color:var(--green)">➕ ${data.tambah} ditambahkan</div>
            <div class="ir-chip" style="color:var(--blue)">🔄 ${data.update} diupdate</div>
            <div class="ir-chip" style="color:var(--muted)">⏭️ ${data.skip} dilewati</div>
            <div class="ir-chip" style="color:var(--accent)">📦 ${data.total_valid} total valid</div>
          </div>
          ${data.error_baris && data.error_baris.length ? `
            <div class="ir-err" style="margin-top:8px">
              ⚠️ <strong>${data.error_baris.length} baris bermasalah:</strong>
              <ul style="margin-top:4px;padding-left:16px">
                ${data.error_baris.slice(0,5).map(e=>`<li>${e}</li>`).join('')}
                ${data.error_baris.length > 5 ? `<li style="color:var(--muted)">...dan ${data.error_baris.length-5} lainnya</li>` : ''}
              </ul>
            </div>` : ''}
        </div>`;
      // Refresh produk dan kategori
      await muatKategori();
      await muatProduk();
      resetFile();
      showToast(`✅ Import selesai: ${data.tambah} ditambah, ${data.update} diupdate`);
    }
  } catch(e) {
    document.getElementById('importResult').innerHTML =
      `<div class="ir-err">❌ <strong>Error koneksi:</strong> ${e.message}</div>`;
    document.getElementById('importResult').style.display = 'block';
  }

  document.getElementById('btnImport').disabled = false;
  showLoading(false);
}

// ══════════════════════════════════
