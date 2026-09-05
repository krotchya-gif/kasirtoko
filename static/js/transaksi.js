// static/js/transaksi.js — pindahan murni dari templates/index.html (split Fase 5).
// Global bersama (api, showToast, openM, fRp, ...) tetap window-scope.

//  RIWAYAT
// ══════════════════════════════════
// ═══════════════════════════════════════════════════════════════
//  RIWAYAT TRANSAKSI - NEW DESIGN
// ═══════════════════════════════════════════════════════════════
let riwayatTab = 'lunas'; // 'lunas' atau 'belum_lunas'
let riwayatCache = [];
let riwayatSearchQuery = '';

async function openRiwayat() { 
  openM('mRiwayat'); 
  // Set default tanggal hari ini
  const today = new Date().toISOString().split('T')[0];
  document.getElementById('rTanggal').value = today;
  switchTabRiwayat('lunas');
}

function switchTabRiwayat(tab) {
  riwayatTab = tab;
  document.getElementById('tabLunas').classList.toggle('active', tab === 'lunas');
  document.getElementById('tabBelumLunas').classList.toggle('active', tab === 'belum_lunas');
  
  if (tab === 'lunas') {
    document.getElementById('riwayatLunasSection').style.display = 'block';
    document.getElementById('riwayatBelumLunasSection').style.display = 'none';
    muatRiwayat();
  } else {
    document.getElementById('riwayatLunasSection').style.display = 'none';
    document.getElementById('riwayatBelumLunasSection').style.display = 'block';
    muatPiutang();
    muatReminderPiutang();
  }
}

function onPeriodeChange() {
  // Update date picker based on periode
  const periode = document.getElementById('rPeriode').value;
  const dateInput = document.getElementById('rTanggal');
  const today = new Date();
  
  if (periode === 'harian') {
    dateInput.type = 'date';
    dateInput.value = today.toISOString().split('T')[0];
  } else if (periode === 'mingguan') {
    dateInput.type = 'week';
    const weekNum = getWeekNumber(today);
    dateInput.value = `${today.getFullYear()}-W${weekNum.toString().padStart(2, '0')}`;
  } else if (periode === 'bulanan') {
    dateInput.type = 'month';
    dateInput.value = `${today.getFullYear()}-${(today.getMonth() + 1).toString().padStart(2, '0')}`;
  }
  muatRiwayat();
}

function getWeekNumber(d) {
  d = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
  return weekNo;
}

let riwayatSearchDebounce;
function filterRiwayatDebounced() {
  clearTimeout(riwayatSearchDebounce);
  riwayatSearchDebounce = setTimeout(() => {
    riwayatSearchQuery = document.getElementById('rCari').value.toLowerCase().trim();
    renderRiwayatList();
  }, 300);
}

async function muatRiwayat() {
  const periode = document.getElementById('rPeriode').value;
  const tanggal = document.getElementById('rTanggal').value;
  
  showLoading(true);
  try {
    // Build date range based on periode
    let dari, ke;
    if (periode === 'harian' && tanggal) {
      dari = tanggal;
      ke = tanggal;
    } else if (periode === 'mingguan' && tanggal) {
      const [year, week] = tanggal.split('-W');
      const dates = getWeekDates(parseInt(year), parseInt(week));
      dari = dates[0];
      ke = dates[6];
    } else if (periode === 'bulanan' && tanggal) {
      const [year, month] = tanggal.split('-');
      dari = `${year}-${month}-01`;
      ke = `${year}-${month}-${new Date(parseInt(year), parseInt(month), 0).getDate()}`;
    } else {
      // Default: today
      const today = new Date().toISOString().split('T')[0];
      dari = today;
      ke = today;
    }
    
    // Load all transactions (both lunas and belum lunas)
    const status = riwayatTab === 'lunas' ? 'aktif' : 'aktif';
    const list = await api(`/api/transaksi?dari=${dari}&ke=${ke}&status=${status}&limit=200`);
    
    // Gunakan field is_lunas dari backend (1=lunas, 0=belum lunas/piutang)
    riwayatCache = list.map(r => ({
      ...r,
      is_lunas: r.is_lunas === 1 || r.is_lunas === '1' || r.is_lunas === true
    }));
    
    renderRiwayatSummary();
    renderRiwayatList();
  } catch(e) {
    showToast('❌ Gagal memuat riwayat: ' + e.message);
  }
  showLoading(false);
}

