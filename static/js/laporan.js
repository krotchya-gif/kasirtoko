// static/js/laporan.js — pindahan murni dari templates/index.html (split Fase 5).
// Global bersama (api, showToast, openM, fRp, ...) tetap window-scope.

//  LAPORAN
// ══════════════════════════════════
let lapTabIdx = 0;
let chartInstance = null;
let currentChartType = 'harian';

async function openLaporan() {
  // Default: hari ini
  const today = new Date().toISOString().split('T')[0];
  if (!document.getElementById('lDari').value) document.getElementById('lDari').value = today;
  if (!document.getElementById('lKe').value)   document.getElementById('lKe').value   = today;
  openM('mLaporan');
  switchLapTab(0);
}

function switchLapTab(idx) {
  lapTabIdx = idx;
  [0,1,2,3,4,5].forEach(i => {
    const tab = document.getElementById(`lapTab${i}`);
    if (tab) tab.classList.toggle('active', i === idx);
  });
  document.getElementById('lapContent').style.display    = idx === 0 ? '' : 'none';
  document.getElementById('lapTopContent').style.display = idx === 1 ? '' : 'none';
  document.getElementById('lapStokContent').style.display= idx === 2 ? '' : 'none';
  document.getElementById('lapChartContent').style.display= idx === 3 ? '' : 'none';
  document.getElementById('lapStokFullContent').style.display= idx === 4 ? '' : 'none';
  document.getElementById('lapKeuanganContent').style.display= idx === 5 ? '' : 'none';
  document.getElementById('lapDateFilter').style.display = idx === 0 || idx === 1 || idx === 3 || idx === 5 ? '' : 'none';
  document.getElementById('lapExportBtn').style.display  = idx === 0 || idx === 4 ? '' : 'none';
  muatLapTab();
}

async function muatLapTab() {
  if (lapTabIdx === 0) await muatLaporan();
  else if (lapTabIdx === 1) await muatTopProduk();
  else if (lapTabIdx === 2) await muatStokRendah();
  else if (lapTabIdx === 3) await muatChart();
  else if (lapTabIdx === 4) await muatLapStok();
  else if (lapTabIdx === 5) await muatLapKeuangan();
}

// ══════════════════════════════════

//  GRAFIK / CHART
// ══════════════════════════════════
function switchChartTab(tipe) {
  currentChartType = tipe;
  ['harian','mingguan','bulanan'].forEach(t => {
    document.getElementById(`chartTab${t.charAt(0).toUpperCase() + t.slice(1)}`).classList.toggle('active', t === tipe);
  });
  muatChart();
}

async function muatChart() {
  showLoading(true);
  
  const dari = document.getElementById('lDari').value;
  const ke   = document.getElementById('lKe').value;
  
  // Update button active state
  ['harian','mingguan','bulanan'].forEach(t => {
    document.getElementById(`chartTab${t.charAt(0).toUpperCase() + t.slice(1)}`).classList.toggle('active', t === currentChartType);
  });
  
  try {
    const data = await api(`/api/laporan/chart?tipe=${currentChartType}&dari=${dari}&ke=${ke}`);
    
    const ctx = document.getElementById('salesChart').getContext('2d');
    
    // Destroy existing chart
    if (chartInstance) {
      chartInstance.destroy();
    }
    
    // Calculate stats
    const totalTransaksi = data.datasets.transaksi.reduce((a,b)=>a+b,0);
    const totalOmzet = data.datasets.omzet.reduce((a,b)=>a+b,0);
    const totalDiskon = data.datasets.diskon.reduce((a,b)=>a+b,0);
    
    document.getElementById('chartStats').innerHTML = `
      <div style="background:var(--surface2);border:1px solid var(--border);border-radius:10px;padding:14px;text-align:center;">
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px;">Total Transaksi</div>
        <div style="font-family:var(--fh);font-size:18px;font-weight:800;color:var(--blue);">${totalTransaksi}</div>
      </div>
      <div style="background:var(--surface2);border:1px solid var(--border);border-radius:10px;padding:14px;text-align:center;">
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px;">Total Omzet</div>
        <div style="font-family:var(--fh);font-size:18px;font-weight:800;color:var(--accent);">${fRp(totalOmzet)}</div>
      </div>
      <div style="background:var(--surface2);border:1px solid var(--border);border-radius:10px;padding:14px;text-align:center;">
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px;">Total Diskon</div>
        <div style="font-family:var(--fh);font-size:18px;font-weight:800;color:var(--purple);">${fRp(totalDiskon)}</div>
      </div>
    `;
    
    // Create new chart
    chartInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.labels,
        datasets: [
          {
            label: 'Omzet (Rp)',
            data: data.datasets.omzet,
            backgroundColor: 'rgba(245, 166, 35, 0.8)',
            borderColor: 'rgba(245, 166, 35, 1)',
            borderWidth: 1,
            yAxisID: 'y',
            borderRadius: 4,
          },
          {
            label: 'Jumlah Transaksi',
            data: data.datasets.transaksi,
            type: 'line',
            borderColor: 'rgba(92, 154, 255, 1)',
            backgroundColor: 'rgba(92, 154, 255, 0.1)',
            borderWidth: 2,
            pointBackgroundColor: 'rgba(92, 154, 255, 1)',
            pointRadius: 4,
            fill: true,
            yAxisID: 'y1',
            tension: 0.4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          legend: {
            labels: {
              color: getComputedStyle(document.body).getPropertyValue('--text').trim() || '#f0f0f8',
              font: { family: 'DM Sans', size: 12 }
            }
          },
          tooltip: {
            backgroundColor: 'rgba(26, 29, 39, 0.95)',
            titleColor: '#f5a623',
            bodyColor: '#f0f0f8',
            borderColor: 'rgba(245, 166, 35, 0.3)',
            borderWidth: 1,
            padding: 12,
            callbacks: {
              label: function(context) {
                let label = context.dataset.label || '';
                if (label) {
                  label += ': ';
                }
                if (context.dataset.yAxisID === 'y') {
                  label += fRp(context.parsed.y);
                } else {
                  label += context.parsed.y + ' trx';
                }
                return label;
              }
            }
          }
        },
        scales: {
          x: {
            ticks: {
              color: getComputedStyle(document.body).getPropertyValue('--muted').trim() || '#8891a8',
              font: { family: 'DM Sans', size: 10 },
              maxRotation: 45,
              minRotation: 0
            },
            grid: {
              color: 'rgba(46, 50, 68, 0.5)'
            }
          },
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            ticks: {
              color: '#f5a623',
              font: { family: 'DM Sans', size: 10 },
              callback: function(value) {
                return 'Rp ' + (value / 1000000).toFixed(1) + 'jt';
              }
            },
            grid: {
              color: 'rgba(46, 50, 68, 0.5)'
            }
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            ticks: {
              color: '#5c9aff',
              font: { family: 'DM Sans', size: 10 }
            },
            grid: {
              drawOnChartArea: false
            }
          }
        }
      }
    });
    
  } catch(e) {
    console.error('Chart error:', e);
    document.getElementById('chartStats').innerHTML = '<div style="color:var(--red);text-align:center;">Gagal memuat grafik</div>';
  }
  
  showLoading(false);
}

