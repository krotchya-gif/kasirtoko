// static/js/kasir.js — pindahan murni dari templates/index.html (split Fase 5).
// Global bersama (api, showToast, openM, fRp, ...) tetap window-scope.

//  CART
// ══════════════════════════════════
function addToCart(id, nama, harga, emoji, stok) {
  if (stok === 0) return;
  const idx = cart.findIndex(x=>x.id===id);
  if (idx > -1) {
    if (cart[idx].qty >= stok) { showToast('⚠️ Stok tidak cukup!'); return; }
    cart[idx].qty++;
  } else {
    cart.push({id, nama, harga, emoji, stok, qty:1});
  }
  renderCart(); updateSummary(); showToast(`✅ ${nama} +1`);
}

function changeQty(id, d) {
  const idx = cart.findIndex(x=>x.id===id);
  if (idx===-1) return;
  cart[idx].qty += d;
  if (cart[idx].qty <= 0) cart.splice(idx,1);
  else if (cart[idx].qty > cart[idx].stok) { cart[idx].qty=cart[idx].stok; showToast('⚠️ Maks stok!'); }
  renderCart(); updateSummary();
}

function clearCart() { cart=[]; renderCart(); updateSummary(); }

function renderCart() {
  document.getElementById('cartCount').textContent = cart.length;
  // update mobile badges
  const badge = document.getElementById('bnBadge');
  const mobBadge = document.getElementById('mobCartBadge');
  if (badge) { badge.textContent = cart.length; badge.classList.toggle('hidden', cart.length===0); }
  if (mobBadge) { mobBadge.textContent = cart.length; mobBadge.classList.toggle('hidden', cart.length===0); }
  const el = document.getElementById('klist');
  if (!cart.length) {
    el.innerHTML=`<div class="ec"><span class="eico">🛒</span>Keranjang kosong.<br>Pilih produk di kiri.</div>`;
    return;
  }
  el.innerHTML = cart.map(i=>`
    <div class="ki">
      <span class="ie">${i.emoji}</span>
      <div class="ii">
        <div class="in">${i.nama}</div>
        <div class="is">${fRp(i.harga*i.qty)} <span style="color:var(--muted);font-size:10px;font-family:var(--fb)">@${fRp(i.harga)}</span></div>
      </div>
      <div class="qctrl">
        <button class="qb" onclick="changeQty(${i.id},-1)">−</button>
        <span class="qn">${i.qty}</span>
        <button class="qb" onclick="changeQty(${i.id},1)">+</button>
      </div>
    </div>`).join('');
}

// ══════════════════════════════════

//  SUMMARY
// ══════════════════════════════════
function getDiskon(sub) {
  const v = parseFloat(document.getElementById('dVal').value)||0;
  const t = document.getElementById('dType').value;
  return t==='persen' ? Math.round(sub*Math.min(v,100)/100) : Math.min(v,sub);
}

function updateSummary() {
  const sub = cart.reduce((s,i)=>s+i.harga*i.qty,0);
  const cnt = cart.reduce((s,i)=>s+i.qty,0);
  const dis = getDiskon(sub);
  const tot = Math.max(0, sub-dis);
  document.getElementById('subVal').textContent = fRp(sub);
  document.getElementById('icount').textContent = cnt;
  document.getElementById('dAmt').textContent = dis>0?`- ${fRp(dis)}`:'- Rp 0';
  document.getElementById('totVal').textContent = fRp(tot);
  // default bayar = uang pas jika input masih kosong
  const iBayarEl = document.getElementById('iBayar');
  if (!iBayarEl.value && tot > 0) iBayarEl.value = tot;
  else if (tot === 0) iBayarEl.value = '';
  buatQBayar(tot); hitungKem();
  document.getElementById('btnPay').disabled = cart.length===0;
}

function buatQBayar(tot=0) {
  document.getElementById('qBayar').innerHTML =
    [5000,10000,20000,50000,100000,'Pas'].map(p=>{
      if(p==='Pas') return `<button class="qkb" onclick="bayarPas()">💰 Pas</button>`;
      return `<button class="qkb" onclick="setNom(${p})">${fRpS(p)}</button>`;
    }).join('');
}

function setNom(v) {
  const tot = pRp(document.getElementById('totVal').textContent);
  document.getElementById('iBayar').value = Math.ceil(tot/v)*v;
  hitungKem();
}
function bayarPas() { document.getElementById('iBayar').value=pRp(document.getElementById('totVal').textContent); hitungKem(); }
function hitungKem() {
  const tot=pRp(document.getElementById('totVal').textContent);
  const bayar=parseFloat(document.getElementById('iBayar').value)||0;
  const kem=bayar-tot;
  const el=document.getElementById('kemVal');
  el.textContent=fRp(Math.abs(kem));
  el.className=kem>=0?'kp':'kn';
  document.getElementById('btnPay').disabled=cart.length===0||bayar<tot;
}

// ══════════════════════════════════

//  METODE BAYAR
// ══════════════════════════════════
let bayarMetode = 'tunai';
const _METODE_LABEL = {tunai:'💵 Tunai', transfer:'🏦 Transfer', qris:'📱 QRIS', piutang:'⏳ Piutang'};
const _METODE_SHORT = {tunai:'Tunai',    transfer:'Transfer',    qris:'QRIS',    piutang:'Piutang'};
function metodeLabel(m, short=false) { return (short ? _METODE_SHORT : _METODE_LABEL)[m||'tunai'] || 'Tunai'; }