function getWeekDates(year, week) {
  const d = new Date(year, 0, 1);
  const dayNum = d.getDay() || 7;
  d.setDate(d.getDate() + 4 - dayNum);
  d.setDate(d.getDate() + (week - 1) * 7);
  const dates = [];
  for (let i = 0; i < 7; i++) {
    const date = new Date(d);
    date.setDate(d.getDate() + i);
    dates.push(date.toISOString().split('T')[0]);
  }
  return dates;
}

function renderRiwayatSummary() {
  const filtered = riwayatCache.filter(r => {
    if (riwayatTab === 'lunas') return r.is_lunas;
    return !r.is_lunas;
  });
  
  const jumlahTrx = filtered.length;
  const produkTerjual = filtered.reduce((s, r) => s + r.items.reduce((ss, i) => ss + i.qty, 0), 0);
  const totalOmzet = filtered.reduce((s, r) => s + r.total, 0);
  
  const el = document.getElementById('rSummary');
  
  if (riwayatTab === 'lunas') {
    // Hitung profit (butuh harga_modal dari backend)
    const totalProfit = filtered.reduce((s, r) => {
      return s + r.items.reduce((ss, i) => {
        const modal = i.harga_modal || 0;
        return ss + ((i.harga - modal) * i.qty);
      }, 0);
    }, 0);
    
    el.innerHTML = `
      <div class="riwayat-summary-grid">
        <div class="riwayat-summary-item">
          <span class="riwayat-summary-label">Jumlah Transaksi</span>
          <span class="riwayat-summary-value">${jumlahTrx}</span>
        </div>
        <div class="riwayat-summary-item">
          <span class="riwayat-summary-label">Jumlah Produk Terjual</span>
          <span class="riwayat-summary-value">${produkTerjual} <a href="#" class="riwayat-summary-link" onclick="showProdukTerjualDetail();return false;">› Lihat Detail</a></span>
        </div>
        <div class="riwayat-summary-item">
          <span class="riwayat-summary-label">Omzet</span>
          <span class="riwayat-summary-value accent">${fRp(totalOmzet)}</span>
        </div>
        <div class="riwayat-summary-item">
          <span class="riwayat-summary-label">Profit</span>
          <span class="riwayat-summary-value">${fRp(totalProfit)}</span>
        </div>
      </div>
    `;
  } else {
    // Belum Lunas - Piutang
    const totalPiutang = filtered.reduce((s, r) => s + r.total, 0);
    const totalTerbayar = filtered.reduce((s, r) => s + (r.terbayar || 0), 0);
    const sisaPiutang = totalPiutang - totalTerbayar;
    
    el.innerHTML = `
      <div class="riwayat-summary-grid">
        <div class="riwayat-summary-item">
          <span class="riwayat-summary-label">Jumlah Transaksi</span>
          <span class="riwayat-summary-value">${jumlahTrx}</span>
        </div>
        <div class="riwayat-summary-item">
          <span class="riwayat-summary-label">Jumlah Produk Terjual</span>
          <span class="riwayat-summary-value">${produkTerjual}</span>
        </div>
        <div class="riwayat-summary-item">
          <span class="riwayat-summary-label">Total Piutang</span>
          <span class="riwayat-summary-value accent">${fRp(totalPiutang)}</span>
        </div>
        <div class="riwayat-summary-item">
          <span class="riwayat-summary-label">Total Terbayar</span>
          <span class="riwayat-summary-value green">${fRp(totalTerbayar)}</span>
        </div>
        <div class="riwayat-summary-item full-width">
          <span class="riwayat-summary-label">Sisa Piutang</span>
          <span class="riwayat-summary-value red">${fRp(sisaPiutang)}</span>
        </div>
      </div>
    `;
  }
}