// ══════════════════════════════════

//  LAPORAN STOK
// ══════════════════════════════════
async function muatLapStok() {
  showLoading(true);
  try {
    const data = await api('/api/laporan/stok?mode=opname');
    const el = document.getElementById('lapStokFullContent');
    
    el.innerHTML = `
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px">
        <div style="background:var(--surface2);padding:14px;border-radius:10px;text-align:center">
          <div style="font-size:11px;color:var(--muted)">Total Produk</div>
          <div style="font-size:22px;font-weight:800;color:var(--text)">${data.stats.total_produk}</div>
        </div>
        <div style="background:var(--surface2);padding:14px;border-radius:10px;text-align:center">
          <div style="font-size:11px;color:var(--muted)">Hampir Habis</div>
          <div style="font-size:22px;font-weight:800;color:var(--orange)">${data.stats.hampir_habis}</div>
        </div>
        <div style="background:var(--surface2);padding:14px;border-radius:10px;text-align:center">
          <div style="font-size:11px;color:var(--muted)">Stok Habis</div>
          <div style="font-size:22px;font-weight:800;color:var(--red)">${data.stats.stok_nol}</div>
        </div>
        <div style="background:var(--surface2);padding:14px;border-radius:10px;text-align:center">
          <div style="font-size:11px;color:var(--muted)">Nilai Stok</div>
          <div style="font-size:22px;font-weight:800;color:var(--green)">${fRp(data.stats.total_nilai_stok)}</div>
        </div>
      </div>
      
      <div style="display:flex;gap:8px;margin-bottom:12px">
        <button class="mbtn" onclick="exportStokCSV()">⬇️ Export Stok</button>
        <button class="mbtn sec" onclick="filterStokHampirHabis()">⚠️ Hampir Habis</button>
      </div>
      
      <div style="max-height:400px;overflow:auto;scrollbar-width:thin;-webkit-overflow-scrolling:touch">
        <table style="width:100%;font-size:13px;border-collapse:collapse">
          <thead style="position:sticky;top:0;background:var(--surface)">
            <tr style="border-bottom:2px solid var(--border)">
              <th style="padding:10px;text-align:left">Produk</th>
              <th style="padding:10px;text-align:center">Stok</th>
              <th style="padding:10px;text-align:center">Min</th>
              <th style="padding:10px;text-align:right">Harga</th>
              <th style="padding:10px;text-align:right">Nilai</th>
              <th style="padding:10px;text-align:center">Status</th>
            </tr>
          </thead>
          <tbody>
            ${data.produk.map(p => {
              const status = p.stok === 0 ? '<span style="background:var(--red);color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">Habis</span>' :
                            (p.stok <= p.stok_min || (p.stok_min === 0 && p.stok <= 5)) ? '<span style="background:var(--orange);color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">Hampir Habis</span>' :
                            '<span style="background:var(--green);color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">Aman</span>';
              const nilai = p.stok * p.harga_modal;
              return `<tr style="border-bottom:1px solid var(--border2)">
                <td style="padding:10px"><span style="font-size:16px;margin-right:6px">${p.emoji}</span>${p.nama}</td>
                <td style="padding:10px;text-align:center;font-weight:700">${p.stok}</td>
                <td style="padding:10px;text-align:center;color:var(--muted)">${p.stok_min || '-'}</td>
                <td style="padding:10px;text-align:right">${fRp(p.harga_modal)}</td>
                <td style="padding:10px;text-align:right;font-weight:600">${fRp(nilai)}</td>
                <td style="padding:10px;text-align:center">${status}</td>
              </tr>`;
            }).join('')}
          </tbody>
        </table>
      </div>
    `;
  } catch(e) {
    showToast('❌ Gagal memuat laporan stok: ' + e.message);
  }
  showLoading(false);
}