function setBayarMetode(m) {
  // Reset piutang fields jika beralih dari piutang ke metode lain
  if (bayarMetode === 'piutang' && m !== 'piutang') {
    document.getElementById('piutangNama').value = '';
    document.getElementById('piutangBayar').value = '';
    document.getElementById('selectedPlgId').value = '';
    piutangPelangganId = null;
    document.getElementById('piutangPelangganDropdown')?.remove();
  }
  
  bayarMetode = m;
  ['tunai','transfer','qris','piutang'].forEach(k => {
    const id = 'mb' + k.charAt(0).toUpperCase() + k.slice(1);
    const el = document.getElementById(id);
    if (el) el.classList.toggle('active', k === m);
  });
  
  const isTunai = m === 'tunai';
  const isPiutang = m === 'piutang';
  
  // Tampilkan/sembunyikan form piutang
  document.getElementById('piutangForm').style.display = isPiutang ? 'block' : 'none';
  
  // Transfer/QRIS/Piutang: sembunyikan quick bayar, input bayar, kembalian
  document.getElementById('qBayar').style.display  = isTunai ? '' : 'none';
  document.getElementById('bayarSection').style.display = isPiutang ? 'none' : '';
  
  if (isPiutang) {
    // Piutang: update sisa piutang = total
    hitungSisaPiutang();
  } else if (!isTunai) {
    const tot = pRp(document.getElementById('totVal').textContent);
    document.getElementById('iBayar').value = tot;
    hitungKem();
  }
}

function hitungSisaPiutang() {
  const total = pRp(document.getElementById('totVal').textContent);
  const bayar = parseFloat(document.getElementById('piutangBayar').value) || 0;
  const sisa = Math.max(0, total - bayar);
  document.getElementById('sisaPiutangVal').textContent = fRp(sisa);
}

let piutangPelangganId = null;
let _piutangPelangganList = []; // Cache untuk autocomplete

function openPelangganForPiutang() {
  // Buka modal pelanggan dengan mode 'pilih_piutang'
  openPelanggan('pilih_piutang');
}

// Search dan autocomplete untuk nama pelanggan di form piutang
async function onPiutangNamaInput(value) {
  if (!value || value.length < 2) {
    document.getElementById('piutangPelangganDropdown')?.remove();
    return;
  }
  
  // Cari pelanggan via API
  try {
    const data = await api(`/api/pelanggan?cari=${encodeURIComponent(value)}`);
    _piutangPelangganList = data;
    renderPiutangPelangganDropdown(data, value);
  } catch(e) {
    // Silent error - user bisa tetap lanjut dengan nama baru
  }
}

function renderPiutangPelangganDropdown(data, searchValue) {
  // Hapus dropdown lama
  document.getElementById('piutangPelangganDropdown')?.remove();
  
  if (!data.length) return;
  
  const dropdown = document.createElement('div');
  dropdown.id = 'piutangPelangganDropdown';
  dropdown.style.cssText = `
    position: absolute; top: 100%; left: 0; right: 80px; 
    background: var(--surface); border: 1px solid var(--border); 
    border-radius: 8px; margin-top: 4px; max-height: 200px; overflow-y: auto;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 1000;
  `;
  
  dropdown.innerHTML = data.map(p => `
    <div onclick="selectPiutangPelanggan(${p.id}, '${p.nama.replace(/'/g, "\\'")}')" 
         style="padding: 10px 12px; cursor: pointer; border-bottom: 1px solid var(--border2); display: flex; align-items: center; gap: 10px;">
      <div style="width: 32px; height: 32px; border-radius: 50%; background: var(--accent); color: white; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px;">${p.nama[0].toUpperCase()}</div>
      <div style="flex: 1;">
        <div style="font-weight: 600; font-size: 14px;">${p.nama}</div>
        ${p.telepon ? `<div style="font-size: 12px; color: var(--muted);">${p.telepon}</div>` : ''}
      </div>
    </div>
  `).join('');
  
  // Insert setelah input container
  const container = document.getElementById('piutangNama').parentElement;
  container.style.position = 'relative';
  container.appendChild(dropdown);
}

function selectPiutangPelanggan(id, nama) {
  piutangPelangganId = id;
  document.getElementById('piutangNama').value = nama;
  document.getElementById('selectedPlgId').value = id;
  document.getElementById('piutangPelangganDropdown')?.remove();
}

// ══════════════════════════════════

//  INPUT PELANGGAN UMUM (AUTOCOMPLETE)
// ══════════════════════════════════
let _pelangganListCache = [];

async function onInputPelanggan(value) {
  // Reset selected ID saat user ketik ulang
  document.getElementById('selectedPlgId').value = '';
  if (!value || value.length < 2) {
    document.getElementById('pelangganDropdown')?.remove();
    return;
  }
  try {
    const data = await api(`/api/pelanggan?cari=${encodeURIComponent(value)}`);
    _pelangganListCache = data;
    renderPelangganDropdown(data, value);
  } catch(e) {}
}

function renderPelangganDropdown(data, searchValue) {
  document.getElementById('pelangganDropdown')?.remove();
  if (!data.length) return;
  const dropdown = document.createElement('div');
  dropdown.id = 'pelangganDropdown';
  dropdown.style.cssText = `
    position: absolute; top: calc(100% + 4px); left: 0; right: 80px;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 8px; max-height: 200px; overflow-y: auto;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 1000;
  `;
  dropdown.innerHTML = data.map(p => `
    <div onclick="selectInputPelanggan(${p.id}, '${p.nama.replace(/'/g, "\\'")}')"
         style="padding: 10px 12px; cursor: pointer; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 10px;">
      <div style="width: 32px; height: 32px; border-radius: 50%; background: var(--accent); color: #111; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px;">${p.nama[0].toUpperCase()}</div>
      <div style="flex: 1;">
        <div style="font-weight: 600; font-size: 14px;">${p.nama}</div>
        ${p.telepon ? `<div style="font-size: 12px; color: var(--muted);">${p.telepon}</div>` : ''}
      </div>
    </div>
  `).join('');
  const container = document.getElementById('inputPelanggan').parentElement;
  container.style.position = 'relative';
  container.appendChild(dropdown);
}