function renderRiwayatList() {
  const el = document.getElementById('rContent');
  
  let filtered = riwayatCache.filter(r => {
    if (riwayatTab === 'lunas') return r.is_lunas;
    return !r.is_lunas;
  });
  
  // Apply search
  if (riwayatSearchQuery) {
    filtered = filtered.filter(r => 
      r.no_trx.toLowerCase().includes(riwayatSearchQuery) ||
      (r.pelanggan_nama && r.pelanggan_nama.toLowerCase().includes(riwayatSearchQuery))
    );
  }
  
  if (!filtered.length) {
    el.innerHTML = '<div style="color:var(--muted);text-align:center;padding:40px 20px;font-size:15px;">Tidak ada transaksi di periode ini</div>';
    return;
  }
  
  el.innerHTML = filtered.map(r => {
    const isVoid = r.status === 'void';
    const waktu = new Date(r.waktu);
    const tgl = waktu.getDate();
    const bln = waktu.toLocaleDateString('id-ID', { month: 'short' }).toUpperCase();
    const jam = waktu.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
    
    const metodeClass = r.metode_bayar === 'tunai' ? 'tunai' : 
                        r.metode_bayar === 'transfer' ? 'transfer' : 
                        r.metode_bayar === 'piutang' ? 'piutang' : 'qris';
    const metodeLabel = r.metode_bayar === 'tunai' ? 'TUNAI' : 
                        r.metode_bayar === 'transfer' ? 'TRANSFER' : 
                        r.metode_bayar === 'piutang' ? 'PIUTANG' : 'QRIS';
    
    return `
      <div class="riwayat-item ${isVoid ? 'void' : ''}" onclick="lihatDetailTrx(${r.id})">
        <div class="riwayat-date-box ${isVoid ? 'void' : ''}">
          <div class="riwayat-date-day">${tgl}</div>
          <div class="riwayat-date-month">${bln} ${waktu.getFullYear()}</div>
          <div class="riwayat-date-time">${jam}</div>
        </div>
        <div class="riwayat-item-content">
          <div class="riwayat-item-trx">${r.no_trx}</div>
          <div class="riwayat-item-pelanggan">${r.pelanggan_nama || 'Umum'}</div>
          <div class="riwayat-item-total ${isVoid ? 'void' : ''}">${fRp(r.total)}</div>
        </div>
        <div class="riwayat-item-meta">
          ${isVoid ? 
            '<span class="riwayat-item-badge void">VOID</span>' :
            `<span class="riwayat-item-badge ${metodeClass}">${metodeLabel}</span>`
          }
          <div class="riwayat-item-kasir">Dibuat Oleh <span>${r.kasir || 'Kasir'}</span></div>
        </div>
      </div>
    `;
  }).join('');
}

async function exportRiwayatExcel() {
  showToast('📊 Mempersiapkan export Excel...');
  // Implementasi export Excel akan ditambahkan di kemudian hari
  // Bisa menggunakan library seperti SheetJS atau export CSV sementara
  const filtered = riwayatCache.filter(r => {
    if (riwayatTab === 'lunas') return r.is_lunas;
    return !r.is_lunas;
  });
  
  // Export CSV sebagai sementara
  let csv = 'No,No Transaksi,Waktu,Pelanggan,Kasir,Total,Status\n';
  filtered.forEach((r, i) => {
    csv += `${i+1},${r.no_trx},"${r.waktu}","${r.pelanggan_nama || 'Umum'}","${r.kasir || '-'}",${r.total},${r.status}\n`;
  });
  
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `riwayat_transaksi_${new Date().toISOString().split('T')[0]}.csv`;
  a.click();
  URL.revokeObjectURL(url);
  showToast('✅ Export CSV berhasil');
}