async function filterStokHampirHabis() {
  showLoading(true);
  try {
    const data = await api('/api/laporan/stok?mode=hampir_habis');
    const el = document.getElementById('lapStokFullContent');
    
    el.innerHTML = `
      <div style="background:var(--orange);color:#fff;padding:12px 16px;border-radius:10px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center">
        <div style="font-weight:700">⚠️ Produk Hampir Habis / Stok Rendah</div>
        <button class="mbtn" style="background:#fff;color:var(--orange)" onclick="muatLapStok()">Lihat Semua</button>
      </div>
      
      <div style="max-height:400px;overflow:auto;scrollbar-width:thin;-webkit-overflow-scrolling:touch">
        ${data.produk.length === 0 ? '<div style="text-align:center;padding:40px;color:var(--muted)">Tidak ada produk dengan stok rendah ✅</div>' : `
        <table style="width:100%;font-size:13px;border-collapse:collapse">
          <thead style="position:sticky;top:0;background:var(--surface)">
            <tr style="border-bottom:2px solid var(--border)">
              <th style="padding:10px;text-align:left">Produk</th>
              <th style="padding:10px;text-align:center">Stok</th>
              <th style="padding:10px;text-align:center">Min</th>
              <th style="padding:10px;text-align:right">Harga Jual</th>
              <th style="padding:10px;text-align:center">Aksi</th>
            </tr>
          </thead>
          <tbody>
            ${data.produk.map(p => `
              <tr style="border-bottom:1px solid var(--border2)">
                <td style="padding:10px"><span style="font-size:16px;margin-right:6px">${p.emoji}</span>${p.nama}</td>
                <td style="padding:10px;text-align:center;font-weight:700;color:var(--red)">${p.stok}</td>
                <td style="padding:10px;text-align:center;color:var(--muted)">${p.stok_min || '-'}</td>
                <td style="padding:10px;text-align:right">${fRp(p.harga)}</td>
                <td style="padding:10px;text-align:center">
                  <button class="mbtn" style="padding:4px 12px;font-size:11px" onclick="openTambahStok(${p.id}, '${p.nama.replace(/'/g, "\\'")}')">+ Stok</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
        `}
      </div>
    `;
  } catch(e) {
    showToast('❌ ' + e.message);
  }
  showLoading(false);
}

function openTambahStok(id, nama) {
  const tambah = prompt(`Tambah stok untuk "${nama}":\nMasukkan jumlah stok yang ingin ditambahkan:`, '10');
  if (tambah && parseInt(tambah) > 0) {
    // Buka modal adjust stok
    openKelola();
    showToast(`Silakan adjust stok untuk ${nama} di menu Kelola Produk`);
  }
}

function exportStokCSV() {
  showToast('📥 Export stok ke CSV...');
  // Implementasi export akan ditambahkan
}

// ══════════════════════════════════

//  LAPORAN KEUANGAN
// ══════════════════════════════════
async function muatLapKeuangan() {
  const dari = document.getElementById('lDari').value;
  const ke   = document.getElementById('lKe').value;
  
  showLoading(true);
  try {
    const data = await api(`/api/laporan/keuangan?dari=${dari}&ke=${ke}`);
    const el = document.getElementById('lapKeuanganContent');
    
    el.innerHTML = `
      <div style="font-size:12px;color:var(--muted);margin-bottom:12px">Periode: ${new Date(data.periode.dari).toLocaleDateString('id-ID')} - ${new Date(data.periode.ke).toLocaleDateString('id-ID')}</div>
      
      <!-- Arus Kas -->
      <div style="background:var(--surface2);border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:16px">
        <div style="font-size:14px;font-weight:700;margin-bottom:12px;color:var(--accent)">💰 Arus Kas</div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">
          <div style="text-align:center;padding:12px;background:var(--surface);border-radius:8px">
            <div style="font-size:11px;color:var(--muted)">Pemasukan</div>
            <div style="font-size:18px;font-weight:800;color:var(--green)">${fRp(data.arus_kas.pemasukan.total)}</div>
            <div style="font-size:11px;color:var(--muted)">${data.arus_kas.pemasukan.count} transaksi</div>
          </div>
          <div style="text-align:center;padding:12px;background:var(--surface);border-radius:8px">
            <div style="font-size:11px;color:var(--muted)">Pengeluaran</div>
            <div style="font-size:18px;font-weight:800;color:var(--red)">${fRp(data.arus_kas.pengeluaran.total)}</div>
            <div style="font-size:11px;color:var(--muted)">${data.arus_kas.pengeluaran.count} transaksi</div>
          </div>
          <div style="text-align:center;padding:12px;background:var(--surface);border-radius:8px">
            <div style="font-size:11px;color:var(--muted)">Saldo</div>
            <div style="font-size:18px;font-weight:800;color:${data.arus_kas.saldo >= 0 ? 'var(--green)' : 'var(--red)'}">${fRp(data.arus_kas.saldo)}</div>
            <div style="font-size:11px;color:var(--muted)">Net</div>
          </div>
        </div>
      </div>
      
      <!-- Penjualan -->
      <div style="background:var(--surface2);border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:16px">
        <div style="font-size:14px;font-weight:700;margin-bottom:12px;color:var(--accent)">📊 Penjualan</div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px">
          <div style="text-align:center">
            <div style="font-size:11px;color:var(--muted)">Omzet</div>
            <div style="font-size:16px;font-weight:800;color:var(--text)">${fRp(data.penjualan.omzet)}</div>
          </div>
          <div style="text-align:center">
            <div style="font-size:11px;color:var(--muted)">Diskon</div>
            <div style="font-size:16px;font-weight:800;color:var(--purple)">${fRp(data.penjualan.diskon)}</div>
          </div>
          <div style="text-align:center">
            <div style="font-size:11px;color:var(--muted)">Net</div>
            <div style="font-size:16px;font-weight:800;color:var(--green)">${fRp(data.penjualan.net)}</div>
          </div>
          <div style="text-align:center">
            <div style="font-size:11px;color:var(--muted)">Transaksi</div>
            <div style="font-size:16px;font-weight:800;color:var(--blue)">${data.penjualan.transaksi}</div>
          </div>
        </div>
      </div>
      
      <!-- Laba/Rugi -->
      <div style="background:var(--surface2);border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:16px">
        <div style="font-size:14px;font-weight:700;margin-bottom:12px;color:var(--accent)">📈 Laba / Rugi</div>
        <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px">
          <div style="text-align:center;padding:12px;background:var(--surface);border-radius:8px">
            <div style="font-size:11px;color:var(--muted)">Laba Kotor (Estimasi)</div>
            <div style="font-size:20px;font-weight:800;color:${data.laba_rugi.laba_kotor >= 0 ? 'var(--green)' : 'var(--red)'}">${fRp(data.laba_rugi.laba_kotor)}</div>
          </div>
          <div style="text-align:center;padding:12px;background:var(--surface);border-radius:8px">
            <div style="font-size:11px;color:var(--muted)">Estimasi Net (Setelah Pengeluaran)</div>
            <div style="font-size:20px;font-weight:800;color:${data.laba_rugi.estimasi_net >= 0 ? 'var(--green)' : 'var(--red)'}">${fRp(data.laba_rugi.estimasi_net)}</div>
          </div>
        </div>
      </div>
      
      <!-- Metode Pembayaran -->
      <div style="background:var(--surface2);border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:16px">
        <div style="font-size:14px;font-weight:700;margin-bottom:12px;color:var(--accent)">💳 Pembayaran</div>
        <div style="display:flex;gap:12px;flex-wrap:wrap">
          ${data.metode_pembayaran.map(m => `
            <div style="flex:1;min-width:120px;text-align:center;padding:12px;background:var(--surface);border-radius:8px">
              <div style="font-size:11px;color:var(--muted)">${m.metode_bayar.toUpperCase()}</div>
              <div style="font-size:16px;font-weight:800;color:var(--text)">${fRp(m.total)}</div>
              <div style="font-size:11px;color:var(--muted)">${m.count} trx</div>
            </div>
          `).join('')}
        </div>
      </div>
      
      <!-- Harian -->
      <div style="background:var(--surface2);border:1px solid var(--border);border-radius:12px;padding:16px">
        <div style="font-size:14px;font-weight:700;margin-bottom:12px;color:var(--accent)">📅 Detail Harian</div>
        <div style="max-height:200px;overflow:auto;scrollbar-width:thin;-webkit-overflow-scrolling:touch">
          <table style="width:100%;font-size:12px;border-collapse:collapse">
            <thead>
              <tr style="border-bottom:1px solid var(--border)">
                <th style="padding:8px;text-align:left">Tanggal</th>
                <th style="padding:8px;text-align:center">Trx</th>
                <th style="padding:8px;text-align:right">Omzet</th>
                <th style="padding:8px;text-align:right">Diskon</th>
                <th style="padding:8px;text-align:right">Net</th>
              </tr>
            </thead>
            <tbody>
              ${data.harian.map(h => `
                <tr style="border-bottom:1px solid var(--border2)">
                  <td style="padding:8px">${new Date(h.tanggal).toLocaleDateString('id-ID', {weekday:'short',day:'numeric',month:'short'})}</td>
                  <td style="padding:8px;text-align:center">${h.transaksi}</td>
                  <td style="padding:8px;text-align:right">${fRp(h.omzet)}</td>
                  <td style="padding:8px;text-align:right;color:var(--purple)">${fRp(h.diskon)}</td>
                  <td style="padding:8px;text-align:right;font-weight:600">${fRp(h.omzet - h.diskon)}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch(e) {
    showToast('❌ Gagal memuat laporan keuangan: ' + e.message);
  }
  showLoading(false);
}

async function muatLaporan() {
  const dari = document.getElementById('lDari').value;
  const ke   = document.getElementById('lKe').value;
  showLoading(true);
  const data = await api(`/api/laporan/rentang?dari=${dari}&ke=${ke}`);
  const el = document.getElementById('lapContent');
  const s = data.stats;
  el.innerHTML=`
    <div class="lg">
      <div class="lc"><div class="lv" style="color:var(--accent)">${fRp(Math.round(s.omzet))}</div><div class="ll">Total Omzet</div></div>
      <div class="lc"><div class="lv" style="color:var(--blue)">${s.total_transaksi}</div><div class="ll">Transaksi</div></div>
      <div class="lc"><div class="lv" style="color:var(--green)">${fRp(Math.round(s.rata_rata))}</div><div class="ll">Rata-rata / Trx</div></div>
      <div class="lc"><div class="lv" style="color:var(--purple)">${fRp(Math.round(s.total_diskon))}</div><div class="ll">Total Diskon</div></div>
    </div>
    ${data.harian.length?`
      <div style="font-family:var(--fh);font-size:12px;font-weight:700;margin-bottom:8px;color:var(--muted);letter-spacing:1px">📅 OMZET HARIAN</div>
      <div style="max-height:240px;overflow-y:auto;scrollbar-width:thin;scrollbar-color:var(--border) transparent;">
        ${data.harian.map(h=>`
          <div style="display:flex;justify-content:space-between;padding:7px 11px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;margin-bottom:4px;font-size:12px">
            <span>${new Date(h.tanggal).toLocaleDateString('id-ID',{weekday:'short',day:'numeric',month:'short'})} — ${h.transaksi} trx</span>
            <span style="font-family:var(--fh);font-weight:700;color:var(--accent)">${fRp(h.omzet)}</span>
          </div>`).join('')}
      </div>`:
    '<div style="color:var(--muted);text-align:center;padding:20px">Tidak ada data di periode ini</div>'}`;
  showLoading(false);
}

async function muatTopProduk() {
  const dari = document.getElementById('lDari').value;
  const ke   = document.getElementById('lKe').value;
  showLoading(true);
  const list = await api(`/api/laporan/top-produk?dari=${dari}&ke=${ke}&limit=15`);
  const el = document.getElementById('lapTopContent');
  if (!list.length) {
    el.innerHTML = '<div style="color:var(--muted);text-align:center;padding:24px">Tidak ada data di periode ini</div>';
    showLoading(false); return;
  }
  const rankEmoji = ['🥇','🥈','🥉'];
  const rankClass = ['gold','silver','bronze'];
  el.innerHTML = `
    <div style="font-family:var(--fh);font-size:11px;font-weight:700;color:var(--muted);letter-spacing:1px;margin-bottom:8px">🏆 PRODUK TERLARIS</div>
    <div style="max-height:360px;overflow-y:auto;scrollbar-width:thin;scrollbar-color:var(--border) transparent;">
    ${list.map((p,i)=>{
      const profitPerUnit = p.harga_modal > 0 ? (p.total_nilai / p.total_qty - p.harga_modal) : null;
      const profitTotal   = profitPerUnit !== null ? profitPerUnit * p.total_qty : null;
      return `
        <div class="top-item">
          <div class="top-rank ${rankClass[i]||''}">${i < 3 ? rankEmoji[i] : `${i+1}`}</div>
          <span style="font-size:20px;flex-shrink:0">${p.emoji||'📦'}</span>
          <div class="top-info">
            <div class="top-nama">${p.nama}</div>
            <div class="top-sub">${p.total_qty} terjual${profitTotal !== null ? ` · Laba ${fRp(Math.round(profitTotal))}` : ''}</div>
          </div>
          <div class="top-val">${fRp(p.total_nilai)}</div>
        </div>`;
    }).join('')}
    </div>`;
  showLoading(false);
}

async function muatStokRendah() {
  showLoading(true);
  const list = await api('/api/produk/stok-rendah');
  const el = document.getElementById('lapStokContent');
  if (!list.length) {
    el.innerHTML = '<div style="color:var(--green);text-align:center;padding:24px;font-size:13px">✅ Semua stok dalam kondisi aman</div>';
    showLoading(false); return;
  }
  el.innerHTML = `
    <div style="font-family:var(--fh);font-size:11px;font-weight:700;color:var(--muted);letter-spacing:1px;margin-bottom:8px">⚠️ STOK PERLU DIISI ULANG (${list.length} produk)</div>
    <div style="max-height:360px;overflow-y:auto;scrollbar-width:thin;scrollbar-color:var(--border) transparent;">
    ${list.map(p=>`
      <div class="stok-r-item">
        <span style="font-size:20px;flex-shrink:0">${p.emoji||'📦'}</span>
        <div style="flex:1;min-width:0">
          <div style="font-size:13px;font-weight:600;">${p.nama}</div>
          <div style="font-size:11px;color:var(--muted)">${p.kategori}</div>
        </div>
        <div style="text-align:right;flex-shrink:0">
          <div style="font-family:var(--fh);font-size:14px;font-weight:800;color:var(--red)">Sisa ${p.stok}</div>
          ${p.stok_min>0?`<div style="font-size:10px;color:var(--muted)">min: ${p.stok_min}</div>`:''}
        </div>
      </div>`).join('')}
    </div>`;
  showLoading(false);
}

async function exportCSV() {
  const dari = document.getElementById('lDari').value;
  const ke   = document.getElementById('lKe').value;
  window.location.href = `/api/export/csv?dari=${dari}&ke=${ke}`;
  showToast('✅ CSV sedang didownload...');
}

async function exportPDF() {
  const dari = document.getElementById('lDari').value;
  const ke   = document.getElementById('lKe').value;
  showLoading(true);
  try {
    const res = await fetch(`/api/export/pdf?dari=${dari}&ke=${ke}`);
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.error || 'Gagal export PDF');
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `laporan-penjualan-${dari || 'semua'}-${ke || 'semua'}.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    showToast('✅ PDF sedang didownload...');
  } catch(e) {
    showToast('❌ ' + e.message);
  }
  showLoading(false);
}

// ══════════════════════════════════

//  DOMPET / KAS
// ══════════════════════════════════
let kasTipe   = 'pemasukan';
let kasMetode = 'tunai';

function setKasTipe(t) {
  kasTipe = t;
  document.getElementById('kTipe').value = t;
  document.getElementById('kBtnMasuk').classList.toggle('active', t === 'pemasukan');
  document.getElementById('kBtnKeluar').classList.toggle('active', t === 'pengeluaran');
}

function setKasMetode(m) {
  kasMetode = m;
  document.getElementById('kMetode').value = m;
  ['tunai','transfer','qris'].forEach(k => {
    document.getElementById('kBtn' + k.charAt(0).toUpperCase() + k.slice(1))
      .classList.toggle('active', k === m);
  });
}

async function openDompet() {
  const today = new Date().toISOString().split('T')[0];
  if (!document.getElementById('kDari').value) document.getElementById('kDari').value = today;
  if (!document.getElementById('kKe').value)   document.getElementById('kKe').value   = today;
  openM('mDompet');
  await muatKas();
}

async function muatKas() {
  const dari = document.getElementById('kDari').value;
  const ke   = document.getElementById('kKe').value;
  showLoading(true);
  const data = await api(`/api/kas?dari=${dari}&ke=${ke}`);
  const s = data.stats;
  document.getElementById('kasSaldo').textContent         = fRp(s.saldo);
  document.getElementById('kasSaldoTunai').textContent    = fRp(s.saldo_tunai);
  document.getElementById('kasSaldoNonTunai').textContent = fRp(s.saldo_nontunai);
  document.getElementById('kasMasuk').textContent  = fRp(s.total_masuk);
  document.getElementById('kasKeluar').textContent = fRp(s.total_keluar);

  const el = document.getElementById('kasList');
  if (!data.rows.length) {
    el.innerHTML = '<div style="text-align:center;color:var(--muted);padding:20px;font-size:13px">Belum ada data di periode ini</div>';
    showLoading(false); return;
  }
  const metodeLabel = { tunai:'💵 Tunai', transfer:'🏦 Transfer', qris:'📱 QRIS' };
  const metodeClass = m => m === 'tunai' ? 'tunai' : 'nontunai';
  el.innerHTML = data.rows.map(r => {
    const isMasuk = r.tipe === 'pemasukan';
    const wkt     = new Date(r.waktu).toLocaleString('id-ID', {day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'});
    const m       = r.metode || 'tunai';
    return `
      <div class="kas-item">
        <span class="kas-item-ico">${isMasuk ? '⬆️' : '⬇️'}</span>
        <div class="kas-item-info">
          <div class="kas-item-ket">${r.keterangan || (isMasuk ? 'Pemasukan' : 'Pengeluaran')}
            <span class="kas-m-badge ${metodeClass(m)}">${metodeLabel[m] || m}</span>
          </div>
          <div class="kas-item-wkt">${wkt}</div>
        </div>
        <span class="kas-item-jml ${isMasuk ? 'masuk' : 'keluar'}">${isMasuk ? '+' : '-'}${fRp(r.jumlah)}</span>
        <button class="kas-del" onclick="hapusKas(${r.id})" title="Hapus">🗑</button>
      </div>`;
  }).join('');
  showLoading(false);
}

async function simpanKas() {
  const jumlah = parseInt(document.getElementById('kJumlah').value) || 0;
  const ket    = document.getElementById('kKet').value.trim();
  if (jumlah <= 0) { showToast('⚠️ Jumlah harus lebih dari 0'); return; }
  showLoading(true);
  await api('/api/kas', 'POST', { tipe: kasTipe, jumlah, keterangan: ket, metode: kasMetode });
  document.getElementById('kJumlah').value = '';
  document.getElementById('kKet').value    = '';
  await muatKas();
  showToast(`✅ ${kasTipe === 'pemasukan' ? 'Pemasukan' : 'Pengeluaran'} ${fRp(jumlah)} dicatat`);
}

async function hapusKas(id) {
  if (!confirm('Hapus entri kas ini?')) return;
  showLoading(true);
  await api(`/api/kas/${id}`, 'DELETE');
  await muatKas();
  showToast('🗑 Entri kas dihapus');
}

// ══════════════════════════════════

//  RESET SALDO DOMPET
// ══════════════════════════════════
function bukaResetSaldo() {
  document.getElementById('resetSaldoInput').value = '';
  document.getElementById('btnConfirmReset').disabled = true;
  document.getElementById('btnConfirmReset').style.opacity = '0.5';
  document.getElementById('btnConfirmReset').style.cursor = 'not-allowed';
  openM('mResetSaldo');
}

function validateResetSaldo() {
  const input = document.getElementById('resetSaldoInput').value.trim();
  const btn = document.getElementById('btnConfirmReset');
  const isValid = input === 'Reset Saldo';
  btn.disabled = !isValid;
  btn.style.opacity = isValid ? '1' : '0.5';
  btn.style.cursor = isValid ? 'pointer' : 'not-allowed';
}

async function prosesResetSaldo() {
  const input = document.getElementById('resetSaldoInput').value.trim();
  if (input !== 'Reset Saldo') {
    showToast('❌ Konfirmasi tidak valid');
    return;
  }

  showLoading(true);
  try {
    await api('/api/kas/reset', 'POST', { konfirmasi: input });
    closeM('mResetSaldo');
    await muatKas();
    showToast('✅ Saldo dompet berhasil direset');
  } catch(e) {
    showToast('❌ ' + e.message);
  }
  showLoading(false);
}

// ══════════════════════════════════

//  RESET TRANSAKSI & DOMPET
// ══════════════════════════════════
function bukaResetTransaksi() {
  document.getElementById('resetTransaksiInput').value = '';
  document.getElementById('btnConfirmResetTrx').disabled = true;
  document.getElementById('btnConfirmResetTrx').style.opacity = '0.5';
  document.getElementById('btnConfirmResetTrx').style.cursor = 'not-allowed';
  openM('mResetTransaksi');
}

function validateResetTransaksi() {
  const input = document.getElementById('resetTransaksiInput').value.trim();
  const btn = document.getElementById('btnConfirmResetTrx');
  const isValid = input === 'RESET TRANSAKSI';
  btn.disabled = !isValid;
  btn.style.opacity = isValid ? '1' : '0.5';
  btn.style.cursor = isValid ? 'pointer' : 'not-allowed';
}

async function prosesResetTransaksi() {
  const input = document.getElementById('resetTransaksiInput').value.trim();
  if (input !== 'RESET TRANSAKSI') {
    showToast('❌ Konfirmasi tidak valid');
    return;
  }

  showLoading(true);
  try {
    const r = await api('/api/transaksi/reset', 'POST', { konfirmasi: input });
    closeM('mResetTransaksi');
    closeM('mRiwayat');
    showToast(`✅ Reset selesai: ${r.dihapus.transaksi} transaksi dihapus (backup: ${r.backup.length} file)`);
    if (typeof muatRiwayat === 'function') await muatRiwayat();
    if (typeof muatKas === 'function') await muatKas();
  } catch(e) {
    showToast('❌ ' + e.message);
  }
  showLoading(false);
}

// ══════════════════════════════════

//  TUTUP KASIR
// ══════════════════════════════════
async function openTutupKasir() {
  openM('mTutupKasir');
  await muatPreviewTutup();
  if (APP_USER.role === 'pemilik') await muatRiwayatTutup();
}

async function muatPreviewTutup() {
  document.getElementById('tkPreviewContent').innerHTML =
    '<div style="text-align:center;color:var(--muted);padding:12px">Memuat...</div>';
  document.getElementById('tkFormSection').style.display = 'none';

  const data = await api('/api/tutup-kasir/preview');
  const el = document.getElementById('tkPreviewContent');

  if (data.jumlah_trx === 0) {
    el.innerHTML = '<div style="text-align:center;color:var(--muted);padding:16px;font-size:13px">✅ Semua transaksi sudah ditutup</div>';
    return;
  }

  el.innerHTML = `
    <div class="tk-stat-row bold">
      <span class="lbl">Total Pendapatan</span>
      <span class="val" style="color:var(--green)">${fRp(data.total)}</span>
    </div>
    <div class="tk-sub">
      ${data.total_tunai    > 0 ? `<div class="tk-stat-row"><span class="lbl">💵 Tunai</span><span class="val">${fRp(data.total_tunai)}</span></div>` : ''}
      ${data.total_transfer > 0 ? `<div class="tk-stat-row"><span class="lbl">🏦 Transfer</span><span class="val">${fRp(data.total_transfer)}</span></div>` : ''}
      ${data.total_qris     > 0 ? `<div class="tk-stat-row"><span class="lbl">📱 QRIS</span><span class="val">${fRp(data.total_qris)}</span></div>` : ''}
    </div>
    <div class="tk-stat-row" style="margin-top:6px">
      <span class="lbl">Jumlah Transaksi</span>
      <span class="val">${data.jumlah_trx} transaksi</span>
    </div>`;

  document.getElementById('tkFormSection').style.display = 'block';
}

async function prosesTutupKasir() {
  const ket = document.getElementById('tkKet').value.trim();
  showLoading(true);
  try {
    await api('/api/tutup-kasir', 'POST', { keterangan: ket });
    document.getElementById('tkKet').value = '';
    showToast('🔒 Tutup kasir berhasil! Menunggu konfirmasi pemilik');
    await muatPreviewTutup();
    if (APP_USER.role === 'pemilik') await muatRiwayatTutup();
    _updateTkBadge();
  } catch(e) {
    showToast('❌ ' + e.message);
  }
  showLoading(false);
}

async function muatRiwayatTutup() {
  const el = document.getElementById('tkRiwayat');
  if (!el) return;
  const data = await api('/api/tutup-kasir');
  if (!data.rows.length) {
    el.innerHTML = '<div style="text-align:center;color:var(--muted);padding:20px;font-size:13px">Belum ada riwayat</div>';
    return;
  }
  el.innerHTML = data.rows.map(r => {
    const wkt = new Date(r.waktu).toLocaleString('id-ID', {day:'numeric',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'});
    const isPending = r.status === 'pending';
    const metodeDetail = [
      r.total_tunai    > 0 ? `💵 Tunai ${fRp(r.total_tunai)}`    : '',
      r.total_transfer > 0 ? `🏦 Transfer ${fRp(r.total_transfer)}` : '',
      r.total_qris     > 0 ? `📱 QRIS ${fRp(r.total_qris)}`      : '',
    ].filter(Boolean).join(' · ');
    return `
      <div class="tk-item">
        <div class="tk-item-head">
          <span class="tk-item-title">${fRp(r.total)} · ${r.jumlah_trx} trx</span>
          <span class="tk-item-badge ${r.status}">${isPending ? '⏳ Pending' : '✅ Confirmed'}</span>
        </div>
        <div class="tk-item-detail">${metodeDetail}</div>
        <div class="tk-item-detail">${wkt} · oleh ${r.dibuat_oleh}${r.keterangan ? ' · "'+r.keterangan+'"' : ''}</div>
        <div class="tk-item-meta">
          ${isPending
            ? `<button class="mbtn" style="background:var(--green);color:#111;padding:6px 14px;font-size:12px" onclick="konfirmasiTutup(${r.id})">✅ Konfirmasi ke Kas</button>`
            : `<span style="font-size:11px;color:var(--muted)">Dikonfirmasi oleh ${r.dikonfirmasi_oleh}</span>`
          }
        </div>
      </div>`;
  }).join('');
}

async function konfirmasiTutup(id) {
  if (!confirm('Konfirmasi tutup kasir ini ke Kas?')) return;
  showLoading(true);
  try {
    await api(`/api/tutup-kasir/${id}/konfirmasi`, 'POST');
    showToast('✅ Dikonfirmasi! Entri kas berhasil dibuat');
    await muatRiwayatTutup();
    _updateTkBadge();
  } catch(e) {
    showToast('❌ ' + e.message);
  }
  showLoading(false);
}

async function _updateTkBadge() {
  if (APP_USER.role !== 'pemilik') return;
  try {
    const data = await api('/api/tutup-kasir');
    const hasPending = data.pending > 0;
    ['tkBadge','tkBadgeMob'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.classList.toggle('hidden', !hasPending);
    });
  } catch(e) { /* silent */ }
}

// ══════════════════════════════════

// ── Bootstrap: dipanggil setelah SEMUA modul terparse (sebelumnya inline di section UTILS).
init();