function selectInputPelanggan(id, nama) {
  document.getElementById('inputPelanggan').value = nama;
  document.getElementById('selectedPlgId').value = id;
  document.getElementById('pelangganDropdown')?.remove();
}

// Tutup dropdown saat klik di luar
document.addEventListener('click', (e) => {
  const ddPiutang = document.getElementById('piutangPelangganDropdown');
  const inputPiutang = document.getElementById('piutangNama');
  if (ddPiutang && !ddPiutang.contains(e.target) && e.target !== inputPiutang) {
    ddPiutang.remove();
  }
  const ddPlg = document.getElementById('pelangganDropdown');
  const inputPlg = document.getElementById('inputPelanggan');
  if (ddPlg && !ddPlg.contains(e.target) && e.target !== inputPlg) {
    ddPlg.remove();
  }
});

// ══════════════════════════════════

//  TRANSAKSI → kirim ke Flask/SQLite
// ══════════════════════════════════
async function prosesTrx() {
  const sub = cart.reduce((s,i)=>s+i.harga*i.qty,0);
  const dis = getDiskon(sub);
  const tot = Math.max(0, sub-dis);
  
  const isPiutang = bayarMetode === 'piutang';
  
  // Validasi piutang - perlu nama pelanggan
  if (isPiutang) {
    const namaPiutang = document.getElementById('piutangNama').value.trim();
    if (!namaPiutang) {
      showToast('❌ Piutang wajib mengisi nama pelanggan!');
      return;
    }
  }
  
  const bayar = isPiutang 
    ? (parseFloat(document.getElementById('piutangBayar').value) || 0)
    : parseFloat(document.getElementById('iBayar').value);
    
  if (!isPiutang && bayar < tot) { 
    showToast('❌ Uang tidak cukup!'); 
    return; 
  }

  const dv = parseFloat(document.getElementById('dVal').value)||0;
  const dt = document.getElementById('dType').value;

  showLoading(true);
  try {
    let plgId = parseInt(document.getElementById('selectedPlgId').value) || null;
    
    // Auto-create pelanggan jika belum ada (nama diketik manual)
    if (!plgId) {
      const namaInput = isPiutang 
        ? document.getElementById('piutangNama').value.trim()
        : document.getElementById('inputPelanggan').value.trim();
      
      if (namaInput) {
        const cacheList = isPiutang ? _piutangPelangganList : _pelangganListCache;
        const existing = Array.isArray(cacheList) && cacheList.find(p => p.nama.toLowerCase() === namaInput.toLowerCase());
        if (existing) {
          plgId = existing.id;
        } else {
          try {
            const newPlg = await api('/api/pelanggan', 'POST', {
              nama: namaInput,
              telepon: '',
              alamat: '',
              catatan: isPiutang ? 'Auto-created dari piutang' : 'Auto-created dari kasir'
            });
            plgId = newPlg.id;
          } catch(e) {
            // 409 = nama sudah ada (cache basi / beda huruf besar-kecil):
            // pakai data server, jangan batalkan transaksi
            if (e.status === 409) {
              const srv = await api(`/api/pelanggan?cari=${encodeURIComponent(namaInput)}`);
              const cocok = Array.isArray(srv) && srv.find(p => p.nama.toLowerCase() === namaInput.toLowerCase());
              if (cocok) { plgId = cocok.id; }
              else { showToast('❌ ' + e.message); showLoading(false); return; }
            } else {
              showToast('❌ Gagal membuat pelanggan: ' + e.message);
              showLoading(false);
              return;
            }
          }
        }
      }
    }
    
    const trx = await api('/api/transaksi','POST', {
      items: cart, subtotal:sub, diskon:dis, diskon_val:dv, diskon_tipe:dt,
      total:tot, bayar, pelanggan_id: plgId, metode_bayar: bayarMetode
    });
    lastTrx = trx;
    renderStrukModal(trx);
    openM('mSukses');
    mobAfterTrx();
    cart=[]; 
    document.getElementById('iBayar').value=''; 
    document.getElementById('piutangBayar').value='';
    document.getElementById('piutangNama').value='';
    document.getElementById('selectedPlgId').value='';
    document.getElementById('dVal').value='';
    piutangPelangganId = null;
    clearPelanggan();
    setBayarMetode('tunai'); // reset metode bayar ke tunai
    renderCart(); updateSummary();
    await muatProduk(); // refresh stok dari DB
  } catch(e) {
    showToast('❌ Gagal menyimpan transaksi: '+e.message);
  }
  showLoading(false);
}