async function showProdukTerjualDetail() {
  const periode = document.getElementById('rPeriode').value;
  const tanggal = document.getElementById('rTanggal').value;
  
  // Build date range
  let dari, ke, periodeLabel;
  if (periode === 'harian' && tanggal) {
    dari = tanggal;
    ke = tanggal;
    periodeLabel = new Date(tanggal).toLocaleDateString('id-ID', {day:'numeric', month:'long', year:'numeric'});
  } else if (periode === 'mingguan' && tanggal) {
    const [year, week] = tanggal.split('-W');
    const dates = getWeekDates(parseInt(year), parseInt(week));
    dari = dates[0];
    ke = dates[6];
    periodeLabel = `Minggu ke-${week}, ${year}`;
  } else if (periode === 'bulanan' && tanggal) {
    const [year, month] = tanggal.split('-');
    dari = `${year}-${month}-01`;
    ke = `${year}-${month}-${new Date(parseInt(year), parseInt(month), 0).getDate()}`;
    periodeLabel = new Date(`${year}-${month}-01`).toLocaleDateString('id-ID', {month:'long', year:'numeric'});
  } else {
    const today = new Date().toISOString().split('T')[0];
    dari = today;
    ke = today;
    periodeLabel = 'Hari Ini';
  }
  
  document.getElementById('ptPeriodeLabel').textContent = periodeLabel;
  openM('mProdukTerjual');
  
  showLoading(true);
  try {
    const data = await api(`/api/laporan/produk-terjual?dari=${dari}&ke=${ke}`);
    
    document.getElementById('ptTotalQty').textContent = data.total_qty || 0;
    document.getElementById('ptTotalOmzet').textContent = fRp(data.total_omzet || 0);
    
    const listEl = document.getElementById('produkTerjualList');
    if (!data.rows || data.rows.length === 0) {
      listEl.innerHTML = '<div style="text-align:center;color:var(--muted);padding:40px;">Tidak ada data produk terjual</div>';
    } else {
      listEl.innerHTML = data.rows.map(p => `
        <div style="display:flex;align-items:center;gap:12px;background:var(--surface2);border:1px solid var(--border);border-radius:14px;padding:14px;margin-bottom:10px;">
          <div style="font-size:36px;">${p.emoji || '📦'}</div>
          <div style="flex:1;min-width:0;">
            <div style="font-weight:700;font-size:15px;margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${p.nama}</div>
            <div style="font-size:12px;color:var(--muted);">
              <span style="background:var(--surface);padding:3px 8px;border-radius:6px;margin-right:6px;">${p.kategori || 'Umum'}</span>
              SKU: ${p.id}
            </div>
            <div style="display:flex;gap:16px;margin-top:8px;font-size:13px;">
              <div>
                <span style="color:var(--muted);">Terjual:</span>
                <span style="font-weight:700;color:var(--accent);">${p.total_terjual} pcs</span>
              </div>
              <div>
                <span style="color:var(--muted);">Omzet:</span>
                <span style="font-weight:700;color:var(--green);">${fRp(p.total_omzet)}</span>
              </div>
            </div>
          </div>
        </div>
      `).join('');
    }
  } catch(e) {
    showToast('❌ Gagal memuat produk terjual: ' + e.message);
  }
  showLoading(false);
}