function renderStrukModal(t) {
  const nm = toko.nama_toko||'TOKO';
  const waktuFmt = new Date(t.waktu).toLocaleString('id-ID');
  document.getElementById('struk').innerHTML=`
    <div class="snm">${nm}</div>
    ${toko.alamat?`<div class="ssub">${toko.alamat}</div>`:''}
    ${toko.telp?`<div class="ssub">📞 ${toko.telp}</div>`:''}
    <div class="sdiv"></div>
    <div class="srow"><span>No. Transaksi</span><span>${t.no_trx}</span></div>
    <div class="srow"><span>Waktu</span><span>${waktuFmt}</span></div>
    ${t.pelanggan_nama ? `<div class="srow"><span>Pelanggan</span><span>${t.pelanggan_nama}</span></div>` : ''}
    <div class="sdiv"></div>
    ${t.items.map(i=>`
      <div class="srow"><span>${i.emoji} ${i.nama_produk}</span></div>
      <div class="srow" style="padding-left:10px;color:var(--muted)"><span>${i.qty} × ${fRp(i.harga)}</span><span>${fRp(i.subtotal)}</span></div>`).join('')}
    <div class="sdiv"></div>
    <div class="srow"><span>Subtotal</span><span>${fRp(t.subtotal)}</span></div>
    ${t.diskon>0?`<div class="srow dis"><span>Diskon</span><span>- ${fRp(t.diskon)}</span></div>`:''}
    <div class="srow bold"><span>TOTAL</span><span>${fRp(t.total)}</span></div>
    <div class="srow"><span>Bayar</span><span>${fRp(t.bayar)}</span></div>
    ${(t.metode_bayar && t.metode_bayar!=='tunai') ? '' : `<div class="srow"><span style="color:var(--green)">Kembalian</span><span style="color:var(--green)">${fRp(t.kembalian)}</span></div>`}
    <div class="srow"><span>Metode</span><span>${metodeLabel(t.metode_bayar)}</span></div>
    <div class="sdiv"></div>
    <div style="text-align:center;color:var(--muted);font-size:11px">${toko.pesan_struk||'Terima kasih!'}</div>`;
  renderPrintButtons();
}

// ══════════════════════════════════

//  CETAK STRUK
// ══════════════════════════════════
function cetakStruk() {
  const t = lastTrx; if (!t) return;
  const nm = toko.nama_toko||'TOKO';
  const waktuFmt = new Date(t.waktu).toLocaleString('id-ID');
  document.getElementById('printArea').style.display='block';
  document.getElementById('printArea').innerHTML=`
    <div class="psnm">${nm}</div>
    ${toko.alamat?`<div class="pssub">${toko.alamat}</div>`:''}
    ${toko.telp?`<div class="pssub">Telp: ${toko.telp}</div>`:''}
    <div class="psdiv"></div>
    <div class="psrow"><span>No</span><span>${t.no_trx}</span></div>
    <div class="psrow"><span>Waktu</span><span>${waktuFmt}</span></div>
    <div class="psdiv"></div>
    ${t.items.map(i=>`
      <div class="psitem">${i.nama_produk}</div>
      <div class="psitem-h"><span>${i.qty} x ${fRp(i.harga)}</span><span>${fRp(i.subtotal)}</span></div>`).join('')}
    <div class="psdiv"></div>
    ${t.diskon>0?`<div class="psrow"><span>Diskon</span><span>- ${fRp(t.diskon)}</span></div>`:''}
    <div class="psrow psbold"><span>TOTAL</span><span>${fRp(t.total)}</span></div>
    <div class="psrow"><span>Bayar</span><span>${fRp(t.bayar)}</span></div>
    ${(!t.metode_bayar||t.metode_bayar==='tunai')?`<div class="psrow"><span>Kembali</span><span>${fRp(t.kembalian)}</span></div>`:''}
    <div class="psrow"><span>Metode</span><span>${metodeLabel(t.metode_bayar, true)}</span></div>
    <div class="psdiv"></div>
    <div class="psfooter">${toko.pesan_struk||'Terima kasih!'}</div>
    <br>`;
  window.print();
  setTimeout(()=>document.getElementById('printArea').style.display='none',800);
}

// ══════════════════════════════════