async function exportProdukTerjualExcel() {
  const periode = document.getElementById('rPeriode').value;
  const tanggal = document.getElementById('rTanggal').value;
  
  // Build date range sama seperti showProdukTerjualDetail
  let dari, ke;
  if (periode === 'harian' && tanggal) {
    dari = tanggal;
    ke = tanggal;
  } else if (periode === 'mingguan' && tanggal) {
    const [year, week] = tanggal.split('-W');
    const dates = getWeekDates(parseInt(year), parseInt(week));
    dari = dates[0];
    ke = dates[6];
  } else if (periode === 'bulanan' && tanggal) {
    const [year, month] = tanggal.split('-');
    dari = `${year}-${month}-01`;
    ke = `${year}-${month}-${new Date(parseInt(year), parseInt(month), 0).getDate()}`;
  } else {
    const today = new Date().toISOString().split('T')[0];
    dari = today;
    ke = today;
  }
  
  showLoading(true);
  try {
    const data = await api(`/api/laporan/produk-terjual?dari=${dari}&ke=${ke}`);
    
    // Export CSV
    let csv = 'ID,Nama Produk,Kategori,Terjual,Omzet\n';
    data.rows.forEach(p => {
      csv += `${p.id},"${p.nama}","${p.kategori || 'Umum'}",${p.total_terjual},${p.total_omzet}\n`;
    });
    csv += `\nTOTAL,,,${data.total_qty},${data.total_omzet}\n`;
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `produk_terjual_${dari}_${ke}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('✅ Export Excel berhasil');
  } catch(e) {
    showToast('❌ Gagal export: ' + e.message);
  }
  showLoading(false);
}

// ══════════════════════════════════

//  VOID TRANSAKSI
// ══════════════════════════════════
function bukaVoidTrx(id, noTrx, total, waktu) {
  document.getElementById('voidTrxId').value = id;
  document.getElementById('voidNoTrx').textContent = noTrx;
  document.getElementById('voidTotal').textContent = fRp(total);
  document.getElementById('voidWaktu').textContent = new Date(waktu).toLocaleString('id-ID');
  document.getElementById('voidReason').value = '';
  openM('mVoidTrx');
}

async function prosesVoidTrx() {
  const id = document.getElementById('voidTrxId').value;
  const reason = document.getElementById('voidReason').value.trim();
  
  if (!reason) {
    showToast('⚠️ Alasan void wajib diisi');
    return;
  }
  
  if (!confirm('Yakin ingin void transaksi ini? Stok akan dikembalikan.')) return;
  
  showLoading(true);
  try {
    await api(`/api/transaksi/${id}/void`, 'POST', { reason });
    showToast('✅ Transaksi berhasil di-void');
    closeM('mVoidTrx');
    await muatRiwayat();
    await muatProduk(); // Refresh stok
  } catch(e) {
    showToast('❌ ' + e.message);
  }
  showLoading(false);
}

async function restoreTrx(id) {
  if (!confirm('Yakin ingin mengembalikan (restore) transaksi ini? Stok akan dikurangi kembali.')) return;
  
  showLoading(true);
  try {
    await api(`/api/transaksi/${id}/restore`, 'POST', {});
    showToast('✅ Transaksi berhasil di-restore');
    await muatRiwayat();
    await muatProduk(); // Refresh stok
  } catch(e) {
    showToast('❌ ' + e.message);
  }
  showLoading(false);
}

let currentDetailTrx = null;

async function lihatDetailTrx(id) {
  showLoading(true);
  try {
    const trx = await api(`/api/transaksi/${id}`);
    currentDetailTrx = trx;
    const isVoid = trx.status === 'void';
    const isPemilik = APP_USER && APP_USER.role === 'pemilik';
    
    // Update header
    document.getElementById('detailNoTrx').textContent = trx.no_trx;
    const statusEl = document.getElementById('detailStatus');
    statusEl.textContent = isVoid ? 'VOID' : 'AKTIF';
    statusEl.className = 'detail-trx-status ' + (isVoid ? 'void' : '');
    
    // Build content
    const waktu = new Date(trx.waktu);
    const waktuStr = waktu.toLocaleDateString('id-ID', { 
      day: 'numeric', month: 'long', year: 'numeric' 
    }) + ' ' + waktu.toLocaleTimeString('id-ID', { 
      hour: '2-digit', minute: '2-digit' 
    });
    
    // Tabel pesanan
    const tabelPesanan = trx.items.map(i => `
      <tr>
        <td>${i.nama_produk}</td>
        <td>${fRp(i.harga)} × ${i.qty}</td>
        <td>${fRp(i.subtotal)}</td>
      </tr>
    `).join('');
    
    document.getElementById('detailTrxContent').innerHTML = `
      <!-- Rincian Transaksi -->
      <div class="detail-trx-section">
        <div class="detail-trx-section-title">📋 Rincian Transaksi</div>
        <div class="detail-trx-row">
          <span>Dibuat Oleh</span>
          <span>${trx.kasir || 'Kasir'} (Staff Kasir)</span>
        </div>
        <div class="detail-trx-row">
          <span>Pembayaran</span>
          <span>${(trx.metode_bayar || 'tunai').charAt(0).toUpperCase() + (trx.metode_bayar || 'tunai').slice(1)}</span>
        </div>
        <div class="detail-trx-row">
          <span>Tanggal Transaksi</span>
          <span>${waktuStr}</span>
        </div>
      </div>
      
      <!-- Pesanan -->
      <div class="detail-trx-section">
        <div class="detail-trx-section-title">🛒 Pesanan</div>
        <table class="detail-trx-table">
          <thead>
            <tr>
              <th>Nama Barang</th>
              <th>Jumlah</th>
              <th>Harga</th>
            </tr>
          </thead>
          <tbody>
            ${tabelPesanan}
          </tbody>
        </table>
        <div style="border-top:2px solid var(--border);padding-top:12px;margin-top:12px;">
          <div class="detail-trx-row">
            <span>Total Pesanan</span>
            <span>${fRp(trx.subtotal)}</span>
          </div>
          ${trx.diskon > 0 ? `
          <div class="detail-trx-row">
            <span>Diskon</span>
            <span style="color:var(--green);">-${fRp(trx.diskon)}</span>
          </div>` : ''}
          <div class="detail-trx-row" style="font-size:16px;font-weight:700;margin-top:8px;">
            <span>Total</span>
            <span style="color:var(--accent);">${fRp(trx.total)}</span>
          </div>
          <div class="detail-trx-row">
            <span>Bayar</span>
            <span>${fRp(trx.bayar)}</span>
          </div>
          <div class="detail-trx-row">
            <span>Kembali</span>
            <span style="color:var(--green);">${fRp(trx.kembalian)}</span>
          </div>
        </div>
      </div>
      
      <!-- Pelanggan -->
      ${trx.pelanggan_nama ? `
      <div class="detail-trx-section">
        <div class="detail-trx-section-title">👤 Pelanggan</div>
        <div class="detail-trx-pelanggan" onclick="copyPelangganName('${trx.pelanggan_nama}')">
          <span class="detail-trx-pelanggan-name">${trx.pelanggan_nama}</span>
          <span class="detail-trx-pelanggan-copy">📋</span>
        </div>
      </div>
      ` : ''}
      
      <!-- Void Info -->
      ${isVoid ? `
      <div class="detail-trx-section" style="background:rgba(255,92,92,0.1);border-radius:12px;padding:16px;border-left:4px solid var(--red);">
        <div style="color:var(--red);font-weight:700;margin-bottom:8px;">🗑 Transaksi Dibatalkan</div>
        <div class="detail-trx-row">
          <span>Oleh</span>
          <span>${trx.void_by}</span>
        </div>
        <div class="detail-trx-row">
          <span>Waktu Void</span>
          <span>${new Date(trx.void_at).toLocaleString('id-ID')}</span>
        </div>
        <div style="margin-top:8px;padding-top:8px;border-top:1px solid rgba(255,92,92,0.3);">
          <span style="color:var(--muted);font-size:12px;">Alasan:</span>
          <div style="margin-top:4px;">${trx.void_reason}</div>
        </div>
      </div>
      ` : ''}
    `;
    
    // Update menu dropdown
    const menuEl = document.getElementById('detailTrxMenu');
    const btnVoid = document.getElementById('btnVoidTrx');
    if (isPemilik) {
      btnVoid.style.display = isVoid ? 'none' : 'flex';
      btnVoid.onclick = () => { closeDetailMenu(); bukaVoidTrx(trx.id, trx.no_trx, trx.total, trx.waktu); };
    } else {
      btnVoid.style.display = 'none';
    }
    
    openM('mDetailTrx');
  } catch(e) {
    showToast('❌ ' + e.message);
  }
  showLoading(false);
}

function copyNoTrx() {
  if (currentDetailTrx) {
    navigator.clipboard.writeText(currentDetailTrx.no_trx);
    showToast('📋 No. Transaksi disalin');
  }
}

function copyPelangganName(nama) {
  navigator.clipboard.writeText(nama);
  showToast('📋 Nama pelanggan disalin');
}

function toggleDetailMenu() {
  document.getElementById('detailTrxMenu').classList.toggle('show');
}

function closeDetailMenu() {
  document.getElementById('detailTrxMenu').classList.remove('show');
}

function openPreviewStruk() {
  if (!currentDetailTrx) return;
  closeM('mDetailTrx');
  renderPreviewStruk(currentDetailTrx);
  openM('mPreviewStruk');
}

function renderPreviewStruk(trx) {
  const waktu = new Date(trx.waktu);
  const waktuStr = waktu.toLocaleDateString('id-ID', { 
    day: '2-digit', month: '2-digit', year: 'numeric' 
  }) + ' ' + waktu.toLocaleTimeString('id-ID', { 
    hour: '2-digit', minute: '2-digit' 
  });
  
  const itemRows = trx.items.map(i => `
    <div class="preview-struk-item">
      <div class="preview-struk-item-name">${i.nama_produk}</div>
      <div class="preview-struk-item-detail">
        <span>${fRp(i.harga)} x ${i.qty}</span>
        <span>${fRp(i.subtotal)}</span>
      </div>
    </div>
  `).join('');
  
  document.getElementById('previewStrukContent').innerHTML = `
    <div class="preview-struk-header">
      <div class="preview-struk-nama-toko" id="strukNamaToko">${document.getElementById('logoToko').textContent || 'KasirToko'}</div>
      <div class="preview-struk-alamat" id="strukAlamat">Jl. Contoh Alamat No. 123</div>
      <div class="preview-struk-telepon" id="strukTelepon">0812-3456-7890</div>
    </div>
    
    <div class="preview-struk-divider"></div>
    
    <div class="preview-struk-info">
      <div class="preview-struk-row">
        <span>Atas Nama</span>
        <span>${trx.pelanggan_nama || 'Umum'}</span>
      </div>
      <div class="preview-struk-row">
        <span>No</span>
        <span>${trx.no_trx}</span>
      </div>
      <div class="preview-struk-row">
        <span>Tanggal</span>
        <span>${waktuStr}</span>
      </div>
      <div class="preview-struk-row">
        <span>Kasir</span>
        <span>${trx.kasir || 'Kasir'}</span>
      </div>
      <div class="preview-struk-row">
        <span>Pembayaran</span>
        <span>${(trx.metode_bayar || 'tunai').charAt(0).toUpperCase() + (trx.metode_bayar || 'tunai').slice(1)}</span>
      </div>
    </div>
    
    <div class="preview-struk-divider"></div>
    
    <div class="preview-struk-items">
      ${itemRows}
    </div>
    
    <div class="preview-struk-divider"></div>
    
    <div class="preview-struk-info">
      <div class="preview-struk-row">
        <span>Total Pesanan</span>
        <span>${fRp(trx.subtotal)}</span>
      </div>
      ${trx.diskon > 0 ? `
      <div class="preview-struk-row">
        <span>Diskon</span>
        <span>-${fRp(trx.diskon)}</span>
      </div>` : ''}
      <div class="preview-struk-row preview-struk-total">
        <span>Total</span>
        <span>${fRp(trx.total)}</span>
      </div>
      <div class="preview-struk-row">
        <span>Bayar</span>
        <span>${fRp(trx.bayar)}</span>
      </div>
      <div class="preview-struk-row">
        <span>Kembali</span>
        <span>${fRp(trx.kembalian)}</span>
      </div>
    </div>
    
    <div class="preview-struk-footer">
      Terima kasih telah berbelanja
    </div>
  `;
}

function shareStruk() {
  showToast('↗️ Fitur bagikan struk akan segera hadir');
}

function toggleLogoOnStruk() {
  const showLogo = document.getElementById('toggleLogoStruk').checked;
  showToast(showLogo ? '✅ Logo akan ditampilkan di struk' : '❌ Logo disembunyikan');
}

function cetakStrukFromPreview() {
  if (currentDetailTrx) {
    window.print();
  }
}

function openStrukSettings() {
  showToast('⚙️ Pengaturan struk akan segera hadir');
}

function printStruk() {
  closeDetailMenu();
  openPreviewStruk();
}

function shareStrukDetail() {
  closeDetailMenu();
  shareStruk();
}

// ══════════════════════════════════