//  BAGIKAN STRUK (PDF via Web Share)
// ══════════════════════════════════
async function bagikanStruk() {
  const t = lastTrx; if (!t) return;
  if (typeof window.jspdf === 'undefined') {
    alert('Library PDF belum siap, coba lagi sebentar.'); return;
  }

  const mm     = parseInt(toko.ukuran_kertas || '58');
  const isWide = mm >= 80;
  const W      = mm;
  const pad    = 2;                          // margin kiri/kanan (mm)

  // Font sizes (pt) — sedikit lebih besar agar terbaca jelas
  const fsNm  = isWide ? 13 : 11;
  const fsSub = isWide ? 9  : 8;
  const fsRow = isWide ? 9  : 8;
  const fsTot = isWide ? 11 : 10;

  // Step height sesuai rumus jsPDF (satuan mm)
  const sH    = fs => fs * 0.38 + 0.8;     // tinggi teks per baris
  const sLine = 2.2;                        // tinggi garis divider
  const hasTunai = !t.metode_bayar || t.metode_bayar === 'tunai';

  // ── PASS 1: hitung tinggi aktual tanpa menggambar ──────────────
  let y = 4;
  y += sH(fsNm);
  if (toko.alamat) y += sH(fsSub);
  if (toko.telp)   y += sH(fsSub);
  y += sLine;
  y += sH(fsRow);                          // No
  y += sH(fsRow);                          // Waktu
  if (t.kasir) y += sH(fsRow);
  y += sLine;
  t.items.forEach(() => { y += sH(fsRow); y += sH(fsRow); });
  y += sLine;
  if (t.diskon > 0) y += sH(fsRow);
  y += sH(fsTot);                          // TOTAL
  y += sH(fsRow);                          // Bayar
  if (hasTunai) y += sH(fsRow);           // Kembali
  y += sH(fsRow);                          // Metode
  y += sLine;
  y += sH(fsSub);                          // footer
  const docH = y + 6;                      // 6mm padding bawah

  // ── PASS 2: buat dokumen & gambar ─────────────────────────────
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ unit: 'mm', format: [W, docH], orientation: 'portrait' });

  y = 4; // reset ke posisi awal

  const draw = (fn) => {
    fn();
  };
  const center = (txt, fs, bold=false) => {
    doc.setFont('courier', bold ? 'bold' : 'normal');
    doc.setFontSize(fs);
    // potong teks jika terlalu panjang
    const maxW = W - pad * 2;
    const lines = doc.splitTextToSize(txt, maxW);
    doc.text(lines[0] || txt, W / 2, y, { align: 'center' });
    y += sH(fs);
  };
  const row = (left, right, fs, bold=false) => {
    doc.setFont('courier', bold ? 'bold' : 'normal');
    doc.setFontSize(fs);
    doc.text(left+'',  pad,   y);
    doc.text(right+'', W-pad, y, { align: 'right' });
    y += sH(fs);
  };
  const textL = (txt, fs) => {
    doc.setFont('courier', 'normal');
    doc.setFontSize(fs);
    doc.text((txt+'').substring(0, 48), pad, y);
    y += sH(fs);
  };
  const divider = () => {
    doc.setDrawColor(150);
    doc.setLineDash([0.6, 0.6]);
    doc.line(pad, y, W - pad, y);
    doc.setLineDash([]);
    y += sLine;
  };

  // Header toko
  center(toko.nama_toko || 'TOKO', fsNm, true);
  if (toko.alamat) center(toko.alamat, fsSub);
  if (toko.telp)   center('Telp: ' + toko.telp, fsSub);
  divider();

  // Info transaksi
  row('No', t.no_trx, fsRow);
  row('Waktu', new Date(t.waktu).toLocaleString('id-ID'), fsRow);
  if (t.kasir) row('Kasir', t.kasir, fsRow);
  divider();

  // Items
  t.items.forEach(i => {
    textL(i.nama_produk, fsRow);
    row('  ' + i.qty + ' x ' + fRp(i.harga), fRp(i.subtotal), fsRow);
  });
  divider();

  // Totals
  if (t.diskon > 0) row('Diskon', '- ' + fRp(t.diskon), fsRow);
  row('TOTAL', fRp(t.total), fsTot, true);
  row('Bayar', fRp(t.bayar), fsRow);
  if (hasTunai) row('Kembali', fRp(t.kembalian), fsRow);
  row('Metode', metodeLabel(t.metode_bayar, true), fsRow);
  divider();

  // Footer
  center(toko.pesan_struk || 'Terima kasih!', fsSub);

  // Generate & share/download
  const pdfBlob = doc.output('blob');
  const noSafe  = (t.no_trx || 'struk').replace(/[\/\\:*?"<>|]/g, '-');
  const fname   = 'struk-' + noSafe + '.pdf';
  const pdfFile = new File([pdfBlob], fname, { type: 'application/pdf' });

  if (navigator.canShare && navigator.canShare({ files: [pdfFile] })) {
    try {
      await navigator.share({ title: 'Struk Transaksi', files: [pdfFile] });
    } catch(e) {
      if (e.name !== 'AbortError') _downloadPdf(pdfBlob, fname);
    }
  } else {
    _downloadPdf(pdfBlob, fname);
  }
}

function _downloadPdf(blob, fname) {
  const url = URL.createObjectURL(blob);
  const a   = document.createElement('a');
  a.href = url; a.download = fname; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

// ══════════════════════════════════

//  PRINT: PLATFORM DETECTION & SMART BUTTONS
// ══════════════════════════════════
function renderPrintButtons() {
  const el = document.getElementById('mSuksesActions');
  if (!el) return;
  const isAndroid = /Android/i.test(navigator.userAgent);
  const hasSerial = 'serial' in navigator;
  const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
  const canShare = navigator.share !== undefined;

  let html = '';
  
  // Row 1: Print options
  html += `<div style="display:flex;gap:6px;flex-wrap:wrap;justify-content:center;margin-bottom:10px;">`;
  html += `<button class="mbtn sec" onclick="cetakStruk()">🖨️ Cetak</button>`;

  if (isAndroid) {
    html += `<button class="mbtn" style="background:#2d7d32;color:#fff;font-size:11px;padding:8px 12px;"
               title="Print langsung ke printer Bluetooth via RawBT"
               onclick="printRawBT()">📱 RawBT</button>`;
  }
  if (hasSerial) {
    html += `<button class="mbtn" style="background:#6a1b9a;color:#fff;font-size:11px;padding:8px 12px;"
               title="Print via USB/COM Port (Chrome desktop)"
               onclick="printSerial()">🔌 USB</button>`;
  }
  html += `</div>`;
  
  // Row 2: Share options
  html += `<div style="display:flex;gap:6px;flex-wrap:wrap;justify-content:center;margin-bottom:10px;">`;
  
  // Share Button (opens modal)
  html += `<button class="mbtn" style="background:#25D366;color:#fff;font-size:11px;padding:8px 12px;"
             onclick="openShareModal()">📤 Share</button>`;
  
  // Share PDF
  html += `<button class="mbtn" style="background:var(--blue);color:#fff;font-size:11px;padding:8px 12px;"
             onclick="bagikanStruk()">📄 PDF</button>`;
  
  // Native Share (Web Share API) - untuk mobile
  if (canShare) {
    html += `<button class="mbtn" style="background:#FF6B6B;color:#fff;font-size:11px;padding:8px 12px;"
               onclick="nativeShareStruk()">🔗 Share...</button>`;
  }
  
  html += `</div>`;
  
  // Row 3: Action done
  html += `<div style="display:flex;gap:6px;justify-content:center;">`;
  html += `<button class="mbtn grn" onclick="closeM('mSukses')" style="flex:1;max-width:200px;">✅ Selesai</button>`;
  html += `</div>`;
  
  el.innerHTML = html;
}

// ══════════════════════════════════

//  SHARE STRUK DIGITAL
// ══════════════════════════════════
async function shareStrukImage(app) {
  if (!lastTrx) return;
  showLoading(true);
  
  try {
    // Generate struk image
    const res = await fetch(`/api/struk/${lastTrx.id}/image`);
    if (!res.ok) throw new Error('Gagal generate struk image');
    
    const blob = await res.blob();
    const file = new File([blob], `struk-${lastTrx.no_trx}.png`, { type: 'image/png' });
    
    // Check if Web Share API with files is supported
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      try {
        await navigator.share({
          title: `Struk ${lastTrx.no_trx}`,
          text: `Transaksi di ${toko.nama_toko || 'Toko'} - Total: ${fRp(lastTrx.total)}`,
          files: [file]
        });
        showToast('✅ Struk dibagikan');
      } catch (err) {
        if (err.name !== 'AbortError') {
          // Fallback: download file
          downloadBlob(blob, `struk-${lastTrx.no_trx}.png`);
        }
      }
    } else {
      // Fallback: download
      downloadBlob(blob, `struk-${lastTrx.no_trx}.png`);
      
      // Show instructions based on app
      let appName = 'aplikasi';
      let url = '';
      
      switch(app) {
        case 'whatsapp':
          appName = 'WhatsApp';
          url = 'https://wa.me/';
          break;
        case 'telegram':
          appName = 'Telegram';
          url = 'https://t.me/share/url';
          break;
        case 'instagram':
          appName = 'Instagram';
          break;
      }
      
      showToast(`📎 Gambar struk didownload. Buka ${appName} untuk membagikan.`);
      
      // Open app if URL available
      if (url && app === 'whatsapp') {
        setTimeout(() => {
          window.open(url, '_blank');
        }, 1000);
      }
    }
  } catch(e) {
    showToast('❌ ' + e.message);
  }
  
  showLoading(false);
}

async function nativeShareStruk() {
  if (!lastTrx) return;
  
  const shareData = {
    title: `Struk ${lastTrx.no_trx}`,
    text: `Transaksi di ${toko.nama_toko || 'Toko'}\n` +
          `No: ${lastTrx.no_trx}\n` +
          `Total: ${fRp(lastTrx.total)}\n` +
          `Bayar: ${fRp(lastTrx.bayar)}\n` +
          `Kembalian: ${fRp(lastTrx.kembalian)}`,
    url: window.location.href
  };
  
  try {
    if (navigator.share) {
      await navigator.share(shareData);
      showToast('✅ Struk dibagikan');
    } else {
      // Fallback: copy to clipboard
      copyStrukText();
    }
  } catch (err) {
    if (err.name !== 'AbortError') {
      copyStrukText();
    }
  }
}

function copyStrukText() {
  if (!lastTrx) return;
  
  const text = `*STRUK ${toko.nama_toko || 'TOKO'}*\n` +
               `No: ${lastTrx.no_trx}\n` +
               `Waktu: ${new Date(lastTrx.waktu).toLocaleString('id-ID')}\n\n` +
               lastTrx.items.map(i => `${i.nama_produk} x${i.qty} = ${fRp(i.subtotal)}`).join('\n') +
               `\n\n*Total: ${fRp(lastTrx.total)}*\n` +
               `Bayar: ${fRp(lastTrx.bayar)}\n` +
               `Kembali: ${fRp(lastTrx.kembalian)}\n\n` +
               `Terima kasih!`;
  
  navigator.clipboard.writeText(text).then(() => {
    showToast('✅ Teks struk disalin ke clipboard');
  }).catch(() => {
    showToast('❌ Gagal menyalin teks');
  });
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ══════════════════════════════════

//  SHARE STRUK LENGKAP
// ══════════════════════════════════
function openShareModal() {
  if (!lastTrx) return;
  
  // Render preview
  const previewEl = document.getElementById('shareStrukPreview');
  previewEl.innerHTML = `
    <div style="text-align:center;margin-bottom:8px;">
      <strong style="color:var(--accent);">${toko.nama_toko || 'TOKO'}</strong>
    </div>
    <div style="color:var(--muted);text-align:center;font-size:10px;margin-bottom:10px;">
      ${lastTrx.no_trx} · ${new Date(lastTrx.waktu).toLocaleString('id-ID')}
    </div>
    <div style="border-top:1px dashed var(--border);border-bottom:1px dashed var(--border);padding:8px 0;margin:8px 0;">
      ${lastTrx.items.map(i => `
        <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
          <span>${i.nama_produk} x${i.qty}</span>
          <span>${fRp(i.subtotal)}</span>
        </div>
      `).join('')}
    </div>
    <div style="text-align:right;">
      <div style="font-size:16px;font-weight:700;color:var(--accent);">Total: ${fRp(lastTrx.total)}</div>
      <div style="font-size:11px;color:var(--muted);">Bayar: ${fRp(lastTrx.bayar)} · Kembali: ${fRp(lastTrx.kembalian)}</div>
    </div>
  `;
  
  openM('mShareStruk');
}

async function shareToApp(app) {
  if (!lastTrx) return;
  
  showLoading(true);
  
  try {
    switch(app) {
      case 'whatsapp':
        await shareToWhatsApp();
        break;
      case 'telegram':
        await shareToTelegram();
        break;
      case 'instagram':
        await shareToInstagram();
        break;
      case 'email':
        shareToEmail();
        break;
      case 'rawbt':
        printRawBT();
        closeM('mShareStruk');
        break;
      case 'download':
        await downloadStrukImage();
        break;
    }
  } catch(e) {
    showToast('❌ ' + e.message);
  }
  
  showLoading(false);
}

async function shareToWhatsApp() {
  // Generate image
  const res = await fetch(`/api/struk/${lastTrx.id}/image`);
  const blob = await res.blob();
  
  // Try Web Share API first
  const file = new File([blob], `struk-${lastTrx.no_trx}.png`, { type: 'image/png' });
  
  if (navigator.canShare && navigator.canShare({ files: [file] })) {
    await navigator.share({
      title: `Struk ${lastTrx.no_trx}`,
      files: [file]
    });
    closeM('mShareStruk');
  } else {
    // Fallback: download then open WA
    downloadBlob(blob, `struk-${lastTrx.no_trx}.png`);
    
    // Open WhatsApp
    const text = encodeURIComponent(`Struk ${lastTrx.no_trx} - Total: ${fRp(lastTrx.total)}`);
    window.open(`https://wa.me/?text=${text}`, '_blank');
    
    showToast('📎 Gambar didownload. Silakan lampirkan di WhatsApp.');
    closeM('mShareStruk');
  }
}

async function shareToTelegram() {
  const text = encodeURIComponent(
    `*STRUK ${toko.nama_toko || 'TOKO'}*\n\n` +
    `No: ${lastTrx.no_trx}\n` +
    `Waktu: ${new Date(lastTrx.waktu).toLocaleString('id-ID')}\n\n` +
    `*Item:*\n` +
    lastTrx.items.map(i => `• ${i.nama_produk} x${i.qty} = ${fRp(i.subtotal)}`).join('\n') +
    `\n\n*Total: ${fRp(lastTrx.total)}*\n` +
    `Bayar: ${fRp(lastTrx.bayar)}\n` +
    `Kembali: ${fRp(lastTrx.kembalian)}\n\n` +
    `_Terima kasih telah berbelanja!_`
  );
  
  window.open(`https://t.me/share/url?url=&text=${text}`, '_blank');
  closeM('mShareStruk');
}

async function shareToInstagram() {
  // Instagram tidak support sharing dari web directly
  // Download image dan instruksikan user untuk upload ke IG
  const res = await fetch(`/api/struk/${lastTrx.id}/image`);
  const blob = await res.blob();
  downloadBlob(blob, `struk-${lastTrx.no_trx}.png`);
  
  showToast('📎 Gambar struk disimpan. Buka Instagram untuk membagikan.');
  
  // Try to open Instagram app
  setTimeout(() => {
    window.location.href = 'instagram://camera';
  }, 1000);
  
  closeM('mShareStruk');
}

function shareToEmail() {
  const subject = encodeURIComponent(`Struk Transaksi ${lastTrx.no_trx} - ${toko.nama_toko || 'Toko'}`);
  const body = encodeURIComponent(
    `Yth. Pelanggan,\n\n` +
    `Berikut adalah detail transaksi Anda:\n\n` +
    `No Transaksi: ${lastTrx.no_trx}\n` +
    `Tanggal: ${new Date(lastTrx.waktu).toLocaleString('id-ID')}\n` +
    `Toko: ${toko.nama_toko || 'Toko'}\n` +
    `Alamat: ${toko.alamat || '-'}\n\n` +
    `--- Detail Pembelian ---\n\n` +
    lastTrx.items.map(i => `${i.nama_produk} x${i.qty} @ ${fRp(i.harga)} = ${fRp(i.subtotal)}`).join('\n') +
    `\n\nSubtotal: ${fRp(lastTrx.subtotal)}\n` +
    (lastTrx.diskon > 0 ? `Diskon: -${fRp(lastTrx.diskon)}\n` : '') +
    `TOTAL: ${fRp(lastTrx.total)}\n` +
    `Bayar: ${fRp(lastTrx.bayar)}\n` +
    `Kembalian: ${fRp(lastTrx.kembalian)}\n\n` +
    `---\n` +
    `Terima kasih telah berbelanja!\n` +
    `${toko.pesan_struk || ''}`
  );
  
  window.open(`mailto:?subject=${subject}&body=${body}`, '_blank');
  closeM('mShareStruk');
}

async function downloadStrukImage() {
  const res = await fetch(`/api/struk/${lastTrx.id}/image`);
  const blob = await res.blob();
  downloadBlob(blob, `struk-${lastTrx.no_trx}.png`);
  showToast('✅ Gambar struk disimpan');
  closeM('mShareStruk');
}

// ══════════════════════════════════

//  PRINT: BUILD PLAIN TEXT (RawBT / fallback)
// ══════════════════════════════════
function buildStrukText() {
  const t = lastTrx; if (!t) return '';
  const W  = parseInt(toko.ukuran_kertas||'58') >= 80 ? 42 : 32;
  const ctr = s => { s=(s+'').substring(0,W); const p=Math.max(0,Math.floor((W-s.length)/2)); return ' '.repeat(p)+s; };
  const row = (l,r) => { l=(l+'').substring(0,W-2); r=r+''; return l+' '.repeat(Math.max(1,W-l.length-r.length))+r; };
  const div = () => '-'.repeat(W);
  const ln  = [];

  ln.push(ctr(toko.nama_toko||'TOKO'));
  if (toko.alamat) ln.push(ctr(toko.alamat));
  if (toko.telp)   ln.push(ctr('Telp: '+toko.telp));
  ln.push(div());
  ln.push(row('No', t.no_trx));
  ln.push(row('Waktu', new Date(t.waktu).toLocaleString('id-ID')));
  if (t.kasir) ln.push(row('Kasir', t.kasir));
  ln.push(div());
  t.items.forEach(i => {
    ln.push((i.nama_produk||'').substring(0, W));
    ln.push(row('  '+i.qty+'x'+fRp(i.harga), fRp(i.subtotal)));
  });
  ln.push(div());
  if (t.diskon > 0) ln.push(row('Diskon', '- '+fRp(t.diskon)));
  ln.push(row('TOTAL', fRp(t.total)));
  ln.push(row('Bayar', fRp(t.bayar)));
  if (!t.metode_bayar || t.metode_bayar==='tunai') ln.push(row('Kembali', fRp(t.kembalian)));
  ln.push(row('Metode', metodeLabel(t.metode_bayar, true)));
  ln.push(div());
  ln.push(ctr(toko.pesan_struk||'Terima kasih!'));
  ln.push(''); ln.push(''); ln.push('');
  return ln.join('\n');
}

// ══════════════════════════════════

//  PRINT: BUILD ESC/POS BYTES (Web Serial)
// ══════════════════════════════════
function buildEscPos() {
  const t = lastTrx; if (!t) return new Uint8Array();
  const W   = parseInt(toko.ukuran_kertas||'58') >= 80 ? 42 : 32;
  const ESC = 0x1B, GS = 0x1D, LF = 0x0A;
  const b   = [];

  const enc  = s => { for (const ch of s+'') { const c=ch.charCodeAt(0); b.push(c<128?c:c<=255?c:0x3F); } };
  const line = (s='') => { enc(s+''); b.push(LF); };
  const ctr  = s => { s=(s+'').substring(0,W); const p=Math.max(0,Math.floor((W-s.length)/2)); return ' '.repeat(p)+s; };
  const row  = (l,r) => { l=(l+'').substring(0,W-2); r=r+''; return l+' '.repeat(Math.max(1,W-l.length-r.length))+r; };
  const div  = () => line('-'.repeat(W));

  b.push(ESC, 0x40);                        // Init
  b.push(ESC, 0x61, 1); b.push(ESC,0x45,1); // Center + Bold on
  line(ctr(toko.nama_toko||'TOKO'));
  b.push(ESC, 0x45, 0);                     // Bold off
  if (toko.alamat) line(ctr(toko.alamat));
  if (toko.telp)   line(ctr('Telp: '+toko.telp));
  b.push(ESC, 0x61, 0);                     // Left align
  div();
  line(row('No', t.no_trx));
  line(row('Waktu', new Date(t.waktu).toLocaleString('id-ID')));
  if (t.kasir) line(row('Kasir', t.kasir));
  div();
  t.items.forEach(i => {
    line((i.nama_produk||'').substring(0, W));
    line(row('  '+i.qty+'x'+fRp(i.harga), fRp(i.subtotal)));
  });
  div();
  if (t.diskon > 0) line(row('Diskon', '- '+fRp(t.diskon)));
  b.push(ESC,0x45,1); line(row('TOTAL', fRp(t.total))); b.push(ESC,0x45,0);
  line(row('Bayar', fRp(t.bayar)));
  if (!t.metode_bayar || t.metode_bayar==='tunai') line(row('Kembali', fRp(t.kembalian)));
  line(row('Metode', metodeLabel(t.metode_bayar, true)));
  div();
  b.push(ESC, 0x61, 1);
  line(ctr(toko.pesan_struk||'Terima kasih!'));
  b.push(ESC, 0x61, 0);
  b.push(LF, LF, LF);
  b.push(GS, 0x56, 0x41, 0x00);            // Full cut
  return new Uint8Array(b);
}

// ══════════════════════════════════

//  PRINT: WEB SERIAL API (Chrome desktop — USB/COM)
// ══════════════════════════════════
let _serialPort = null;

async function printSerial() {
  if (!('serial' in navigator)) {
    showToast('❌ Butuh Chrome desktop untuk Serial/USB print'); return;
  }
  const t = lastTrx; if (!t) return;
  showLoading(true);
  try {
    // Gunakan port yang pernah diizinkan, atau minta pilih baru
    if (!_serialPort) {
      const saved = await navigator.serial.getPorts();
      _serialPort = saved.length ? saved[0] : await navigator.serial.requestPort();
    }
    await _serialPort.open({ baudRate: 9600 });
    const writer = _serialPort.writable.getWriter();
    await writer.write(buildEscPos());
    writer.releaseLock();
    await _serialPort.close();
    showToast('✅ Struk dicetak via Serial/USB!');
  } catch(e) {
    _serialPort = null; // reset agar bisa pilih ulang
    if (e.name !== 'NotFoundError') showToast('❌ Serial: '+e.message);
  }
  showLoading(false);
}

// ══════════════════════════════════

//  PRINT: MOBILE PRINTER DEEP LINK (RawBT / Custom)
// ══════════════════════════════════
function printRawBT() {
  const t = lastTrx; if (!t) return;
  const strukText = buildStrukText();
  // Gunakan scheme dari pengaturan (default: rawbt)
  const scheme = (toko.printer_app_scheme || 'rawbt').replace(/:$/, ''); // hapus : jika ada
  const url = scheme + ':?charset=utf-8&text=' + encodeURIComponent(strukText);
  console.log('[PrintMobile] Scheme:', scheme, 'URL:', url.substring(0, 100));
  window.location.href = url;
}

// ══════════════════════════════════
